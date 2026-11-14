"""Opt-in real Qwen roundtrip. Uses a synthetic preset sample as the clone reference."""
import secrets
import time
import uuid
import sys
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
BASE='http://localhost:8010/api'


def browser_verify(session,output):
    from playwright.sync_api import sync_playwright,expect
    import tempfile
    chrome=next(p for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
                Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')] if p.exists())
    with tempfile.TemporaryDirectory(prefix='mellifon-audio-browser-') as profile,sync_playwright() as p:
        context=p.chromium.launch_persistent_context(profile,executable_path=str(chrome),headless=True,
                    viewport={'width':1440,'height':1050})
        context.add_cookies([{'name':'voice_session','value':session.cookies.get('voice_session'),
                             'url':'http://localhost:5173','httpOnly':True,'sameSite':'Lax'}])
        page=context.pages[0]
        page.goto('http://localhost:5173/#/history')
        expect(page.locator('audio')).to_have_count(2,timeout=15000)
        page.locator('audio').first.evaluate('(audio) => audio.load()')
        page.wait_for_function("() => document.querySelector('audio').readyState >= 1")
        assert page.locator('audio').first.evaluate('(audio) => audio.duration')>0
        page.screenshot(path=str(output/'real-generation-history.png'),full_page=True)
        page.goto('http://localhost:5173/#/voices')
        expect(page.locator('.voice-card h2')).to_have_text('Synthetic QA voice')
        page.screenshot(path=str(output/'real-voice-library.png'),full_page=True)
        context.close()
    print('Browser verified private audio metadata/playback source and the saved clone library.',flush=True)


def main():
    session=requests.Session()
    output=ROOT/'backend'/'storage'/'qa'
    if '--browser-only' in sys.argv:
        # Local QA helper, not an HTTP endpoint: only the synthetic account created by this test.
        # No credentials are persisted. This avoids rerunning GPU work to check browser playback.
        from http.cookies import SimpleCookie
        sys.path.insert(0,str(ROOT/'backend'))
        from app import create_app
        from app.models.database import rows
        from app.routes.auth import session as issue_session
        app=create_app()
        with app.test_request_context():
            user=rows("SELECT * FROM users WHERE name='Inference QA' AND email LIKE 'inference-%@example.com' ORDER BY created_at DESC LIMIT 1",one=True)
            if not user:raise RuntimeError('Run the real inference check first.')
            response=issue_session(user)
            cookie=SimpleCookie();cookie.load(response.headers['Set-Cookie'])
            session.cookies.set('voice_session',cookie['voice_session'].value)
        browser_verify(session,output)
        return
    def call(path,method='GET',**kwargs):
        response=session.request(method,BASE+path,timeout=60,**kwargs)
        if response.status_code>=400:raise RuntimeError(f'{path}: {response.status_code} {response.text[:500]}')
        return response
    options=call('/studio/options').json()
    if not options['worker'] or options['worker']['status']!='ready':
        raise RuntimeError('Start the audio worker and wait for its ready heartbeat first.')
    registration=call('/auth/register','POST',json={'name':'Inference QA','email':f'inference-{uuid.uuid4().hex[:12]}@example.com',
                      'password':secrets.token_urlsafe(24)}).json()
    session.headers['X-CSRF-Token']=registration['csrf']
    def wait(job):
        deadline=time.monotonic()+600
        last=None
        while time.monotonic()<deadline:
            data=call('/jobs/'+job['id']).json()
            if data['status']!=last:print(f"{data['kind']}: {data['status']}",flush=True);last=data['status']
            if data['status']=='failed':raise RuntimeError(data['error'])
            if data['status']=='completed':return data
            time.sleep(2)
        raise TimeoutError('The Qwen job is still running. Check its saved job state.')
    script='Hello there. This is a clear synthetic voice sample for testing my new audio workspace. Every story begins with a little curiosity.'
    job=call('/generations','POST',json={'text':script,'speaker':'ryan','language':'english'},headers={'Idempotency-Key':uuid.uuid4().hex}).json()
    finished=wait(job)
    reference=call('/audio/generation/'+finished['id']).content
    output.mkdir(parents=True,exist_ok=True)
    (output/'real-preset.wav').write_bytes(reference)
    job=call('/voices','POST',data={'name':'Synthetic QA voice','ref_text':script,'consent':'true'},
             files={'audio':('synthetic-reference.wav',reference,'audio/wav')},headers={'Idempotency-Key':uuid.uuid4().hex}).json()
    clone=wait(job)
    job=call('/generations','POST',json={'text':'Welcome to Mellifon. This recording was generated with a saved voice clone in my private workspace.',
             'voice_id':clone['voice_id'],'language':'english'},headers={'Idempotency-Key':uuid.uuid4().hex}).json()
    speech=wait(job)
    (output/'real-cloned-speech.wav').write_bytes(call('/audio/generation/'+speech['id']).content)
    balance=call('/auth/me').json()['user']['credits']
    expected=5000-len(script)-1000-len(job['text'])
    assert balance==expected,(balance,expected)
    assert reference.startswith(b'RIFF')
    # Verify actual private generated audio also loads in the browser, using this QA session.
    try:
        browser_verify(session,output)
    except ImportError:
        print('Playwright not installed; browser audio verification skipped.',flush=True)
    print(f'Real inference roundtrip passed. Balance: {balance}. Audio: {output}',flush=True)


if __name__=='__main__':main()
