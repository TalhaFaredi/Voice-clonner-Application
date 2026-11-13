import hashlib
import json
import re
import shutil
import time
import uuid
from flask import Blueprint, abort, current_app, g, jsonify, request, send_from_directory
from .auth import body, field
from ..middleware.security import authenticated, limit
from ..models.database import rows, transaction
from ..services.credits import change
from ..services.files import user_dir, validate_sample

bp = Blueprint('library', __name__)
LANGUAGES = ['auto','chinese','english','japanese','korean','german','french','russian','portuguese','spanish','italian']
SPEAKERS = ['aiden','dylan','eric','ono_anna','ryan','serena','sohee','uncle_fu','vivian']


def owned_voice(identifier):
    voice = rows('SELECT * FROM voices WHERE id=? AND user_id=? AND deleted=0',(identifier,g.user['id']),one=True)
    if not voice:
        abort(404,'Voice not found.')
    return voice


def request_key():
    key = request.headers.get('Idempotency-Key','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{16,100}',key):
        abort(400,'A unique Idempotency-Key header is required.')
    return key


def existing(key, fingerprint):
    job = rows('SELECT * FROM jobs WHERE user_id=? AND idempotency_key=?',(g.user['id'],key),one=True)
    if job and job['fingerprint'] != fingerprint:
        abort(409,'This request key was already used for different input.')
    return job


def insert_job(db, identifier, key, fingerprint, cost, kind, voice_id=None, text='', language='auto', speaker=None, instruct=''):
    change(db,g.user['id'],-cost,f'{kind.title()} reservation',f'job:{identifier}')
    db.execute('INSERT INTO jobs(id,user_id,kind,voice_id,text,language,speaker,instruct,status,cost,idempotency_key,fingerprint,created_at) '
               'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(identifier,g.user['id'],kind,voice_id,text,language,speaker,instruct,
                                                    'queued',cost,key,fingerprint,time.time()))


@bp.get('/studio/options')
def options():
    worker = rows('SELECT * FROM worker_status ORDER BY heartbeat DESC LIMIT 1',one=True)
    return jsonify(languages=LANGUAGES,speakers=SPEAKERS,clone_cost=1000,credits_per_character=1,
                   worker=worker if worker and worker['heartbeat']>time.time()-120 else None)


@bp.get('/dashboard')
@authenticated
def dashboard():
    user = g.user['id']
    return jsonify(credits=g.user['credits'], low_credits=g.user['credits']<1000,
                   voice_count=rows('SELECT count(*) AS n FROM voices WHERE user_id=? AND deleted=0',(user,),one=True)['n'],
                   generation_count=rows("SELECT count(*) AS n FROM jobs WHERE user_id=? AND kind='generate' AND status='completed' AND deleted=0",(user,),one=True)['n'],
                   characters_used=rows("SELECT coalesce(sum(cost),0) AS n FROM jobs WHERE user_id=? AND kind='generate' AND status='completed'",(user,),one=True)['n'],
                   recent_jobs=rows('SELECT * FROM jobs WHERE user_id=? AND deleted=0 ORDER BY created_at DESC LIMIT 6',(user,)))


@bp.get('/voices')
@authenticated
def voices():
    return jsonify(rows('SELECT * FROM voices WHERE user_id=? AND deleted=0 ORDER BY created_at DESC',(g.user['id'],)))


@bp.post('/voices')
@authenticated
def clone():
    limit('clone',10,3600)
    if request.form.get('consent') != 'true':
        abort(400,'Confirm that you own this voice or have permission to clone it.')
    name = field(request.form,'name',80)
    ref_text = request.form.get('ref_text','').strip()
    if len(ref_text)>4000:
        abort(400,'Reference transcript is too long.')
    upload = request.files.get('audio')
    if not upload or not upload.filename:
        abort(400,'Upload a voice sample.')
    key = request_key()
    # Include content identity, so reusing a key with a different sample is rejected.
    audio_bytes = upload.read()
    upload.seek(0)
    fingerprint = hashlib.sha256(audio_bytes+name.encode()+ref_text.encode()).hexdigest()
    prior = existing(key,fingerprint)
    if prior:
        return jsonify(prior),200
    voice_id, job_id = uuid.uuid4().hex, uuid.uuid4().hex
    directory = user_dir(g.user['id'],'voices',voice_id)
    try:
        validate_sample(upload,directory)
        with transaction() as db:
            prior = db.execute('SELECT * FROM jobs WHERE user_id=? AND idempotency_key=?',(g.user['id'],key)).fetchone()
            if prior:
                if prior['fingerprint'] != fingerprint:
                    abort(409,'This request key was already used for different input.')
                shutil.rmtree(directory)
                return jsonify(dict(prior)),200
            if db.execute('SELECT count(*) FROM voices WHERE user_id=? AND deleted=0',(g.user['id'],)).fetchone()[0]>=50:
                abort(400,'Your library is limited to 50 voices.')
            db.execute('INSERT INTO voices VALUES(?,?,?,?,?,?,?,0)',
                       (voice_id,g.user['id'],name,ref_text,'queued',time.time(),time.time()))
            insert_job(db,job_id,key,fingerprint,1000,'clone',voice_id)
        return jsonify(rows('SELECT * FROM jobs WHERE id=?',(job_id,),one=True)),202
    except Exception:
        if directory.exists():
            shutil.rmtree(directory)
        raise


@bp.patch('/voices/<identifier>')
@authenticated
def rename_voice(identifier):
    owned_voice(identifier)
    with transaction() as db:
        db.execute('UPDATE voices SET name=? WHERE id=? AND user_id=?',(field(body(),'name',80),identifier,g.user['id']))
    return jsonify(ok=True)


@bp.delete('/voices/<identifier>')
@authenticated
def delete_voice(identifier):
    owned_voice(identifier)
    with transaction() as db:
        if db.execute("SELECT 1 FROM jobs WHERE voice_id=? AND status IN ('queued','processing')",(identifier,)).fetchone():
            abort(409,'Wait for this voice’s current job to finish before deleting it.')
        db.execute('UPDATE voices SET deleted=1 WHERE id=? AND user_id=?',(identifier,g.user['id']))
    shutil.rmtree(user_dir(g.user['id'],'voices',identifier))
    return jsonify(ok=True)


@bp.post('/generations')
@authenticated
def generate():
    limit('generate',30,3600)
    data = body()
    text = field(data,'text',5000)
    voice_id = data.get('voice_id') or None
    speaker = data.get('speaker','ryan')
    language = data.get('language','auto')
    instruct = data.get('instruct','')
    if not isinstance(instruct,str) or len(instruct)>500:
        abort(400,'Style instruction must be under 500 characters.')
    if language not in LANGUAGES or (not voice_id and speaker not in SPEAKERS):
        abort(400,'Select a supported language and voice.')
    key = request_key()
    fingerprint = hashlib.sha256(json.dumps([voice_id,speaker,text,language,instruct]).encode()).hexdigest()
    identifier = uuid.uuid4().hex
    with transaction() as db:
        prior = db.execute('SELECT * FROM jobs WHERE user_id=? AND idempotency_key=?',(g.user['id'],key)).fetchone()
        if prior:
            if prior['fingerprint'] != fingerprint:
                abort(409,'This request key was already used for different input.')
            return jsonify(dict(prior)),200
        if voice_id:
            voice = db.execute("SELECT * FROM voices WHERE id=? AND user_id=? AND deleted=0 AND status='ready'",(voice_id,g.user['id'])).fetchone()
            if not voice:
                abort(404,'Ready voice not found.')
        if db.execute("SELECT count(*) FROM jobs WHERE user_id=? AND status IN ('queued','processing')",(g.user['id'],)).fetchone()[0]>=5:
            abort(429,'You already have five jobs in progress.')
        insert_job(db,identifier,key,fingerprint,len(text),'generate',voice_id,text,language,speaker,instruct)
    return jsonify(rows('SELECT * FROM jobs WHERE id=?',(identifier,),one=True)),202


@bp.get('/jobs')
@authenticated
def job_list():
    page = max(0,min(request.args.get('page',0,type=int),100000))
    return jsonify(rows('SELECT * FROM jobs WHERE user_id=? AND deleted=0 ORDER BY created_at DESC LIMIT 30 OFFSET ?',
                        (g.user['id'],page*30)))


@bp.get('/jobs/<identifier>')
@authenticated
def get_job(identifier):
    job = rows('SELECT * FROM jobs WHERE id=? AND user_id=? AND deleted=0',(identifier,g.user['id']),one=True)
    if not job:
        abort(404,'Job not found.')
    return jsonify(job)


@bp.delete('/jobs/<identifier>')
@authenticated
def delete_job(identifier):
    with transaction() as db:
        job = db.execute('SELECT * FROM jobs WHERE id=? AND user_id=? AND deleted=0',(identifier,g.user['id'])).fetchone()
        if not job:
            abort(404,'Job not found.')
        if job['status'] in ('queued','processing'):
            abort(409,'Wait for this job to finish.')
        db.execute('UPDATE jobs SET deleted=1 WHERE id=?',(identifier,))
    (user_dir(g.user['id'],'generated')/(identifier+'.wav')).unlink(missing_ok=True)
    return jsonify(ok=True)


@bp.get('/audio/<category>/<identifier>')
@authenticated
def audio(category,identifier):
    if category == 'voice':
        owned_voice(identifier)
        directory,name = user_dir(g.user['id'],'voices',identifier),'reference.wav'
    elif category == 'generation':
        job = rows("SELECT * FROM jobs WHERE id=? AND user_id=? AND status='completed' AND kind='generate' AND deleted=0",
                   (identifier,g.user['id']),one=True)
        if not job:
            abort(404,'Audio not found.')
        directory,name = user_dir(g.user['id'],'generated'),identifier+'.wav'
    else:
        abort(404)
    return send_from_directory(directory,name,mimetype='audio/wav',as_attachment=request.args.get('download')=='1')
