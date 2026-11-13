"""Local upgrade helper: queue included samples for explicitly selected saved voices.

Run from the project root with --voice-id <id> (repeatable). This is not an HTTP endpoint.
No voice is re-cloned, deleted, published or charged additional credits.
"""
import argparse
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from flask import g
from app import create_app
from app.models.database import rows
from app.routes.library import preview_voice


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--voice-id',action='append',required=True)
    args=parser.parse_args()
    app=create_app()
    for identifier in args.voice_id:
        with app.test_request_context('/api/voices/'+identifier+'/preview',method='POST',json={}):
            voice=rows("SELECT * FROM voices WHERE id=? AND deleted=0 AND status='ready'",(identifier,),one=True)
            if not voice:raise ValueError('A selected saved voice is unavailable.')
            g.user=rows('SELECT * FROM users WHERE id=?',(voice['user_id'],),one=True)
            result=preview_voice(identifier)
            response=result[0] if isinstance(result,tuple) else result
            data=response.get_json()
            print(identifier,'already ready' if data.get('already_ready') else data['status'],flush=True)


if __name__=='__main__':main()
