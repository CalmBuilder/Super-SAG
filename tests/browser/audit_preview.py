"""Reproduce unresolved visual-preview defects with isolated synthetic data.

The script returns a non-zero exit code while any finding remains. It starts a
loopback Vite server with a temporary cache and uses fresh Chromium profiles;
it does not modify the pinned reference tree or access real knowledge bases.
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
from urllib.request import urlopen

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(os.environ.get('SAG_AUDIT_EVIDENCE_DIR', ROOT / '.cache/preview-audit'))
REFERENCE = (ROOT / 'pros/SAG-Wiki').resolve()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main() -> int:
    target = EVIDENCE.resolve()
    if target == REFERENCE or REFERENCE in target.parents:
        raise SystemExit('Evidence must not be written into the static reference.')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    port = free_port()
    origin = f'http://127.0.0.1:{port}'
    with tempfile.TemporaryDirectory(prefix='super-sag-preview-audit-') as dirname:
        tmp = Path(dirname)
        config = tmp / 'vite.config.mjs'
        config.write_text(
            'import {defineConfig} from '+json.dumps(str(ROOT/'node_modules/vite/dist/node/index.js'))+';\n'
            +'import {svelte} from '+json.dumps(str(ROOT/'node_modules/@sveltejs/vite-plugin-svelte/src/index.js'))+';\n'
            +'export default defineConfig({root:'+json.dumps(str(ROOT))+',cacheDir:'+json.dumps(str(tmp/'cache'))
            +',plugins:[svelte()],optimizeDeps:{entries:[]}});\n'
        )
        with (tmp/'vite.log').open('w+') as log:
            process = subprocess.Popen([
                str(ROOT/'node_modules/.bin/vite'), '--config', str(config), '--configLoader', 'runner',
                '--host', '127.0.0.1', '--port', str(port), '--strictPort'
            ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            try:
                for _ in range(150):
                    if process.poll() is not None:
                        raise RuntimeError('Vite exited before the audit.')
                    try:
                        with urlopen(origin, timeout=1):
                            break
                    except OSError:
                        time.sleep(.2)
                else:
                    raise RuntimeError('Vite did not start within 30 seconds.')

                findings = []
                observations = []
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
                    for width in (320, 375, 480, 960):
                        page = browser.new_page(viewport={'width':width,'height':720},locale='zh-CN',reduced_motion='reduce')
                        page.goto(origin+'/tests/visual/',wait_until='networkidle')
                        if width < 960:
                            page.get_by_role('button',name='展开侧边栏').click()
                        page.get_by_role('button',name='示例知识库 的文件夹选项').click()
                        menu=page.locator('#context-menu')
                        item=menu.get_by_role('menuitem',name='搜索')
                        expect(item).to_be_attached()
                        rect=item.bounding_box()
                        assert rect is not None
                        hit=page.evaluate('''([x,y])=>{
                          const menu=document.querySelector('#context-menu'),side=document.querySelector('.sidebar');
                          const element=document.elementFromPoint(x,y);
                          return {menu_z:getComputedStyle(menu).zIndex,sidebar_z:getComputedStyle(side).zIndex,
                            hit_tag:element?.tagName,hit_class:element?.className,
                            hit_menu_item:element?.closest('[role=menuitem]')?.textContent?.trim()||null,
                            menu_rect:menu.getBoundingClientRect().toJSON(),sidebar_rect:side.getBoundingClientRect().toJSON()};
                        }''',[rect['x']+rect['width']/2,rect['y']+rect['height']/2])
                        if width==320:
                            page.screenshot(path=str(EVIDENCE/'sidebar-menu-320.png'))
                        try:
                            item.click(timeout=2000)
                            center_click=True
                        except PlaywrightTimeoutError:
                            center_click=False
                            # Observe what happens after activating the currently exposed edge.
                            item.click(position={'x':rect['width']-5,'y':rect['height']/2},timeout=2000)
                        expect(page.get_by_role('heading',name='搜索你的文件',include_hidden=True)).to_have_count(1)
                        inert=page.locator('.workspace').evaluate('(e)=>e.inert')
                        sidebar_visible=page.locator('.sidebar').is_visible()
                        observations.append({'viewport':[width,720],'center_click':center_click,'hit':hit,
                                             'workspace_inert_after_navigation':inert,'sidebar_visible':sidebar_visible})
                        if not center_click:
                            findings.append(f'{width}px: folder-menu center is blocked')
                        if width<960 and inert:
                            findings.append(f'{width}px: workspace remains inert after menu navigation')
                        page.close()

                    page=browser.new_page(locale='zh-CN',reduced_motion='reduce')
                    page.goto(origin+'/favicon.png')
                    page.evaluate('''()=>{
                      localStorage.setItem('sag.onboarding.seen','preexisting-sentinel');
                      localStorage.setItem('sag.search.history',JSON.stringify(['preexisting-sentinel']));
                    }''')
                    page.goto(origin+'/tests/visual/?fixture=search',wait_until='networkidle')
                    onboarding=page.evaluate("localStorage.getItem('sag.onboarding.seen')")
                    page.get_by_role('button',name='搜索',exact=True).click()
                    page.get_by_role('textbox',name='搜索关键词').fill('示例流程')
                    page.get_by_role('button',name='搜索文件',exact=True).click()
                    expect(page.locator('.search-layout')).to_be_visible()
                    history=page.evaluate("JSON.parse(localStorage.getItem('sag.search.history'))")
                    storage={'onboarding_after_preview':onboarding,'history_after_synthetic_search':history}
                    if onboarding!='preexisting-sentinel' or history!=['preexisting-sentinel']:
                        findings.append('preview changes pre-existing same-origin browser storage')
                    page.close()
                    version=browser.version
                    browser.close()
                files=['src/App.svelte','src/web/visual-shell.css','src/prototype.css','tests/visual/fixture.js','tests/browser/audit_preview.py']
                result={'browser':'Chromium '+version,'fixture':'synthetic data and fresh isolated browser profiles',
                        'observations':observations,'storage':storage,'findings':findings,
                        'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files},
                        'screenshot_sha256':hashlib.sha256((EVIDENCE/'sidebar-menu-320.png').read_bytes()).hexdigest()}
                (EVIDENCE/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                print(json.dumps({'findings':findings,'evidence':str(EVIDENCE)},ensure_ascii=False))
                return 1 if findings else 0
            finally:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait(timeout=5)


if __name__=='__main__':
    raise SystemExit(main())
