import hashlib
import secrets
import time
from functools import wraps
from flask import abort, current_app, g, request
from ..models.database import rows, transaction


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def before_request():
    if request.method == 'OPTIONS':
        return '', 204
    origin = request.headers.get('Origin')
    if origin and origin not in current_app.config['ALLOWED_ORIGINS']:
        abort(403, 'This origin is not allowed.')
    token = request.cookies.get('voice_session', '')
    g.user = rows('SELECT u.*,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id '
                  'WHERE s.token_hash=? AND s.expires>?', (digest(token), time.time()), one=True) if token else None
    if g.user and request.method not in ('GET', 'HEAD') and request.path != '/api/billing/webhook':
        if not secrets.compare_digest(request.headers.get('X-CSRF-Token', ''), g.user['csrf']):
            abort(403, 'Session verification failed. Reload and try again.')


def authenticated(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not g.user:
            abort(401, 'Please sign in to continue.')
        return function(*args, **kwargs)
    return wrapped


def limit(bucket, count=20, seconds=60):
    key = f'{bucket}:{request.remote_addr}'
    with transaction() as db:
        now = time.time()
        db.execute('DELETE FROM rate_limits WHERE expires<?', (now,))
        record = db.execute('SELECT count FROM rate_limits WHERE key=?', (key,)).fetchone()
        if record and record['count'] >= count:
            abort(429, 'Too many requests. Please try again shortly.')
        db.execute('INSERT INTO rate_limits VALUES(?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1',
                   (key, now+seconds))


def public_user(user):
    return {k: user[k] for k in ('id','email','name','credits','created_at')}
