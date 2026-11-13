"""Actual browser/API smoke test. Creates its own local QA account; no payment calls."""
import secrets
import tempfile
import time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]


def main():
    output=ROOT/'backend'/'storage'/'qa'
    output.mkdir(parents=True,exist_ok=True)
    chrome=next(p for p in [Path('C:/Program Files/Google/Chrome/Application/chrome.exe'),
                            Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe')] if p.exists())
    with tempfile.TemporaryDirectory(prefix='sonora-browser-') as profile,sync_playwright() as p:
        context=p.chromium.launch_persistent_context(profile,executable_path=str(chrome),headless=True,
                    viewport={'width':1440,'height':1050})
        page=context.pages[0];errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://localhost:5173')
        expect(page.locator('.hero h1')).to_contain_text('Great ideas deserve')
        expect(page.locator('audio')).to_have_count(2)
        page.locator('audio').first.evaluate('(audio) => audio.load()')
        page.wait_for_function("() => document.querySelector('audio').readyState >= 1")
        page.screenshot(path=str(output/'landing-desktop.png'),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile landing page overflows'
        page.screenshot(path=str(output/'landing-mobile.png'),full_page=True)
        page.set_viewport_size({'width':1440,'height':1050})
        page.goto('http://localhost:5173/#/register')
        page.locator('input[name=name]').fill('Alex Morgan')
        page.locator('input[name=email]').fill(f'qa-{int(time.time())}@example.com')
        page.locator('input[name=password]').fill(secrets.token_urlsafe(24))
        page.locator('#auth-form button').click()
        expect(page.locator('.dashboard h1')).to_contain_text('Hello, Alex',timeout=15000)
        expect(page.locator('#generation-form')).to_be_visible()
        page.locator('#script').fill('A new idea. A familiar voice. This is where a good story begins.')
        expect(page.locator('#char-count')).to_have_text('64')
        page.screenshot(path=str(output/'studio-desktop.png'),full_page=True)
        for name,route in [('voice library','voices'),('clone a voice','clone'),('history','history'),('plan & usage','billing'),('settings','settings')]:
            page.locator(f'.sidebar nav a[href="#/{route}"]').click()
            expect(page.locator('.dashboard h1')).to_be_visible()
            page.wait_for_timeout(200)
            if route=='clone':expect(page.locator('#clone-form')).to_be_visible()
            if route=='billing':expect(page.locator('.billing-summary')).to_be_visible()
            page.screenshot(path=str(output/(route+'-desktop.png')),full_page=True)
        page.set_viewport_size({'width':390,'height':844})
        page.locator('.sidebar a[href="#/studio"]').click()
        expect(page.locator('#generation-form')).to_be_visible()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Mobile studio overflows'
        page.screenshot(path=str(output/'studio-mobile.png'),full_page=True)
        page.locator('[data-action=logout]').click()
        expect(page.locator('.hero h1')).to_be_visible()
        page.goto('http://localhost:5173/#/studio')
        expect(page.locator('#auth-form')).to_be_visible()
        assert not errors,errors
        context.close()
    print('Browser check passed: real registration/session, dashboard, studio, private library, cloning UI, history, billing, settings, logout, access gate, responsive layout.')
    print(f'Screenshots: {output}')


if __name__=='__main__':main()
