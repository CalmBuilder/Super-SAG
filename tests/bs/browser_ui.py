"""Exercise the new shared workspace in an isolated real Chromium-family browser.

The platform below supplies synthetic data. It does not test files, search, models,
the Linux service or an installed desktop application.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright
from layout_probe import exercise_sidebar_collapse

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--browser', choices=['chromium', 'chrome', 'msedge'], default='chromium')
parser.add_argument('--output', type=Path, default=ROOT / '.cache/bs-ui')
args = parser.parse_args()
output = args.output.resolve()
reference = (ROOT / 'pros').resolve()
if output == reference or reference in output.parents:
    raise SystemExit('Evidence cannot be written inside the reference checkout.')
output.mkdir(parents=True, exist_ok=True)

with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
origin = f'http://127.0.0.1:{port}'
cases: list[dict[str, object]] = []
errors: list[str] = []


def record(case: str, **details: object) -> None:
    cases.append({'case': case, 'status': 'passed', **details})


with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as log:
    server = subprocess.Popen(
        ['node', str(ROOT / 'node_modules/vite/bin/vite.js'), '--config', 'vite.web.config.ts',
         '--host', '127.0.0.1', '--port', str(port), '--strictPort'],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
    )
    try:
        for _ in range(150):
            if server.poll() is not None:
                raise RuntimeError('Vite exited before the browser test started.')
            try:
                with urlopen(origin + '/tests/bs/index.html', timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, URLError):
                time.sleep(.2)
        else:
            raise RuntimeError('The isolated Vite server did not start within 30 seconds.')

        with sync_playwright() as playwright:
            launch_args = ['--no-sandbox'] if sys.platform.startswith('linux') else []
            launch_options: dict[str, object] = {'headless': True, 'args': launch_args}
            if args.browser != 'chromium':
                launch_options['channel'] = args.browser
            browser = playwright.chromium.launch(**launch_options)

            def new_page(width: int = 1280, lang: str = 'zh-CN', theme: str = 'light', scenario: str = 'normal'):
                context = browser.new_context(viewport={'width': width, 'height': 800}, locale=lang, reduced_motion='reduce')
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'{origin}/tests/bs/index.html?lang={lang}&theme={theme}&scenario={scenario}', wait_until='networkidle')
                return context, page

            context, page = new_page()
            expect(page.locator('.brand')).to_have_text('Super-SAG')
            expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
            expect(page.locator('.tree-row')).to_have_count(1)
            assert page.evaluate("typeof window.__TAURI_INTERNALS__") == 'undefined'
            assert not page.evaluate("window.__BS_TEST__.calls.includes('quick_search_main_ready')")
            page.get_by_role('button', name='搜索', exact=True).click()
            expect(page.locator('.search-page h1')).to_have_text('搜索你的文件')
            page.get_by_role('button', name='文件', exact=True).click()
            expect(page.locator('.content')).to_contain_text('已索引文件')
            page.get_by_role('button', name='问答', exact=True).click()
            expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
            page.screenshot(path=str(output / f'{args.browser}-workspace.png'))
            record('desktop-sized navigation and shared workspace', width=1280)

            exercise_sidebar_collapse(page)
            record('desktop-sized sidebar collapse and expand')

            page.keyboard.press('Control+k')
            expect(page.locator('.search-page h1')).to_have_text('搜索你的文件')
            page.get_by_role('button', name='问答', exact=True).click()
            expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
            record('page keyboard shortcut opens search')

            page.get_by_role('button', name='设置', exact=True).click()
            expect(page.get_by_role('dialog')).to_be_visible()
            page.get_by_role('button', name='关闭设置').click()
            expect(page.get_by_role('dialog')).to_have_count(0)
            page.get_by_role('button', name='切换明暗主题').click()
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            record('settings open/close and theme change')
            context.close()

            context, page = new_page(scenario='theme-error')
            page.get_by_role('button', name='切换明暗主题').click()
            expect(page.locator('#notice')).to_contain_text('测试保存主题失败')
            expect(page.locator('html')).to_have_attribute('data-theme', 'light')
            record('theme save failure retains prior theme')
            context.close()

            context, page = new_page(lang='en', theme='dark')
            expect(page.locator('.brand')).to_have_text('Super-SAG')
            expect(page.locator('html')).to_have_attribute('lang', 'en')
            expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
            expect(page.get_by_role('button', name='Search', exact=True)).to_be_visible()
            record('English and dark theme')
            context.close()

            context, page = new_page(scenario='empty')
            expect(page.locator('.tree-row')).to_have_count(0)
            expect(page.locator('.folder-empty-state')).to_be_visible()
            record('empty library')
            context.close()

            context, page = new_page(scenario='many')
            expect(page.locator('.tree-row')).to_have_count(120)
            assert page.locator('.tree').evaluate('(el) => el.scrollHeight > el.clientHeight')
            expect(page.locator('.tree-row').last).to_contain_text('119-')
            record('120 long folder names with scrolling')
            context.close()

            context, page = new_page(scenario='tree')
            root = page.get_by_role('button', name='展开示例知识库')
            root.click()
            expect(page.get_by_role('button', name='展开一级')).to_be_visible()
            page.get_by_role('button', name='展开一级').click()
            expect(page.get_by_role('button', name='展开二级')).to_be_visible()
            page.get_by_role('button', name='折叠一级').click()
            page.get_by_role('button', name='折叠示例知识库').click()
            expect(page.locator('.tree-row')).to_have_count(1)
            record('nested folder expansion and collapse')
            context.close()

            context, page = new_page(scenario='tree-error')
            root = page.get_by_role('button', name='展开示例知识库')
            root.click()
            expect(page.locator('#notice')).to_contain_text('测试读取目录失败')
            expect(root).to_have_attribute('aria-expanded', 'false')
            record('folder expansion failure preserves collapsed state')
            context.close()

            context = browser.new_context(viewport={'width': 1280, 'height': 800}, locale='zh-CN')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(origin + '/web/index.html', wait_until='networkidle')
            page.evaluate('''() => {
              localStorage.setItem('sag.sidebar.expanded', '{old invalid value');
              localStorage.setItem('sag.search.history', '["old"]');
              localStorage.setItem('sag.onboarding.seen', 'legacy');
              localStorage.setItem('unrelated', 'keep');
              localStorage.setItem('super-sag.web.v1.other', 'keep');
            }''')
            page.goto(origin + '/tests/bs/index.html?scenario=tree', wait_until='networkidle')
            expect(page.locator('.brand')).to_have_text('Super-SAG')
            page.get_by_role('button', name='展开示例知识库').click()
            expect(page.get_by_role('button', name='展开一级')).to_be_visible()
            assert page.evaluate("localStorage.getItem('sag.sidebar.expanded')") == '{old invalid value'
            assert page.evaluate("localStorage.getItem('super-sag.web.v1.sag.sidebar.expanded')") is not None
            page.get_by_role('button', name='设置', exact=True).click()
            page.get_by_role('button', name='数据与隐私', exact=True).click()
            page.get_by_role('button', name='清除所有数据', exact=True).click()
            page.get_by_role('button', name='确认清除所有数据').click()
            expect(page.get_by_role('dialog')).to_have_count(0)
            assert page.evaluate("localStorage.getItem('sag.sidebar.expanded')") == '{old invalid value'
            assert page.evaluate("localStorage.getItem('sag.search.history')") == '["old"]'
            assert page.evaluate("localStorage.getItem('sag.onboarding.seen')") == 'legacy'
            assert page.evaluate("localStorage.getItem('unrelated')") == 'keep'
            assert page.evaluate("localStorage.getItem('super-sag.web.v1.other')") == 'keep'
            assert page.evaluate("localStorage.getItem('super-sag.web.v1.sag.sidebar.expanded')") is None
            record('old same-origin storage is ignored and preserved after simulated clear')
            context.close()

            for width in (320, 375, 768, 959, 960):
                context, page = new_page(width=width)
                switcher = page.locator('.workspace-switch')
                bounds = switcher.bounding_box()
                assert bounds and bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= width + 1, (width, bounds)
                if width <= 959:
                    toggle = page.get_by_role('button', name='展开侧边栏')
                    expect(toggle).to_be_visible()
                    toggle.click()
                    expect(page.locator('.sidebar')).to_be_visible()
                    expect(page.locator('main.workspace')).to_have_attribute('inert', '')
                    expect(page.locator('.sidebar-titlebar [aria-label="收起侧边栏"]')).to_be_focused()
                    page.keyboard.press('Escape')
                    expect(page.locator('.sidebar')).not_to_be_visible()
                    expect(toggle).to_have_attribute('aria-expanded', 'false')
                    expect(toggle).to_be_focused()
                    toggle.click()
                    page.get_by_role('button', name='设置', exact=True).click()
                    expect(page.get_by_role('dialog')).to_be_visible()
                    page.get_by_role('button', name='关闭设置').click()
                    expect(page.get_by_role('dialog')).to_have_count(0)
                    expect(toggle).to_be_focused()
                else:
                    expect(page.locator('.browser-sidebar-toggle')).to_have_count(0)
                    expect(page.locator('.sidebar')).to_be_visible()
                record('responsive sidebar boundary', width=width)
                context.close()

            context, page = new_page(width=960)
            page.set_viewport_size({'width': 959, 'height': 800})
            toggle = page.get_by_role('button', name='展开侧边栏')
            expect(toggle).to_be_visible()
            toggle.click()
            expect(page.locator('main.workspace')).to_have_attribute('inert', '')
            page.set_viewport_size({'width': 960, 'height': 800})
            expect(page.locator('.browser-sidebar-toggle')).to_have_count(0)
            expect(page.locator('.sidebar')).to_be_visible()
            expect(page.locator('main.workspace')).not_to_have_attribute('inert', '')
            page.set_viewport_size({'width': 959, 'height': 800})
            expect(page.get_by_role('button', name='展开侧边栏')).to_have_attribute('aria-expanded', 'false')
            expect(page.locator('.sidebar')).not_to_be_visible()
            record('resize across sidebar boundary while open')
            context.close()

            for width in (320, 375):
                context, page = new_page(width=width)
                page.get_by_role('button', name='展开侧边栏').click()
                page.locator('.tree-row').first.hover()
                page.get_by_role('button', name='示例知识库 的文件夹选项').click()
                menu_item = page.get_by_role('menuitem', name='搜索', exact=True)
                expect(menu_item).to_be_visible()
                assert menu_item.evaluate('(el) => {const r=el.getBoundingClientRect();return el.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2));}')
                menu_item.click()
                expect(page.locator('.search-page h1')).to_have_text('搜索你的文件')
                expect(page.locator('.sidebar')).not_to_be_visible()
                expect(page.locator('main.workspace')).not_to_have_attribute('inert', '')
                record('folder menu can navigate without blocking workspace', width=width)
                context.close()

            context, page = new_page(scenario='offline')
            expect(page.locator('.startup-error')).to_contain_text('无法连接 Super-SAG Web 服务')
            expect(page.locator('.startup-error')).to_contain_text('测试服务不可用')
            page.get_by_role('button', name='重试').click()
            expect(page.locator('.startup-error')).to_contain_text('测试服务不可用')
            record('startup failure and retry')
            context.close()

            context = browser.new_context(viewport={'width': 1280, 'height': 800})
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.add_init_script("localStorage.setItem('sag.sidebar.expanded', '{old invalid value'); localStorage.setItem('sag.search.history', '{old invalid value');")
            page.goto(origin + '/web/index.html', wait_until='networkidle')
            expect(page.locator('.startup-error')).to_contain_text('Web 服务尚未接通')
            assert page.evaluate("typeof window.__BS_TEST__") == 'undefined'
            assert page.evaluate("typeof window.__TAURI_INTERNALS__") == 'undefined'
            assert page.evaluate("localStorage.getItem('sag.sidebar.expanded')") == '{old invalid value'
            record('product entry rejects unavailable business without a fixture')
            context.close()

            assert not errors, errors
            browser_version = browser.version
            browser.close()

        source_names = [
            'src/App.svelte', 'src/lib/platform.ts', 'src/lib/storage.ts', 'src/lib/remember-scroll.ts',
            'src/bs/platform.ts', 'src/bs/sidebar.ts', 'src/bs/workspace.css', 'src/bs/mount.ts',
            'tests/bs/fixture.ts', 'tests/bs/layout_probe.py', 'tests/bs/browser_ui.py',
        ]
        report = {
            'scope': 'shared UI with isolated synthetic fixture; not Windows desktop or real Web business acceptance',
            'browser': args.browser, 'browser_version': browser_version, 'platform': sys.platform,
            'windows_source_baseline': '9459f4b90617a2042d20848eea6560e0d6812ebe',
            'cases': cases, 'page_errors': errors,
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_names},
        }
        (output / f'{args.browser}-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'browser': args.browser, 'version': browser_version, 'cases': len(cases), 'output': str(output)}, ensure_ascii=False))
    finally:
        failed = sys.exc_info()[0] is not None
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
        if failed:
            log.seek(0)
            print(f'Browser page errors: {errors}\nVite output:\n{log.read()}', file=sys.stderr)
