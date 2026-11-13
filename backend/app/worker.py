"""Run from backend/: python -m app.worker. Persisted queue, heartbeat and refunds."""
import logging
import threading
import time
import uuid
import shutil
from flask import current_app
from . import create_app
from .models.database import rows, transaction
from .services.credits import change
from .services.files import user_dir


def fail_job(db,job,message):
    db.execute("UPDATE jobs SET status='failed',phase='failed',error=?,finished_at=? WHERE id=?",(message,time.time(),job['id']))
    change(db,job['user_id'],job['cost'],'Failed job refund',f'refund:{job["id"]}')
    if job['kind']=='rebuild':
        folder=user_dir(job['user_id'],'voices',job['voice_id'])
        if (folder/'prompt.previous.pt').exists():shutil.copyfile(folder/'prompt.previous.pt',folder/'prompt.pt')
        if (folder/'preview.previous.wav').exists():shutil.copyfile(folder/'preview.previous.wav',folder/'preview.wav')
        db.execute('UPDATE voices SET status=? WHERE id=?',('ready' if (folder/'prompt.pt').exists() else 'failed',job['voice_id']))
    elif job['kind']=='clone':
        db.execute("UPDATE voices SET status='failed' WHERE id=?",(job['voice_id'],))
    elif job['kind']=='preview':
        db.execute('UPDATE voices SET preview_error=? WHERE id=?',
                   ('The sample could not be generated. Your saved voice is still available in the studio.',job['voice_id']))


def recover_stale():
    with transaction() as db:
        for job in db.execute("SELECT * FROM jobs WHERE status='processing' AND heartbeat<?",(time.time()-180,)).fetchall():
            fail_job(db,job,'The audio worker stopped unexpectedly. Credits were returned; you can try again.')


def claim(worker_id):
    with transaction() as db:
        job = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if not job:
            return None
        db.execute("UPDATE jobs SET status='processing',phase='preparing',progress=10,lease_owner=?,heartbeat=? WHERE id=?",(worker_id,time.time(),job['id']))
        return dict(job)


def progress_job(job,phase,percent):
    with transaction() as db:
        db.execute("UPDATE jobs SET phase=?,progress=? WHERE id=? AND status='processing'",(phase,percent,job['id']))


def execute(job,engine):
    current = rows('SELECT status FROM jobs WHERE id=?',(job['id'],),one=True)
    if not current or current['status']!='processing':
        return
    try:
        folder = user_dir(job['user_id'],'voices',job['voice_id']) if job['voice_id'] else None
        duration = None
        if job['kind'] in ('clone','rebuild'):
            voice = rows('SELECT ref_text,preview_text FROM voices WHERE id=?',(job['voice_id'],),one=True)
            ref_text=job['text'] if job['kind']=='rebuild' else voice['ref_text']
            if job['kind']=='rebuild' and (folder/'prompt.pt').exists():shutil.copyfile(folder/'prompt.pt',folder/'prompt.previous.pt')
            if job['kind']=='rebuild' and (folder/'preview.wav').exists():(folder/'preview.wav').replace(folder/'preview.previous.wav')
            progress_job(job,'building_voice',30)
            engine.clone(folder,ref_text)
            # An actual synthesis preview, not a replay of the uploaded reference recording.
            preview_text=voice['preview_text'] or current_app.config['CLONE_PREVIEW_TEXT']
            progress_job(job,'creating_preview',65)
            preview_error=None
            try:
                preview_job=dict(job,kind='preview',text=preview_text,language='auto',instruct='')
                duration=engine.generate(preview_job,folder,folder/'preview.wav')
            except Exception:
                logging.exception('Preview failed for saved voice %s',job['voice_id'])
                preview_error='Voice saved, but the short sample did not complete. Check that the reference transcript matches the recording, then try a script in the studio.'
            with transaction() as db:
                db.execute('UPDATE voices SET preview_text=?,preview_duration=?,preview_error=? WHERE id=?',
                           (preview_text,duration,preview_error,job['voice_id']))
        else:
            output = folder/'preview.wav' if job['kind']=='preview' else user_dir(job['user_id'],'generated')/(job['id']+'.wav')
            duration = engine.generate(job,folder,output,
                       progress=lambda i,n:progress_job(job,'synthesizing',20+int(65*i/n)))
            if job['kind']=='preview':
                with transaction() as db:
                    db.execute('UPDATE voices SET preview_text=?,preview_duration=?,preview_error=NULL WHERE id=?',
                               (job['text'],duration,job['voice_id']))
        progress_job(job,'saving',95)
        with transaction() as db:
            current = db.execute('SELECT status FROM jobs WHERE id=?',(job['id'],)).fetchone()
            if current['status']!='processing':
                return
            db.execute("UPDATE jobs SET status='completed',phase='complete',progress=100,duration=?,finished_at=? WHERE id=?",(duration,time.time(),job['id']))
            if job['kind']=='rebuild':
                db.execute('UPDATE voices SET original_ref_text=coalesce(original_ref_text,ref_text),ref_text=?,clone_mode=? WHERE id=?',
                           (ref_text,job['clone_mode'],job['voice_id']))
            if job['kind'] in ('clone','rebuild'):
                db.execute("UPDATE voices SET status='ready' WHERE id=?",(job['voice_id'],))
    except Exception:
        logging.exception('Audio job %s failed',job['id'])
        with transaction() as db:
            if db.execute('SELECT status FROM jobs WHERE id=?',(job['id'],)).fetchone()['status']=='processing':
                fail_job(db,job,'Audio processing failed. Your credits have been returned.')


def main():
    app = create_app()
    identifier = uuid.uuid4().hex
    stop = threading.Event()
    state = {'status':'loading','error':None}
    def heartbeat():
        with app.app_context():
            while not stop.is_set():
                with transaction() as db:
                    now = time.time()
                    db.execute('INSERT OR REPLACE INTO worker_status VALUES(?,?,?,?)',
                               (identifier,state['status'],now,state['error']))
                    db.execute("UPDATE jobs SET heartbeat=? WHERE lease_owner=? AND status='processing'",(now,identifier))
                stop.wait(15)
    threading.Thread(target=heartbeat,daemon=True).start()
    try:
        from .services.engine import QwenEngine
        engine = QwenEngine(app.config)
        state['status']='ready'
        with app.app_context():
            while True:
                recover_stale()
                job = claim(identifier)
                if job:
                    execute(job,engine)
                else:
                    time.sleep(1)
    except KeyboardInterrupt:
        pass
    except Exception:
        state.update(status='error',error='Voice models could not load. Check worker logs and GPU configuration.')
        logging.exception('Worker stopped')
        with app.app_context(),transaction() as db:
            db.execute('INSERT OR REPLACE INTO worker_status VALUES(?,?,?,?)',
                       (identifier,state['status'],time.time(),state['error']))
        raise
    finally:
        stop.set()


if __name__=='__main__':
    main()
