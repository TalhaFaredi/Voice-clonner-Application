import os
import time
import stripe
from flask import Blueprint, abort, current_app, g, jsonify, request
from .auth import body
from ..middleware.security import authenticated, limit
from ..models.database import rows, transaction
from ..services.credits import change

bp = Blueprint('billing',__name__)
PLANS = {'free':dict(name='Free',monthly=0,yearly=0,credits=5000),
         'starter':dict(name='Starter',monthly=12,yearly=120,credits=50000),
         'creator':dict(name='Creator',monthly=29,yearly=290,credits=200000)}


def price_map():
    return {os.getenv(f'STRIPE_{p.upper()}_{i.upper()}_PRICE'): (p,'month' if i=='monthly' else 'year')
            for p in ('starter','creator') for i in ('monthly','yearly')
            if os.getenv(f'STRIPE_{p.upper()}_{i.upper()}_PRICE')}


def configured():
    if not current_app.config['STRIPE_SECRET_KEY']:
        abort(503,'Payments are not configured yet. Contact the service administrator.')
    stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
    stripe.max_network_retries = 1


@bp.get('/plans')
def plans():
    return jsonify(plans=PLANS,billing_ready=bool(current_app.config['STRIPE_SECRET_KEY'] and price_map()),
                   note='Free credits are a one-time welcome grant. Paid monthly plans receive credits per paid month; annual plans receive 12 months upfront. Credits carry forward. Voice cloning costs 1,000 credits; speech costs 1 per character.')


@bp.get('/billing')
@authenticated
def overview():
    user = g.user['id']
    return jsonify(subscription=rows('SELECT * FROM subscriptions WHERE user_id=?',(user,),one=True),
                   credits=g.user['credits'],ledger=rows('SELECT * FROM ledger WHERE user_id=? ORDER BY created_at DESC LIMIT 50',(user,)),
                   payments=rows('SELECT * FROM payments WHERE user_id=? ORDER BY created_at DESC LIMIT 30',(user,)))


@bp.post('/billing/checkout')
@authenticated
def checkout():
    limit('checkout',10,3600)
    configured()
    data = body()
    plan, interval = data.get('plan'),data.get('interval','month')
    if plan not in ('starter','creator') or interval not in ('month','year'):
        abort(400,'Choose a paid plan and billing interval.')
    price = next((p for p,v in price_map().items() if v==(plan,interval)),None)
    if not price:
        abort(503,'That plan has not been configured in Stripe.')
    try:
        with transaction() as db:
            user = db.execute('SELECT * FROM users WHERE id=?',(g.user['id'],)).fetchone()
            sub = db.execute('SELECT * FROM subscriptions WHERE user_id=?',(g.user['id'],)).fetchone()
            if sub['stripe_id'] and sub['status'] not in ('canceled','incomplete_expired','free'):
                abort(409,'Manage your existing subscription in the billing portal.')
            pending = db.execute('SELECT * FROM checkout_requests WHERE user_id=?',(g.user['id'],)).fetchone()
            if pending and pending['expires']>time.time():
                return jsonify(url=pending['url'])
            customer = user['customer_id']
            if not customer:
                customer = stripe.Customer.create(email=user['email'],name=user['name'],
                           metadata={'user_id':user['id']},idempotency_key=f'customer:{user["id"]}')['id']
                db.execute('UPDATE users SET customer_id=? WHERE id=?',(customer,user['id']))
            session = stripe.checkout.Session.create(customer=customer,mode='subscription',
                line_items=[{'price':price,'quantity':1}],client_reference_id=user['id'],
                subscription_data={'metadata':{'user_id':user['id']}},
                success_url=current_app.config['PUBLIC_URL']+'/#/billing?checkout=success',
                cancel_url=current_app.config['PUBLIC_URL']+'/#/billing?checkout=cancelled',
                expires_at=int(time.time())+1800,
                idempotency_key=f'checkout:{user["id"]}:{int(time.time()//1800)}')
            db.execute('INSERT OR REPLACE INTO checkout_requests VALUES(?,?,?,?)',
                       (user['id'],session['id'],session['url'],session['expires_at']))
        return jsonify(url=session['url'])
    except stripe.StripeError:
        current_app.logger.exception('Stripe checkout failed')
        abort(502,'Stripe could not start checkout. Please try again.')


@bp.post('/billing/portal')
@authenticated
def portal():
    configured()
    if not g.user['customer_id']:
        abort(400,'Choose a paid plan first.')
    try:
        session = stripe.billing_portal.Session.create(customer=g.user['customer_id'],
                    return_url=current_app.config['PUBLIC_URL']+'/#/billing')
        return jsonify(url=session['url'])
    except stripe.StripeError:
        current_app.logger.exception('Stripe portal failed')
        abort(502,'The billing portal is temporarily unavailable.')


def subscription_values(subscription):
    items = subscription.get('items',{}).get('data',[])
    if len(items)!=1 or items[0].get('quantity',1)!=1:
        raise ValueError('Unexpected subscription items')
    item = items[0]
    price = item['price']['id']
    if price not in price_map():
        raise ValueError('Unknown Stripe price')
    plan,interval = price_map()[price]
    return plan,interval,item.get('current_period_end') or subscription.get('current_period_end')


def apply_event(event, subscription=None):
    """Verified events only. The ledger and event receipt commit in the same transaction."""
    obj,kind = event['data']['object'],event['type']
    with transaction() as db:
        if db.execute('SELECT 1 FROM webhook_events WHERE id=?',(event['id'],)).fetchone():
            return
        customer = obj.get('customer')
        user = db.execute('SELECT * FROM users WHERE customer_id=?',(customer,)).fetchone() if customer else None
        if user and subscription:
            if subscription.get('customer') != customer:
                raise ValueError('Subscription customer mismatch')
            plan,interval,end = subscription_values(subscription)
            db.execute('UPDATE subscriptions SET stripe_id=?,plan=?,interval=?,status=?,period_end=?,cancel_at_period_end=? WHERE user_id=?',
                       (subscription['id'],plan,interval,subscription['status'],end,
                        int(subscription.get('cancel_at_period_end',False)),user['id']))
        if user and kind=='invoice.paid':
            if not subscription:
                raise ValueError('Subscription missing for invoice')
            # Proration invoices do not grant an entire additional monthly allowance.
            if obj.get('billing_reason') in ('subscription_create','subscription_cycle'):
                matches=[]
                for line in obj.get('lines',{}).get('data',[]):
                    price=line.get('price',{}).get('id') or line.get('pricing',{}).get('price_details',{}).get('price')
                    if price in price_map() and not line.get('proration'):
                        matches.append(price_map()[price])
                if len(matches)!=1:
                    raise ValueError('Invoice must contain one configured subscription price')
                plan,interval=matches[0]
                credits = PLANS[plan]['credits']*(12 if interval=='year' else 1)
                change(db,user['id'],credits,f'{plan.title()} {interval} credit allocation',f'invoice:{obj["id"]}')
            db.execute('INSERT OR IGNORE INTO payments VALUES(?,?,?,?,?,?,?)',
                       (obj['id'],user['id'],obj.get('amount_paid',0),obj.get('currency','usd'),'paid',
                        obj.get('hosted_invoice_url'),obj.get('created',time.time())))
            db.execute('DELETE FROM checkout_requests WHERE user_id=?',(user['id'],))
        if user and kind=='invoice.payment_failed':
            db.execute("UPDATE subscriptions SET status='past_due' WHERE user_id=?",(user['id'],))
        db.execute('INSERT INTO webhook_events VALUES(?,?)',(event['id'],time.time()))


@bp.post('/billing/webhook')
def webhook():
    configured()
    secret = current_app.config['STRIPE_WEBHOOK_SECRET']
    if not secret:
        abort(503,'Webhook is not configured.')
    try:
        event = stripe.Webhook.construct_event(request.get_data(),request.headers.get('Stripe-Signature',''),secret).to_dict()
    except (ValueError,stripe.SignatureVerificationError):
        abort(400,'Invalid webhook signature.')
    obj = event['data']['object']
    sub_id = obj.get('subscription') or (obj.get('parent') or {}).get('subscription_details',{}).get('subscription')
    if event['type'].startswith('customer.subscription.'):
        sub_id = obj['id']
    subscription = stripe.Subscription.retrieve(sub_id) if sub_id else None
    if subscription is not None and hasattr(subscription,'to_dict'):
        subscription = subscription.to_dict()
    apply_event(event,subscription)
    return jsonify(received=True)
