"""Capture current desktop UI examples with an isolated, synthetic bridge.

These screenshots are documentation illustrations, not native Windows or
real-business acceptance evidence. Run with --docs to update the two-language
documentation images after verifying the assertions.
"""
from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
fixture = (ROOT / 'tests/visual/fixture.js').read_text(encoding='utf8')
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
origin = f'http://127.0.0.1:{port}'

with tempfile.TemporaryDirectory(prefix='super-sag-docs-images-') as temporary:
    output = Path(temporary)
    with tempfile.TemporaryFile(mode='w+') as log:
        server = subprocess.Popen([str(ROOT / 'node_modules/.bin/vite'), '--host', '127.0.0.1', '--port', str(port), '--strictPort'],
                                  cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(150):
                if server.poll() is not None:
                    raise RuntimeError('Vite exited before screenshot capture')
                try:
                    with urlopen(origin, timeout=1):
                        break
                except OSError:
                    time.sleep(.2)
            else:
                raise RuntimeError('Vite did not start')
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
                for lang, suffix, labels in (
                    ('zh-CN', 'cn', ('文件', '已索引文件', '搜索', '搜索关键词', '搜索文件', '设置', '关于')),
                    ('en', 'en', ('Files', 'Indexed files', 'Search', 'Search keywords', 'Search files', 'Settings', 'About')),
                ):
                    context = browser.new_context(viewport={'width': 1280, 'height': 900}, locale=lang, reduced_motion='reduce')
                    context.add_init_script(fixture)
                    page = context.new_page()

                    def capture(name: str) -> None:
                        expect(page.locator('.sidebar')).to_contain_text('Super-SAG')
                        image = output / f'{name}-{suffix}.png'
                        page.screenshot(path=str(image))
                        if '--docs' in sys.argv:
                            (ROOT / 'docs-site/public/images' / image.name).write_bytes(image.read_bytes())

                    page.goto(f'{origin}/?fixture=files&lang={lang}', wait_until='networkidle')
                    capture('product-ask-home')
                    page.get_by_role('button', name=labels[0], exact=True).click()
                    expect(page.get_by_role('heading', name=labels[1])).to_be_visible()
                    capture('product-folders')
                    page.locator('.simple-file-row', has_text='示例知识库').first.click()
                    expect(page.get_by_role('heading', name='示例知识库')).to_be_visible()
                    capture('product-files')
                    page.locator('.simple-file-row', has_text='示例文档.md').first.click()
                    expect(page.get_by_role('heading', name='虚构示例文档')).to_be_visible()
                    capture('product-markdown')

                    page.goto(f'{origin}/?fixture=search&lang={lang}', wait_until='networkidle')
                    page.get_by_role('button', name=labels[2], exact=True).click()
                    expect(page.get_by_role('textbox', name=labels[3])).to_be_visible()
                    capture('product-search-home')
                    page.get_by_role('textbox', name=labels[3]).fill('示例流程')
                    page.get_by_role('button', name=labels[4], exact=True).click()
                    expect(page.locator('.search-preview-body')).to_contain_text('示例流程：整理资料后进行复核。')
                    capture('product-search')

                    page.goto(f'{origin}/?fixture=conversation&lang={lang}', wait_until='networkidle')
                    page.get_by_role('button', name='示例流程讨论', exact=True).click()
                    expect(page.locator('.source-chip')).to_be_visible()
                    capture('product-chat')

                    page.get_by_role('button', name=labels[5], exact=True).click()
                    dialog = page.get_by_role('dialog')
                    dialog.get_by_role('button', name=labels[6], exact=True).click()
                    expect(dialog.locator('.settings-about-version')).to_have_text('v0.1.0')
                    capture('product-about')
                    context.close()
                print(f'Chromium {browser.version}: current synthetic UI examples captured for zh-CN and en')
                browser.close()
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
