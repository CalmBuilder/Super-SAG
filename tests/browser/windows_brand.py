"""Browser regression of desktop branding with synthetic native responses.

This exercises the shared frontend in Chromium. It is not a Windows, installer,
filesystem, search, model, or upgrade acceptance test.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get('SAG_DESKTOP_BRAND_EVIDENCE_DIR', ROOT / '.cache/desktop-brand')).resolve()
REFERENCE = (ROOT / 'pros').resolve()
if OUTPUT == REFERENCE or REFERENCE in OUTPUT.parents:
    raise SystemExit('Evidence cannot be written inside the reference checkout.')
OUTPUT.mkdir(parents=True, exist_ok=True)
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
origin = f'http://127.0.0.1:{port}'
fixture = (ROOT / 'tests/visual/fixture.js').read_text()
observe = """\nwindow.__TEST_COMMANDS__=[];\nconst originalInvoke=window.__TAURI_INTERNALS__.invoke;\nwindow.__TAURI_INTERNALS__.invoke=(command,args)=>{window.__TEST_COMMANDS__.push(command);return originalInvoke(command,args)};\n"""
results = []
errors = []
with tempfile.TemporaryFile(mode='w+') as log:
    process = subprocess.Popen([str(ROOT / 'node_modules/.bin/vite'), '--host', '127.0.0.1', '--port', str(port), '--strictPort'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(150):
            if process.poll() is not None:
                raise RuntimeError('Vite exited before browser testing.')
            try:
                with urlopen(origin, timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, URLError):
                time.sleep(.2)
        else:
            raise RuntimeError('Vite did not start within 30 seconds.')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
            for language, settings, about in [('zh-CN','设置','关于'),('en','Settings','About')]:
                for width, height, theme in [(960,600,'light'), (1280,720,'light'), (1920,1080,'dark')]:
                    context = browser.new_context(viewport={'width':width,'height':height}, locale=language, reduced_motion='reduce')
                    context.add_init_script(fixture + observe)
                    page = context.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(f'{origin}/?fixture=conversation&lang={language}&theme={theme}', wait_until='networkidle')
                    expect(page.locator('.brand')).to_have_text('Super-SAG')
                    assert page.title() == 'Super-SAG'
                    assert page.locator('.brand-row .brand-mark').evaluate('(image)=>image.complete && image.naturalWidth > 0')
                    if width == 1280:
                        page.screenshot(path=str(OUTPUT / f'home-{language}.png'))
                    page.get_by_role('button', name=settings, exact=True).click()
                    dialog = page.get_by_role('dialog')
                    expect(dialog).to_be_visible()
                    dialog.get_by_role('button', name=about, exact=True).click()
                    expect(dialog.locator('.settings-about h3')).to_have_text('Super-SAG')
                    expect(dialog.locator('.settings-about-version')).to_have_text('v' + json.loads((ROOT / 'package.json').read_text())['version'])
                    assert dialog.locator('.settings-about .brand-mark').evaluate('(image)=>image.complete && image.naturalWidth > 0')
                    expect(dialog.locator('.app-updates button')).to_have_count(0)
                    assert 'check_app_update' not in page.evaluate('window.__TEST_COMMANDS__')
                    if width == 1280:
                        page.screenshot(path=str(OUTPUT / f'about-{language}.png'))
                    results.append({'language':language,'width':width,'height':height,'theme':theme,'status':'passed'})
                    context.close()
                context = browser.new_context(viewport={'width':1280,'height':720}, locale=language, reduced_motion='reduce')
                context.add_init_script(fixture + observe + "\nlocalStorage.removeItem('sag.onboarding.seen');\n")
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'{origin}/?lang={language}', wait_until='networkidle')
                dialog = page.get_by_role('dialog')
                expect(dialog).to_be_visible()
                expect(dialog.locator('.onboarding-header b')).to_have_text('Super-SAG')
                assert dialog.locator('.onboarding-header img').evaluate('(image)=>image.complete && image.naturalWidth > 0')
                results.append({'language':language,'case':'first-run guide','status':'passed'})
                context.close()
            assert not errors, errors
            browser_version = browser.version
            browser.close()
        files=['src/App.svelte','src/components/Settings.svelte','src/components/Onboarding.svelte','src/components/AppUpdates.svelte','src/components/UpdateNotification.svelte','src/lib/icons.ts','src/lib/updates.ts','src/lib/locales/en.json','src-tauri/tauri.conf.json','assets/branding/super-sag-icon.svg','tests/visual/fixture.js','tests/browser/windows_brand.py']
        result={'scope':'Chromium desktop frontend with synthetic Tauri fixture; not native Windows or business acceptance',
                'browser':browser_version,'checks':results,'page_errors':errors,
                'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
                'screenshots':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUTPUT.glob('*.png'))}}
        (OUTPUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'checks':len(results),'browser':browser_version,'output':str(OUTPUT)},ensure_ascii=False))
    finally:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
