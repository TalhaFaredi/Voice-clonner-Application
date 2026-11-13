"""Run from backend/: python -m app.worker. Persisted queue, heartbeat and refunds."""
import logging
import threading
import time
import uuid
from . import create_app
from .models.database import rows, transaction
from .services.credits import change
from .services.files import user_dir


def fail_job(db,job,message):
    db.execute("UPDATE jobs SET status='failed',error=?,finished_at=? WHERE id=?",(message,time.time(),job['id']))
    change(db,job['user_id'],job['cost'],'Failed job refund',f'refund:{job["id"]}')
    if job['kind']=='clone':
        db.execute("UPDATE voices SET status='failed' WHERE id=?",(job['voice_id'],))


def recover_stale():
    with transaction() as db:
        for job in db.execute("SELECT * FROM jobs WHERE status='processing' AND heartbeat<?",(time.time()-180,)).fetchall():
            fail_job(db,job,'The audio worker stopped unexpectedly. Credits were returned; you can try again.')


def claim(worker_id):
    with transaction() as db:
        job = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if not job:
            return None
        db.execute("UPDATE jobs SET status='processing',lease_owner=?,heartbeat=? WHERE id=?",(worker_id,time.time(),job['id']))
        return dict(job)


def execute(job,engine):
    current = rows('SELECT status FROM jobs WHERE id=?',(job['id'],),one=True)
    if not current or current['status']!='processing':
        return
    try:
        folder = user_dir(job['user_id'],'voices',job['voice_id']) if job['voice_id'] else None
        duration = None
        if job['kind']=='clone':
            voice = rows('SELECT ref_text FROM voices WHERE id=?',(job['voice_id'],),one=True)
            engine.clone(folder,voice['ref_text'])
        else:
            output = user_dir(job['user_id'],'generated')/(job['id']+'.wav')
            duration = engine.generate(job,folder,output)
        with transaction() as db:
            current = db.execute('SELECT status FROM jobs WHERE id=?',(job['id'],)).fetchone()
            if current['status']!='processing':
                return
            db.execute("UPDATE jobs SET status='completed',duration=?,finished_at=? WHERE id=?",(duration,time.time(),job['id']))
            if job['kind']=='clone':
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
