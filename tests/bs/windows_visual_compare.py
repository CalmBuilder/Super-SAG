"""Capture browser views at the installed Windows app's viewport.

The native screenshots must have been created by native_ui_windows.ps1 on the
same disposable runner. Browser contents use the synthetic B/S fixture, so the
images support visual review; they do not prove business parity.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright
from layout_probe import workspace_layout

if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
    raise SystemExit('Run only on a disposable GitHub-hosted Windows runner.')
ROOT = Path(__file__).resolve().parents[2]
output = Path(os.environ['RUNNER_TEMP']) / 'bs-native-ui-evidence'
native_report = json.loads((output / 'result.json').read_text(encoding='utf-8'))
viewport = None
for name in ('windows-ask.png', 'windows-search.png', 'windows-files.png'):
    data = (output / name).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError(f'Invalid native screenshot: {name}')
    size = struct.unpack('>II', data[16:24])
    if viewport is not None and size != viewport:
        raise RuntimeError('Native screenshots have different viewports')
    viewport = size
assert viewport is not None
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
origin = f'http://127.0.0.1:{port}'
with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as log:
    server = subprocess.Popen(['node', str(ROOT / 'node_modules/vite/bin/vite.js'), '--config', 'vite.web.config.ts',
                               '--host', '127.0.0.1', '--port', str(port), '--strictPort'],
                              cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(150):
            if server.poll() is not None:
                raise RuntimeError('Vite exited before the comparison')
            try:
                with urlopen(origin + '/tests/bs/index.html', timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, URLError):
                time.sleep(.2)
        else:
            raise RuntimeError('The isolated Vite server did not start')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page(viewport={'width': viewport[0], 'height': viewport[1]}, locale='zh-CN')
            errors: list[str] = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(origin + '/tests/bs/index.html', wait_until='networkidle')
            def check_layout(view: str) -> dict[str, dict[str, float]]:
                browser_layout = workspace_layout(page)
                for selector, coordinates in native_report['layout'][view].items():
                    for key, value in coordinates.items():
                        actual = browser_layout[selector][key]
                        if abs(actual - value) > 2:
                            raise AssertionError(f'{view} {selector} {key}: desktop={value}, browser={actual}')
                return browser_layout

            expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
            layouts = {'ask': check_layout('ask')}
            page.evaluate('document.activeElement.blur()')
            page.screenshot(path=str(output / 'browser-ask.png'), animations='disabled')
            page.get_by_role('button', name='搜索', exact=True).click()
            expect(page.locator('.search-page h1')).to_have_text('搜索你的文件')
            layouts['search'] = check_layout('search')
            page.evaluate('document.activeElement.blur()')
            page.screenshot(path=str(output / 'browser-search.png'), animations='disabled')
            page.get_by_role('button', name='文件', exact=True).click()
            expect(page.locator('.content')).to_contain_text('已索引文件')
            layouts['files'] = check_layout('files')
            page.evaluate('document.activeElement.blur()')
            page.screenshot(path=str(output / 'browser-files.png'), animations='disabled')
            assert not errors, errors
            report = {
                'scope': 'same Windows runner and viewport; browser uses synthetic fixture with different folder/model data',
                'viewport': {'width': viewport[0], 'height': viewport[1]},
                'browser': 'Microsoft Edge', 'browser_version': browser.version,
                'layout': layouts,
                'sha256': {name: hashlib.sha256((output / name).read_bytes()).hexdigest()
                           for name in ('windows-ask.png', 'windows-search.png', 'windows-files.png',
                                        'browser-ask.png', 'browser-search.png', 'browser-files.png')},
            }
            (output / 'comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False))
            browser.close()
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
            print(f'Vite output:\n{log.read()}', file=sys.stderr)
