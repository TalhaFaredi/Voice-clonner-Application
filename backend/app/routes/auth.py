import secrets
import sqlite3
import time
import uuid
import re
import smtplib
from email.message import EmailMessage
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from flask import Blueprint, abort, current_app, g, jsonify, request
from ..models.database import rows, transaction
from ..middleware.security import authenticated, digest, limit, public_user

bp = Blueprint('auth', __name__)
hasher = PasswordHasher()
# A fixed-cost comparison prevents a cheap user-enumeration timing shortcut.
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(24))


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, 'Send a JSON object.')
    return data


def password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 128:
        abort(400, 'Use a password between 12 and 128 characters.')
    return value


def field(data, key, maximum=120):
    value = data.get(key, '')
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        abort(400, f'Enter a valid {key}.')
    return value.strip()


def session(user):
    token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
    with transaction() as db:
        db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?)',
                   (digest(token), user['id'], csrf, time.time()+current_app.config['SESSION_DAYS']*86400))
    response = jsonify(user=public_user(user), csrf=csrf)
    response.set_cookie('voice_session', token, httponly=True, secure=current_app.config['APP_ENV']=='production',
                        samesite='Lax', max_age=current_app.config['SESSION_DAYS']*86400, path='/')
    return response


@bp.post('/auth/register')
def register():
    limit('register', 5, 3600)
    data = body()
    email, name = field(data,'email',254).lower(), field(data,'name')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        abort(400, 'Enter a valid email address.')
    hashed = hasher.hash(password(data.get('password')))
    user_id, now = uuid.uuid4().hex, time.time()
    try:
        with transaction() as db:
            db.execute('INSERT INTO users(id,email,name,password_hash,created_at) VALUES(?,?,?,?,?)',
                       (user_id,email,name,hashed,now))
            db.execute('INSERT INTO subscriptions(user_id) VALUES(?)',(user_id,))
            db.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',
                       (uuid.uuid4().hex,user_id,5000,'Welcome credits',f'welcome:{user_id}',now))
    except sqlite3.IntegrityError:
        abort(409, 'An account with this email already exists.')
    return session(rows('SELECT * FROM users WHERE id=?',(user_id,),one=True))


@bp.post('/auth/login')
def login():
    limit('login', 15, 900)
    data = body()
    email = field(data,'email',254).lower()
    user = rows('SELECT * FROM users WHERE email=?',(email,),one=True)
    supplied = data.get('password')
    if not isinstance(supplied,str) or len(supplied)>128:
        abort(401, 'Email or password is incorrect.')
    try:
        hasher.verify(user['password_hash'] if user else DUMMY_HASH, supplied)
    except (VerificationError, InvalidHashError):
        abort(401, 'Email or password is incorrect.')
    if not user:
        abort(401, 'Email or password is incorrect.')
    return session(user)


@bp.get('/auth/me')
@authenticated
def me():
    return jsonify(user=public_user(g.user), csrf=g.user['csrf'])


@bp.post('/auth/logout')
@authenticated
def logout():
    with transaction() as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?',(digest(request.cookies.get('voice_session','')),))
    response = jsonify(ok=True)
    response.delete_cookie('voice_session',path='/')
    return response


@bp.patch('/account')
@authenticated
def profile():
    data = body()
    with transaction() as db:
        db.execute('UPDATE users SET name=? WHERE id=?',(field(data,'name'),g.user['id']))
    return jsonify(user=public_user(rows('SELECT * FROM users WHERE id=?',(g.user['id'],),one=True)))


@bp.post('/account/password')
@authenticated
def change_password():
    data = body()
    try:
        hasher.verify(g.user['password_hash'], field(data,'current_password',128))
    except VerificationError:
        abort(400, 'Current password is incorrect.')
    hashed = hasher.hash(password(data.get('password')))
    with transaction() as db:
        db.execute('UPDATE users SET password_hash=? WHERE id=?',(hashed,g.user['id']))
        db.execute('DELETE FROM sessions WHERE user_id=?',(g.user['id'],))
    return session(rows('SELECT * FROM users WHERE id=?',(g.user['id'],),one=True))


@bp.post('/auth/forgot-password')
def forgot_password():
    limit('reset', 5, 900)
    data = body()
    user = rows('SELECT * FROM users WHERE email=?',(field(data,'email',254).lower(),),one=True)
    if not current_app.config['SMTP_HOST']:
        abort(503, 'Password-reset email is not configured. Contact the service administrator.')
    if user:
        token = secrets.token_urlsafe(40)
        with transaction() as db:
            db.execute('DELETE FROM resets WHERE user_id=?',(user['id'],))
            db.execute('INSERT INTO resets(token_hash,user_id,expires) VALUES(?,?,?)',
                       (digest(token),user['id'],time.time()+1800))
        message = EmailMessage()
        message['Subject'] = 'Reset your Sonora password'
        message['From'], message['To'] = current_app.config['SMTP_FROM'], user['email']
        message.set_content(f"Reset your password within 30 minutes:\n{current_app.config['PUBLIC_URL']}/#/reset?token={token}\n\nIf you didn't request this, ignore this email.")
        try:
            with smtplib.SMTP(current_app.config['SMTP_HOST'],current_app.config['SMTP_PORT'],timeout=15) as smtp:
                smtp.starttls()
                if current_app.config['SMTP_USER']:
                    smtp.login(current_app.config['SMTP_USER'],current_app.config['SMTP_PASSWORD'])
                smtp.send_message(message)
        except Exception:
            current_app.logger.exception('Password reset delivery failed')
    return jsonify(message='If that account exists, a reset link has been emailed.')


@bp.post('/auth/reset-password')
def reset_password():
    limit('reset-confirm', 10, 900)
    data = body()
    hashed = hasher.hash(password(data.get('password')))
    with transaction() as db:
        record = db.execute('SELECT * FROM resets WHERE token_hash=? AND used=0 AND expires>?',
                            (digest(field(data,'token',200)),time.time())).fetchone()
        if not record:
            abort(400, 'This reset link is invalid or expired.')
        db.execute('UPDATE resets SET used=1 WHERE user_id=?',(record['user_id'],))
        db.execute('UPDATE users SET password_hash=? WHERE id=?',(hashed,record['user_id']))
        db.execute('DELETE FROM sessions WHERE user_id=?',(record['user_id'],))
    return jsonify(message='Password updated. You can now sign in.')
