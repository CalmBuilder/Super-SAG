"""Disposable-runner probe of an installed WebView2 desktop app."""
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import urlopen
from playwright.sync_api import expect, sync_playwright
from layout_probe import exercise_sidebar_collapse, preference_layouts, workspace_layout

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
    matches = []
    for _ in range(60):
        pages = [item for context in browser.contexts for item in context.pages]
        matches = [item for item in pages if urlsplit(item.url).hostname == 'tauri.localhost'
                   and not urlsplit(item.url).query]
        if matches:
            break
        time.sleep(.5)
    if len(matches) != 1:
        raise RuntimeError(f'Expected exactly one installed app page, found {len(matches)}')
    page = matches[0]
    page.set_default_timeout(15000)
    tutorial = page.get_by_role('button', name='关闭教程')
    if tutorial.count() and tutorial.is_visible():
        tutorial.click()
    expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
    output = Path(os.environ['RUNNER_TEMP']) / 'bs-native-ui-evidence'
    output.mkdir(exist_ok=True)
    layouts = {'ask': workspace_layout(page)}
    page.screenshot(path=str(output / 'windows-ask.png'), animations='disabled')
    page.get_by_role('button', name='搜索', exact=True).click()
    expect(page.locator('.search-page h1')).to_have_text('搜索你的文件')
    layouts['search'] = workspace_layout(page)
    page.screenshot(path=str(output / 'windows-search.png'), animations='disabled')
    page.get_by_role('button', name='文件', exact=True).click()
    expect(page.locator('.content')).to_contain_text('已索引文件')
    layouts['files'] = workspace_layout(page)
    page.screenshot(path=str(output / 'windows-files.png'), animations='disabled')
    page.get_by_role('button', name='问答', exact=True).click()
    expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
    exercise_sidebar_collapse(page)
    page.get_by_role('button', name='设置', exact=True).click()
    expect(page.get_by_role('dialog')).to_be_visible()
    page.get_by_role('button', name='关闭设置').click()
    expect(page.get_by_role('dialog')).to_have_count(0)
    layouts.update(preference_layouts(page, output, 'windows'))
    report = {'status':'passed', 'scope':'installed Windows app WebView navigation and settings',
              'url':page.url, 'checks':['ask','search','files','sidebar collapse and expand','settings open and close',
                                       'dark theme and English setting'], 'layout':layouts}
    (output / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
