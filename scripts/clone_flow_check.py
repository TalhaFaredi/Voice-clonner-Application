"""Live clone UX regression: real GPU sample, persistent cards, animations and routing.

Uses only the public synthetic demo in a new QA account, never a user's reference audio.
"""
import secrets
import tempfile
import uuid
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]


def main():
    chrome=next(p for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
                             Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')] if p.exists())
    output=ROOT/'backend'/'storage'/'qa';output.mkdir(parents=True,exist_ok=True)
    reference='Hello there. This is a clear synthetic voice sample for testing my new audio workspace. Every story begins with a little curiosity.'
    with tempfile.TemporaryDirectory(prefix='mellifon-clone-check-') as profile,sync_playwright() as p:
        context=p.chromium.launch_persistent_context(profile,executable_path=str(chrome),headless=True,
                 viewport={'width':1440,'height':1050})
        page=context.pages[0];errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://localhost:5173/#/register')
        page.locator('input[name=name]').fill('Clone flow QA')
        page.locator('input[name=email]').fill(f'clone-qa-{uuid.uuid4().hex[:12]}@example.com')
        page.locator('input[name=password]').fill(secrets.token_urlsafe(24))
        page.locator('#auth-form button').click()
        expect(page.locator('#generation-form')).to_be_visible(timeout=15000)
        page.locator('.sidebar nav a[href="#/clone"]').click()
        expect(page.locator('#clone-form')).to_be_visible()
        page.locator('#clone-form input[name=name]').fill('QA saved clone')
        page.locator('#sample').set_input_files(str(ROOT/'frontend'/'public'/'audio'/'preset-demo.wav'))
        expect(page.locator('#upload-preview')).to_be_visible()
        page.locator('#clone-form textarea[name=ref_text]').fill(reference)
        page.locator('#clone-form input[name=consent]').check()
        with page.expect_response(lambda r:r.url.endswith('/api/voices') and r.request.method=='POST') as response:
            page.locator('#clone-form button[type=submit]').click()
        job=response.value.json();assert response.value.status==202,job
        voice_id=job['voice_id'];card=page.locator(f'[data-voice-id="{voice_id}"]')
        expect(card).to_be_visible(timeout=15000)
        expect(page.locator('.clone-progress.is-active')).to_be_visible()
        assert page.locator('.progress-wave .bar').first.evaluate('(el) => getComputedStyle(el).animationName')=='voice-wave'
        print('Clone persisted immediately; real progress animation is running.',flush=True)
        page.reload()
        expect(card).to_be_visible(timeout=15000)
        expect(card.locator('h2')).to_have_text('QA saved clone')
        print('Saved clone and current job survive page reload.',flush=True)
        expect(card.locator('.voice-preview audio')).to_be_visible(timeout=240000)
        expect(page.locator('.clone-progress.is-complete')).to_be_visible()
        card.locator('.voice-preview audio').evaluate('(el) => el.load()')
        page.wait_for_function('() => document.querySelector(".voice-preview audio").readyState >= 1')
        page.screenshot(path=str(output/'clone-page-complete.png'),full_page=True)
        card.locator('.use-saved-voice').click()
        select=page.locator('#generation-form select[name=voice]')
        expect(select).to_have_value('clone:'+voice_id)
        expect(page.locator('#voice-selection-note')).to_contain_text('QA saved clone')
        expect(page.locator('#generation-form input[name=instruct]')).to_be_disabled()
        expect(page.locator('#active-job audio')).to_have_count(0)
        page.locator('#script').fill('This recording uses my saved voice clone, rather than a preset narrator.')
        with page.expect_response(lambda r:r.url.endswith('/api/generations') and r.request.method=='POST') as response:
            page.locator('#generation-form button[type=submit]').click()
        payload=response.value.request.post_data_json
        assert payload['voice_id']==voice_id and 'speaker' not in payload,payload
        print('Studio submitted the selected saved clone ID, without a preset speaker.',flush=True)
        expect(page.locator('#active-job audio')).to_be_visible(timeout=240000)
        expect(page.locator('#active-job')).to_contain_text('Saved clone: QA saved clone')
        page.screenshot(path=str(output/'studio-clone-result.png'),full_page=True)
        select.select_option('preset:ryan')
        expect(page.locator('#active-job audio')).to_have_count(0)
        page.locator('.sidebar nav a[href="#/clone"]').click()
        expect(card).to_be_visible()
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Clone page overflows on mobile'
        page.screenshot(path=str(output/'clone-page-mobile.png'),full_page=True)
        assert not errors,errors
        context.close()
    print('Clone flow passed: persistent storage, generated preview, reload recovery, animated progress, clone selection, real speech, source labeling, mobile layout.',flush=True)


if __name__=='__main__':main()
