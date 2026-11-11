"""Disposable-runner probe of an installed WebView2 desktop app."""
import json
import os
import time
from urllib.request import urlopen
from playwright.sync_api import expect, sync_playwright

port = int(os.environ['BS_NATIVE_DEBUG_PORT'])
endpoint = f'http://127.0.0.1:{port}'
for _ in range(60):
    try:
        with urlopen(endpoint + '/json/version', timeout=1) as response:
            assert response.status == 200
        break
    except OSError:
        time.sleep(.5)
else:
    raise RuntimeError('Installed WebView2 did not expose a loopback debugging endpoint')

with sync_playwright() as playwright:
    browser = playwright.chromium.connect_over_cdp(endpoint, timeout=30000)
    pages = [page for context in browser.contexts for page in context.pages]
    if not pages:
        raise RuntimeError('No app page in installed WebView2')
    page = pages[0]
    page.set_default_timeout(15000)
    tutorial = page.get_by_role('button', name='关闭教程')
    if tutorial.count() and tutorial.is_visible():
        tutorial.click()
    expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
    page.get_by_role('button', name='搜索', exact=True).click()
    expect(page.locator('.search-page h1')).to_have_text('搜索你的文件')
    page.get_by_role('button', name='文件', exact=True).click()
    expect(page.locator('.content')).to_contain_text('已索引文件')
    page.get_by_role('button', name='问答', exact=True).click()
    expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
    page.get_by_role('button', name='设置', exact=True).click()
    expect(page.get_by_role('dialog')).to_be_visible()
    page.get_by_role('button', name='关闭设置').click()
    expect(page.get_by_role('dialog')).to_have_count(0)
    print(json.dumps({'status':'passed', 'scope':'installed Windows app WebView navigation and settings',
                      'url':page.url, 'checks':['ask','search','files','settings open and close']}, ensure_ascii=False))
