"""Real browser/GPU correction check, scoped to the synthetic Clone flow QA account."""
import sys
import tempfile
from pathlib import Path
from http.cookies import SimpleCookie
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app import create_app
from app.models.database import rows
from app.routes.auth import session as issue_session


def main():
    app=create_app()
    with app.test_request_context():
        user=rows("SELECT * FROM users WHERE name='Clone flow QA' AND email LIKE 'clone-qa-%@example.com' ORDER BY created_at DESC LIMIT 1",one=True)
        if not user:raise ValueError('Run clone_flow_check.py first.')
        voice=rows('SELECT * FROM voices WHERE user_id=? AND deleted=0 ORDER BY created_at DESC LIMIT 1',(user['id'],),one=True)
        response=issue_session(user)
        cookie=SimpleCookie();cookie.load(response.headers['Set-Cookie'])
        token=cookie['voice_session'].value
    chrome=next(p for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
                           Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')] if p.exists())
    with tempfile.TemporaryDirectory(prefix='clone-rebuild-check-') as profile,sync_playwright() as p:
        context=p.chromium.launch_persistent_context(profile,executable_path=str(chrome),headless=True)
        context.add_cookies([dict(name='voice_session',value=token,url='http://localhost:5173',httpOnly=True,sameSite='Lax')])
        page=context.pages[0];errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://localhost:5173/#/clone')
        card=page.locator(f'[data-voice-id="{voice["id"]}"]')
        expect(card).to_be_visible(timeout=15000)
        card.get_by_text('Correct transcript / rebuild voice',exact=True).click()
        form=card.locator('.rebuild-voice-form')
        form.locator('select').select_option('speaker_embedding')
        form.locator('select').select_option('text_conditioned')
        form.locator('textarea').fill(voice['ref_text'])
        with page.expect_response(lambda r:'/rebuild' in r.url and r.request.method=='POST') as pending:
            form.locator('button[type=submit]').click()
        response=pending.value;data=response.json()
        assert response.status==202,data
        assert data['cost']==0 and data['voice_id']==voice['id']
        print('Existing QA voice correction queued without charging or changing its ID.',flush=True)
        expect(card.locator('.badge')).to_have_text('Saved & ready',timeout=180000)
        expect(card.locator('.voice-preview audio')).to_be_visible()
        assert not errors,errors
        page.screenshot(path=str(ROOT/'backend'/'storage'/'qa'/'rebuild-complete.png'),full_page=True)
        context.close()
    with app.app_context():
        current=rows('SELECT * FROM users WHERE id=?',(user['id'],),one=True)
        assert current['credits']==user['credits']
    print('Correction passed: same private voice, preserved recording, generated preview, unchanged credits, no browser errors.',flush=True)


if __name__=='__main__':main()
