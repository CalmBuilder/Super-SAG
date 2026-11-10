"""Browser acceptance for the test-only Web workspace; no backend or real files.

The independent reference imports the pinned pros/SAG-Wiki components read-only.
All native operations are a rejecting/synthetic fixture. This does not validate
Windows, a Web service, indexing, model output, or authorization.
"""
from __future__ import annotations

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
EVIDENCE = Path(os.environ.get('SAG_WEB_VISUAL_EVIDENCE_DIR', ROOT / '.cache/web-workspace'))
NOTICE = '仅样式预览 · 虚构数据 · 真实业务未接入'


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def layout(page) -> dict:
    return page.evaluate('''() => Object.fromEntries(
      ['.sidebar', '.workspace', '.workspace-header', '.workspace-switch',
       '.workspace-actions', '.welcome', '.composer'].map(selector => {
        const element = document.querySelector(selector);
        const r = element.getBoundingClientRect(), s = getComputedStyle(element);
        return [selector, {x:r.x,y:r.y,width:r.width,height:r.height,
          font:s.fontFamily,color:s.color}];
      }))''')


def compare(expected: dict, actual: dict) -> None:
    for selector, values in expected.items():
        for key, value in values.items():
            other = actual[selector][key]
            if isinstance(value, (int, float)):
                assert abs(value - other) <= 1, (selector, key, value, other)
            else:
                assert value == other, (selector, key, value, other)


def conversation_layout(page) -> dict:
    return page.evaluate('''() => Object.fromEntries(
      ['.chat-log','.chat-messages','.user-message','.answer-text','.source-chip','.composer'].map(selector => {
        const element=document.querySelector(selector),r=element.getBoundingClientRect(),s=getComputedStyle(element);
        return [selector,{x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontFamily,color:s.color}];
      }))''')


def stream_layout(page) -> dict:
    return page.evaluate('''() => Object.fromEntries(
      ['.chat-log','.user-message','.answer-text','.composer','.send'].map(selector => {
        const element=document.querySelector(selector),r=element.getBoundingClientRect(),s=getComputedStyle(element);
        return [selector,{x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontFamily,color:s.color}];
      }))''')


def search_layout(page) -> dict:
    return page.evaluate('''() => Object.fromEntries(
      ['.search-query-row','.search-layout','.search-results-column','.search-preview',
       '.search-preview-head','.search-result'].map(selector => {
        const element=document.querySelector(selector),r=element.getBoundingClientRect(),s=getComputedStyle(element);
        return [selector,{x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontFamily,color:s.color}];
      }))''')


def files_layout(page) -> dict:
    return page.evaluate('''() => Object.fromEntries(
      ['.library-files .page-heading','.library-folder-title','.library-folder-meta',
       '.simple-file-list','.simple-file-row'].map(selector => {
        const element=document.querySelector(selector),r=element.getBoundingClientRect(),s=getComputedStyle(element);
        return [selector,{x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontFamily,color:s.color}];
      }))''')


def picker_layout(page) -> dict:
    return page.evaluate('''() => Object.fromEntries(
      ['.folder-picker','.folder-picker-heading','.folder-picker-navigation',
       '.folder-picker-list','.folder-picker-footer'].map(selector => {
        const element=document.querySelector(selector),r=element.getBoundingClientRect(),s=getComputedStyle(element);
        return [selector,{x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontFamily,color:s.color}];
      }))''')


def settings_layout(page) -> dict:
    return page.evaluate('''() => Object.fromEntries(
      ['.settings-window','.settings-nav','.settings-content','.settings-footer'].map(selector => {
        const element=document.querySelector(selector),r=element.getBoundingClientRect(),s=getComputedStyle(element);
        return [selector,{x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontFamily,color:s.color}];
      }))''')


def fits(page, selector: str) -> None:
    result = page.locator(selector).evaluate('''element => {
      const r=element.getBoundingClientRect();
      return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,
              width:innerWidth,height:innerHeight};
    }''')
    assert result['left'] >= -1 and result['right'] <= result['width'] + 1, (selector, result)
    assert result['top'] >= -1 and result['bottom'] <= result['height'] + 1, (selector, result)


def main() -> None:
    reference = (ROOT / 'pros/SAG-Wiki').resolve()
    target = EVIDENCE.resolve()
    if target == reference or reference in target.parents:
        raise SystemExit('Evidence must not be written into the static reference.')
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    port = free_port()
    origin = f'http://127.0.0.1:{port}'
    with tempfile.TemporaryFile(mode='w+') as log:
        process = subprocess.Popen([str(ROOT / 'node_modules/.bin/vite'), '--host', '127.0.0.1',
                                    '--port', str(port), '--strictPort'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(150):
                if process.poll() is not None:
                    raise RuntimeError('Vite exited before the browser check.')
                try:
                    with urlopen(origin, timeout=1) as response:
                        if response.status == 200:
                            break
                except (OSError, URLError):
                    time.sleep(.2)
            else:
                raise RuntimeError('Vite did not start within 30 seconds.')

            errors: list[str] = []
            checks: list[str] = []
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
                context = browser.new_context(locale='zh-CN', reduced_motion='reduce')

                def page_at(path: str, width: int, height: int):
                    page = context.new_page()
                    page.set_viewport_size({'width':width, 'height':height})
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(origin + path, wait_until='networkidle')
                    return page

                # Both the current desktop and Web preview are compared to a separate,
                # immutable reference tree, at identical viewport/theme/data.
                for width, height in ((1600,1067), (1280,850), (960,720)):
                    ref = page_at('/tests/browser/reference.html', width, height)
                    # The desktop entry needs the fixture before its module starts.
                    work = context.new_page()
                    work.set_viewport_size({'width':width,'height':height})
                    work.on('pageerror', lambda error: errors.append(str(error)))
                    work.add_init_script((ROOT / 'tests/visual/fixture.js').read_text())
                    work.goto(origin, wait_until='networkidle')
                    web = page_at('/tests/visual/', width, height)
                    for page in (ref,work,web):
                        expect(page.get_by_role('heading', name='向你的文件提问')).to_be_visible()
                    compare(layout(ref),layout(work))
                    compare(layout(ref),layout(web))
                    expect(ref.locator('.window-controls button')).to_have_count(3)
                    expect(work.locator('.window-controls button')).to_have_count(3)
                    expect(web.locator('.window-controls button')).to_have_count(0)
                    expect(web.locator('.brand')).to_have_text('Super-SAG')
                    expect(web.get_by_text(NOTICE, exact=True)).to_be_visible()
                    if width == 1600:
                        web.screenshot(path=str(EVIDENCE / 'workspace-desktop.png'))
                    ref.close(); work.close(); web.close()
                checks.append('1600/1280/960: independent pinned desktop reference, current desktop and Web shell geometry; brand and browser window controls')

                # Responsive boundary, tablet, phone and short viewport.
                for width,height in ((959,720),(768,720),(480,720),(375,720),(320,720),(320,480)):
                    page = page_at('/tests/visual/',width,height)
                    expect(page.get_by_role('heading', name='向你的文件提问')).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    expect(page.locator('.sidebar')).to_be_hidden()
                    open_button = page.get_by_role('button', name='展开侧边栏')
                    expect(open_button).to_be_visible()
                    for selector in ('.workspace-header','.workspace-switch','.workspace-actions'):
                        fits(page,selector)
                    expect(page.get_by_role('button',name='问答',exact=True)).to_be_visible()
                    expect(page.get_by_role('button',name='搜索',exact=True)).to_be_visible()
                    page.get_by_role('button',name='搜索',exact=True).click()
                    expect(page.get_by_role('heading',name='搜索你的文件')).to_be_visible()
                    expect(page.get_by_role('textbox',name='搜索关键词')).to_be_visible()
                    page.get_by_role('button',name='文件',exact=True).click()
                    expect(page.get_by_role('heading',name='已索引文件')).to_be_visible()
                    page.get_by_role('button',name='问答',exact=True).click()
                    expect(page.get_by_role('heading',name='向你的文件提问')).to_be_visible()
                    open_button.focus(); page.keyboard.press('Enter')
                    expect(page.locator('.sidebar')).to_be_visible()
                    expect(open_button).to_have_attribute('aria-expanded','true')
                    assert page.locator('.workspace').evaluate('(e)=>e.inert')
                    assert page.evaluate("document.activeElement.matches('.sidebar-titlebar .icon-button')")
                    if (width,height)==(320,720):
                        page.screenshot(path=str(EVIDENCE / 'workspace-phone-drawer.png'))
                    page.keyboard.press('Escape')
                    expect(page.locator('.sidebar')).to_be_hidden()
                    expect(open_button).to_be_focused()
                    if (width,height)==(320,480):
                        page.locator('.ask-content').evaluate('(e)=>e.scrollTop=e.scrollHeight')
                        fits(page,'.composer')
                    if (width,height)==(320,720):
                        page.screenshot(path=str(EVIDENCE / 'workspace-phone.png'))
                    page.close()
                checks.append('959/768/480/375/320, including 320x480: no horizontal page overflow; navigation; keyboard sidebar and focus restoration')

                page=page_at('/tests/visual/',960,720)
                page.get_by_role('button',name='收起侧边栏').click()
                expect(page.locator('.real-client')).to_have_class('desktop-window real-client web-client compact-sidebar')
                page.set_viewport_size({'width':959,'height':720})
                page.get_by_role('button',name='展开侧边栏').click()
                expect(page.locator('.sidebar .brand')).to_be_visible()
                page.set_viewport_size({'width':960,'height':720})
                expect(page.locator('.real-client')).to_have_class('desktop-window real-client web-client compact-sidebar')
                assert not page.locator('.workspace').evaluate('(e)=>e.inert')
                page.close()
                checks.append('resize across 959/960 preserves the desktop collapsed state and clears the mobile overlay')

                # Real interaction with the folder picker: no write succeeds.
                page = page_at('/tests/visual/',320,720)
                page.get_by_role('button',name='展开侧边栏').click()
                page.locator('.sidebar [aria-label="添加文件夹"]').click()
                dialog=page.get_by_role('dialog',name='添加文件夹')
                expect(dialog).to_be_visible()
                for button in dialog.locator('.folder-picker-footer button').all():
                    box=button.bounding_box(); assert box and box['x'] >= 0 and box['x']+box['width'] <= 320, box
                page.screenshot(path=str(EVIDENCE / 'workspace-phone-folder.png'))
                dialog.get_by_role('checkbox',name='选择 项目资料').check()
                dialog.get_by_role('button',name='添加 1 个文件夹').click()
                expect(dialog.get_by_role('alert')).to_contain_text('Not available in the visual-only test bridge: add_root')
                expect(dialog).to_be_visible()
                dialog.get_by_role('button',name='取消',exact=True).click()
                expect(dialog).to_be_hidden()
                expect(page.get_by_role('button',name='展开侧边栏')).to_be_focused()
                assert page.evaluate('''async()=>{
                  try { await window.__TAURI_INTERNALS__.invoke('save_document', {path:'/demo/x',body:'x'}); return false; }
                  catch { return true; }
                }''')
                page.close()
                checks.append('320 folder dialog controls fit; selected folder write fails visibly; direct synthetic write is rejected')

                # Settings entry remains usable on phone; this is not acceptance of all settings pages.
                page = page_at('/tests/visual/',320,720)
                page.get_by_role('button',name='展开侧边栏').click()
                page.locator('.sidebar-settings').click()
                dialog=page.get_by_role('dialog',name='设置')
                expect(dialog.get_by_role('heading',name='通用')).to_be_visible()
                assert dialog.locator('.settings-content').bounding_box()['width'] > 260
                dialog.get_by_role('button',name='外观',exact=True).click()
                expect(dialog.get_by_role('heading',name='外观')).to_be_visible()
                dialog.get_by_role('button',name='关闭设置').click()
                expect(dialog).to_be_hidden()
                expect(page.get_by_role('button',name='展开侧边栏')).to_be_focused()
                page.close()
                checks.append('320 settings entry, common/appearance category navigation and close')

                # Search failure exposes the fixture error and keeps the back
                # control and navigation separately usable at the smallest width.
                page=page_at('/tests/visual/',320,720)
                page.get_by_role('button',name='搜索',exact=True).click()
                page.get_by_role('textbox',name='搜索关键词').fill('虚构查询')
                page.get_by_role('button',name='搜索文件',exact=True).click()
                expect(page.get_by_text('Not available in the visual-only test bridge: run_query',exact=False)).to_be_visible()
                fits(page,'.workspace-back')
                back=page.locator('.workspace-back').bounding_box()
                nav=page.locator('.workspace-switch').bounding_box()
                assert back and nav and back['x']+back['width'] <= nav['x']+1, (back,nav)
                page.get_by_role('button',name='返回搜索').click()
                expect(page.get_by_role('heading',name='搜索你的文件')).to_be_visible()
                page.close()
                checks.append('320 search failure is visible and the back button does not cover navigation')

                # The conversation and citation use read-only synthetic data;
                # desktop-sized geometry is measured against the pinned tree.
                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html?fixture=conversation',width,height)
                    web=page_at('/tests/visual/?fixture=conversation',width,height)
                    for page in (ref,web):
                        page.get_by_role('button',name='示例流程讨论',exact=True).click()
                        expect(page.locator('.source-chip')).to_be_visible()
                    compare(conversation_layout(ref),conversation_layout(web))
                    if width==1600: web.screenshot(path=str(EVIDENCE / 'conversation-desktop.png'))
                    for page in (ref,web):
                        page.locator('.source-chip').click()
                        expect(page.get_by_text('示例流程：整理资料后进行复核。')).to_be_visible()
                    a,b=ref.locator('.source-panel').bounding_box(),web.locator('.source-panel').bounding_box()
                    for key in ('x','y','width','height'): assert abs(a[key]-b[key])<=1,(key,a,b)
                    ref.close();web.close()
                checks.append('1600/1280 conversation and citation geometry compared with independent desktop reference')

                for width in (375,320):
                    page=page_at('/tests/visual/?fixture=conversation',width,720)
                    page.get_by_role('button',name='示例流程讨论',exact=True).click()
                    expect(page.locator('.source-chip')).to_be_visible()
                    if width==320: page.screenshot(path=str(EVIDENCE / 'conversation-phone.png'))
                    page.locator('.source-chip').click()
                    dialog=page.get_by_role('dialog',name='引用原文')
                    expect(dialog.get_by_text('示例流程：整理资料后进行复核。')).to_be_visible()
                    assert dialog.bounding_box()['width']>=width-16
                    fits(page,'.source-panel .citation-open')
                    if width==320: page.screenshot(path=str(EVIDENCE / 'citation-phone.png'))
                    dialog.get_by_role('button',name='打开当前文档').click()
                    expect(page.locator('.readonly-document')).to_be_visible()
                    assert page.locator('.readonly-document .editor-head').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                    fits(page,'.readonly-document .editor-head button:last-child')
                    page.get_by_title('返回会话').click()
                    expect(page.locator('.source-chip')).to_be_visible()
                    page.get_by_role('button',name='返回会话列表').click()
                    expect(page.get_by_role('button',name='示例流程讨论',exact=True)).to_be_visible()
                    page.close()
                checks.append('375/320 conversation, source preview, synthetic document and return navigation')

                page=page_at('/tests/visual/?fixture=conversation-long',320,720)
                page.get_by_role('button',name='示例流程讨论',exact=True).click()
                expect(page.locator('.user-message')).to_have_count(40)
                assert page.locator('.chat-log').evaluate('(e)=>e.scrollHeight>e.clientHeight && e.scrollWidth<=e.clientWidth+1')
                assert page.locator('.user-message').first.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                page.close()
                page=page_at('/tests/visual/?fixture=conversation-source-missing',320,720)
                page.get_by_role('button',name='示例流程讨论',exact=True).click()
                page.locator('.source-chip').click()
                dialog=page.get_by_role('dialog',name='引用原文')
                expect(dialog.get_by_text('Synthetic source unavailable',exact=False)).to_be_visible()
                expect(dialog.get_by_role('button',name='打开当前文档')).to_have_count(0)
                dialog.get_by_role('button',name='关闭引用').click()
                expect(page.locator('.source-chip')).to_be_visible()
                page.close()
                checks.append('40 long unbroken conversation turns wrap and scroll; missing synthetic source is reported')

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html?fixture=conversation',width,height)
                    web=page_at('/tests/visual/?fixture=conversation',width,height)
                    for page in (ref,web):
                        page.get_by_role('button',name='搜索会话').click()
                        expect(page.get_by_role('dialog',name='会话列表')).to_be_visible()
                    a=ref.get_by_role('dialog',name='会话列表').bounding_box()
                    b=web.get_by_role('dialog',name='会话列表').bounding_box()
                    for key in ('x','y','width','height'): assert abs(a[key]-b[key])<=1,(key,a,b)
                    ref.close();web.close()
                checks.append('1600/1280 conversation search dialog geometry compared with desktop reference')

                for width,height in ((375,720),(320,720),(320,480)):
                    page=page_at('/tests/visual/?fixture=conversation',width,height)
                    page.get_by_role('button',name='搜索会话').click()
                    dialog=page.get_by_role('dialog',name='会话列表')
                    query=dialog.get_by_role('combobox',name='搜索会话')
                    query.fill('整理')
                    expect(dialog.get_by_role('option')).to_have_count(1)
                    if width==320 and height==720: page.screenshot(path=str(EVIDENCE / 'history-search-phone.png'))
                    query.fill('X'*5000)
                    expect(dialog.get_by_text('没有找到相关会话')).to_be_visible()
                    query.fill('流程');query.press('Enter')
                    expect(page.locator('.source-chip')).to_be_visible()
                    page.get_by_role('button',name='返回会话列表').click()
                    page.get_by_role('button',name='示例流程讨论 的选项').click()
                    page.get_by_role('menuitem',name='重命名').click()
                    rename=page.get_by_role('dialog',name='重命名问答')
                    field=rename.get_by_role('textbox',name='问答名称')
                    field.fill('   ')
                    expect(rename.get_by_role('button',name='保存',exact=True)).to_be_disabled()
                    field.fill('X'*1000)
                    rename.get_by_role('button',name='保存',exact=True).click()
                    expect(rename.get_by_role('alert')).to_contain_text('Not available in the visual-only test bridge: edit_conversation')
                    assert field.input_value()=='X'*1000
                    if width==320 and height==720: page.screenshot(path=str(EVIDENCE / 'history-rename-phone.png'))
                    rename.get_by_role('button',name='取消',exact=True).click()
                    page.get_by_role('button',name='示例流程讨论 的选项').click()
                    page.get_by_role('menuitem',name='删除').click()
                    expect(page.get_by_text('Not available in the visual-only test bridge: edit_conversation',exact=False)).to_be_visible()
                    expect(page.get_by_role('button',name='示例流程讨论',exact=True)).to_be_visible()
                    page.close()
                page=page_at('/tests/visual/?fixture=conversation-many',320,720)
                page.get_by_role('button',name='搜索会话').click()
                dialog=page.get_by_role('dialog',name='会话列表')
                expect(dialog.get_by_role('option')).to_have_count(121)
                assert dialog.locator('.history-search-results').evaluate('(e)=>e.scrollHeight>e.clientHeight && e.scrollWidth<=e.clientWidth+1')
                page.close()
                checks.append('375/320 history search, keyboard selection, 121 long titles and rejected rename/delete')

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html?fixture=conversation',width,height)
                    web=page_at('/tests/visual/?fixture=conversation',width,height)
                    for page in (ref,web):
                        page.get_by_role('button',name='示例流程讨论',exact=True).click()
                        page.locator('.user-turn').hover()
                        page.get_by_role('button',name='编辑问题').click()
                        expect(page.get_by_role('textbox',name='编辑问题')).to_be_visible()
                    a=ref.locator('.message-editor').bounding_box();b=web.locator('.message-editor').bounding_box()
                    for key in ('x','y','width','height'): assert abs(a[key]-b[key])<=1,(key,a,b)
                    ref.close();web.close()
                checks.append('1600/1280 question editor geometry compared with desktop reference')

                for width,height in ((375,720),(320,720),(320,480)):
                    page=page_at('/tests/visual/?fixture=conversation',width,height)
                    page.get_by_role('button',name='示例流程讨论',exact=True).click()
                    page.locator('.user-turn').hover()
                    page.get_by_role('button',name='编辑问题').click()
                    editor=page.get_by_role('textbox',name='编辑问题')
                    editor.fill('不应保存的草稿')
                    page.get_by_role('button',name='取消',exact=True).click()
                    expect(page.locator('.user-message')).to_have_text('示例项目的流程是什么？')
                    page.locator('.user-turn').hover()
                    page.get_by_role('button',name='编辑问题').click()
                    editor=page.get_by_role('textbox',name='编辑问题')
                    if width==320 and height==720: page.screenshot(path=str(EVIDENCE / 'message-edit-phone.png'))
                    editor.fill('   ')
                    expect(page.get_by_role('button',name='保存并发送')).to_be_disabled()
                    editor.fill('X'*1000)
                    page.get_by_role('button',name='保存并发送').click()
                    expect(page.get_by_text('Not available in the visual-only test bridge: run_query',exact=False)).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    page.close()
                page=page_at('/tests/visual/?fixture=conversation',320,720)
                page.get_by_role('button',name='示例流程讨论',exact=True).click()
                page.locator('.user-turn').hover()
                page.locator('.user-turn').get_by_role('button',name='删除此轮问答').click()
                expect(page.get_by_text('Not available in the visual-only test bridge: replace_messages',exact=False)).to_be_visible()
                expect(page.locator('.user-message')).to_have_text('示例项目的流程是什么？')
                page.close()
                checks.append('375/320 question edit cancellation, empty/long inputs, rejected regeneration and deletion')

                def start_stream(page):
                    page.get_by_role('textbox',name='向你的文件提问').fill('请展示虚构流式回答')
                    page.get_by_role('button',name='发送问题').click()
                    expect(page.get_by_role('button',name='停止生成')).to_be_visible()
                    page.evaluate("window.__VISUAL_STREAM__.progress('虚构回答第一部分。')")
                    expect(page.locator('.answer-text')).to_contain_text('虚构回答第一部分。')

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html?fixture=stream',width,height)
                    web=page_at('/tests/visual/?fixture=stream',width,height)
                    for page in (ref,web): start_stream(page)
                    compare(stream_layout(ref),stream_layout(web))
                    if width==1600: web.screenshot(path=str(EVIDENCE / 'stream-desktop.png'))
                    for page in (ref,web):
                        page.evaluate("window.__VISUAL_STREAM__.progress(' 后续内容。')")
                        page.evaluate('window.__VISUAL_STREAM__.finish()')
                        expect(page.locator('.answer-text')).to_contain_text('后续内容。')
                        expect(page.get_by_role('button',name='发送问题')).to_be_visible()
                    ref.close();web.close()
                checks.append('1600/1280 synthetic streaming answer state compared with the desktop reference')

                for width in (375,320):
                    page=page_at('/tests/visual/?fixture=stream',width,720)
                    start_stream(page)
                    fits(page,'.composer .send')
                    if width==320: page.screenshot(path=str(EVIDENCE / 'stream-phone.png'))
                    page.get_by_role('button',name='停止生成').click()
                    expect(page.get_by_role('button',name='发送问题')).to_be_visible()
                    page.evaluate("window.__VISUAL_STREAM__.progress('迟到的虚构内容。')")
                    expect(page.locator('.answer-text')).not_to_contain_text('迟到的虚构内容。')
                    page.evaluate('window.__VISUAL_STREAM__.finish()')
                    expect(page.locator('.answer-text')).not_to_contain_text('迟到的虚构内容。')
                    page.close()
                page=page_at('/tests/visual/?fixture=stream',320,720)
                start_stream(page)
                page.evaluate("for(let i=0;i<120;i++) window.__VISUAL_STREAM__.progress('长虚构内容'.repeat(20))")
                expect(page.locator('.chat-log')).to_contain_text('长虚构内容')
                assert page.locator('.chat-log').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1 && e.scrollHeight>e.clientHeight')
                page.evaluate('window.__VISUAL_STREAM__.finish()')
                expect(page.get_by_role('button',name='发送问题')).to_be_visible()
                page.close()
                page=page_at('/tests/visual/?fixture=stream',320,720)
                start_stream(page)
                page.evaluate('window.__VISUAL_STREAM__.fail()')
                expect(page.get_by_text('Synthetic stream unavailable',exact=False)).to_be_visible()
                expect(page.get_by_role('button',name='发送问题')).to_be_visible()
                page.get_by_role('textbox',name='向你的文件提问').fill('再次尝试虚构问题')
                page.get_by_role('button',name='发送问题').click()
                expect(page.get_by_role('button',name='停止生成')).to_be_visible()
                page.evaluate("window.__VISUAL_STREAM__.progress('虚构重试回答。')")
                page.evaluate('window.__VISUAL_STREAM__.finish()')
                expect(page.locator('.answer-text')).to_contain_text('虚构重试回答。')
                page.close()
                checks.append('375/320 stream progress, cancellation and ignored late events, 120 chunks, synthetic failure and retry')

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html?fixture=stream',width,height)
                    web=page_at('/tests/visual/?fixture=stream',width,height)
                    for page in (ref,web):
                        start_stream(page)
                        page.evaluate('window.__VISUAL_STREAM__.tool()')
                        expect(page.locator('.tool-group.running')).to_be_visible()
                        page.evaluate('window.__VISUAL_STREAM__.tool(true)')
                        expect(page.locator('.tool-group.running')).to_have_count(0)
                        page.locator('.tool-group > summary').click()
                        page.locator('.tool-call > summary').click()
                        expect(page.locator('.tool-call')).to_have_attribute('data-phase','complete')
                        page.evaluate('window.__VISUAL_STREAM__.approval()')
                        expect(page.get_by_role('dialog',name='确认 MCP 工具调用')).to_be_visible()
                    a=ref.get_by_role('dialog',name='确认 MCP 工具调用').bounding_box()
                    b=web.get_by_role('dialog',name='确认 MCP 工具调用').bounding_box()
                    for key in ('x','y','width','height'): assert abs(a[key]-b[key])<=1,(key,a,b)
                    if width==1600: web.screenshot(path=str(EVIDENCE / 'tool-approval-desktop.png'))
                    ref.close();web.close()
                checks.append('1600/1280 synthetic tool progress and approval dialog compared with desktop reference')

                for width,height in ((375,720),(320,720),(320,480)):
                    page=page_at('/tests/visual/?fixture=stream',width,height)
                    start_stream(page)
                    page.evaluate('window.__VISUAL_STREAM__.tool()')
                    expect(page.locator('.tool-group.running')).to_be_visible()
                    page.evaluate('window.__VISUAL_STREAM__.tool(true,true)')
                    page.locator('.tool-group > summary').click()
                    page.locator('.tool-call > summary').click()
                    expect(page.locator('.tool-call')).to_have_attribute('data-phase','failed')
                    expect(page.locator('.tool-call')).to_contain_text('Synthetic tool failed')
                    page.evaluate('window.__VISUAL_STREAM__.approval(5000)')
                    dialog=page.get_by_role('dialog',name='确认 MCP 工具调用')
                    expect(dialog).to_be_visible()
                    fits(page,'.tool-approval-arguments')
                    fits(page,'.dialog-footer button:last-child')
                    assert dialog.locator('.tool-approval-arguments').evaluate('(e)=>e.scrollHeight>e.clientHeight')
                    if width==320 and height==720: page.screenshot(path=str(EVIDENCE / 'tool-approval-phone.png'))
                    dialog.get_by_role('button',name='拒绝').click()
                    expect(page.get_by_text('Not available in the visual-only test bridge: resolve_tool_approval',exact=False)).to_be_visible()
                    expect(dialog).to_be_hidden()
                    page.close()
                page=page_at('/tests/visual/?fixture=stream',320,720)
                start_stream(page)
                page.get_by_role('button',name='停止生成').click()
                expect(page.get_by_role('button',name='发送问题')).to_be_visible()
                page.evaluate('window.__VISUAL_STREAM__.approval()')
                expect(page.get_by_role('dialog',name='确认 MCP 工具调用')).to_have_count(0)
                page.evaluate('window.__VISUAL_STREAM__.finish()')
                page.close()
                checks.append('375/320 failed tool details, 5000-character approval and rejected mock action; late approval ignored')

                def synthetic_search(page,query='示例流程'):
                    page.get_by_role('button',name='搜索',exact=True).click()
                    page.get_by_role('textbox',name='搜索关键词').fill(query)
                    page.get_by_role('button',name='搜索文件',exact=True).click()

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html?fixture=search',width,height)
                    web=page_at('/tests/visual/?fixture=search',width,height)
                    for page in (ref,web):
                        synthetic_search(page)
                        expect(page.locator('.search-preview-body')).to_contain_text('示例流程：整理资料后进行复核。')
                    compare(search_layout(ref),search_layout(web))
                    if width==1600: web.screenshot(path=str(EVIDENCE / 'search-desktop.png'))
                    ref.close();web.close()
                checks.append('1600/1280 synthetic search result and source geometry compared with desktop reference')

                for width in (768,375,320):
                    page=page_at('/tests/visual/?fixture=search',width,720)
                    synthetic_search(page)
                    expect(page.locator('.search-preview-body')).to_contain_text('示例流程：整理资料后进行复核。')
                    field=page.get_by_role('textbox',name='搜索关键词')
                    assert field.input_value()=='示例流程' and field.bounding_box()['width']>=80
                    fits(page,'.search-composer.compact')
                    if width<=480:
                        assert page.locator('.search-preview-title strong').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                        page.get_by_role('button',name='返回结果列表').click()
                        expect(page.locator('.search-result')).to_be_visible()
                        page.locator('.search-result').click()
                        expect(page.locator('.search-preview-body')).to_be_visible()
                    if width==320: page.screenshot(path=str(EVIDENCE / 'search-phone.png'))
                    page.close()
                checks.append('768/375/320 search query, source preview and result-list navigation remain usable')

                page=page_at('/tests/visual/?fixture=search-many',320,720)
                synthetic_search(page)
                expect(page.locator('.search-result')).to_have_count(20)
                page.get_by_role('button',name='返回结果列表').click()
                expect(page.locator('.search-pagination-footer')).to_contain_text('第 1–20 个，共 45 个文件')
                page.get_by_role('button',name='下一页').click()
                expect(page.locator('.search-pagination-footer')).to_contain_text('第 21–40 个，共 45 个文件')
                page.get_by_role('button',name='下一页').click()
                expect(page.locator('.search-pagination-footer')).to_contain_text('第 41–45 个，共 45 个文件')
                expect(page.locator('.search-result')).to_have_count(5)
                expect(page.get_by_role('button',name='下一页')).to_be_disabled()
                page.close()
                page=page_at('/tests/visual/?fixture=search',320,720)
                synthetic_search(page,'没有匹配')
                expect(page.get_by_role('heading',name='没有找到相关文件')).to_be_visible()
                page.close()
                page=page_at('/tests/visual/?fixture=search-source-missing',320,720)
                synthetic_search(page)
                expect(page.locator('.search-preview-note')).to_contain_text('Synthetic source unavailable')
                page.get_by_role('button',name='返回结果列表').click()
                expect(page.locator('.search-result')).to_be_visible()
                page.close()
                checks.append('45 synthetic results across three pages, empty result and source-read failure')

                def open_folder(page):
                    page.get_by_role('button',name='文件',exact=True).click()
                    expect(page.get_by_role('heading',name='已索引文件')).to_be_visible()
                    page.locator('.simple-file-row',has_text='示例知识库').first.click()
                    expect(page.get_by_role('heading',name='示例知识库')).to_be_visible()

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html?fixture=files',width,height)
                    web=page_at('/tests/visual/?fixture=files',width,height)
                    for page in (ref,web): open_folder(page)
                    compare(files_layout(ref),files_layout(web))
                    if width==1600: web.screenshot(path=str(EVIDENCE / 'files-desktop.png'))
                    ref.close();web.close()
                checks.append('1600/1280 synthetic file workspace geometry compared with desktop reference')

                for width in (768,375,320):
                    page=page_at('/tests/visual/?fixture=files',width,720)
                    open_folder(page)
                    title=page.get_by_role('heading',name='示例知识库')
                    assert title.evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                    fits(page,'.library-folder-title')
                    if width==320: page.screenshot(path=str(EVIDENCE / 'files-phone.png'))
                    page.locator('.simple-file-row',has_text='子目录').click()
                    expect(page.get_by_role('heading',name='子目录')).to_be_visible()
                    expect(page.locator('.simple-file-row',has_text='子文档.txt')).to_be_visible()
                    page.get_by_role('button',name='返回上层').click()
                    expect(page.get_by_role('heading',name='示例知识库')).to_be_visible()
                    page.locator('.simple-file-row',has_text='示例文档.md').click()
                    editor=page.get_by_role('textbox',name='文档正文')
                    expect(editor).to_contain_text('虚构示例文档')
                    assert page.locator('.wysiwyg-editor .editor-head').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
                    if width==320:
                        toolbar=page.locator('.native-editor-toolbar')
                        assert toolbar.evaluate('(e)=>e.scrollWidth>e.clientWidth && getComputedStyle(e).overflowX==="auto"')
                        page.screenshot(path=str(EVIDENCE / 'editor-phone.png'))
                    page.close()
                checks.append('768/375/320 folder hierarchy and synthetic Markdown editor; phone toolbar scrolls')

                page=page_at('/tests/visual/?fixture=files-many',320,720)
                open_folder(page)
                expect(page.locator('.simple-file-row')).to_have_count(124)
                assert page.locator('.library-files').evaluate('(e)=>e.scrollHeight>e.clientHeight && e.scrollWidth<=e.clientWidth+1')
                page.close()
                page=page_at('/tests/visual/?fixture=empty',320,720)
                page.get_by_role('button',name='文件',exact=True).click()
                expect(page.get_by_text('添加文件夹并完成索引后，文件会显示在这里。')).to_be_visible()
                page.close()
                page=page_at('/tests/visual/?fixture=files-source-missing',320,720)
                open_folder(page)
                page.locator('.simple-file-row',has_text='操作手册.txt').click()
                expect(page.get_by_text('Synthetic source unavailable',exact=False)).to_be_visible()
                expect(page.get_by_role('heading',name='示例知识库')).to_be_visible()
                page.close()
                page=page_at('/tests/visual/?fixture=files',320,720)
                open_folder(page)
                page.locator('.simple-file-row',has_text='示例文档.md').click()
                editor=page.get_by_role('textbox',name='文档正文')
                editor.click();page.keyboard.press('End');page.keyboard.type('test')
                expect(page.locator('.document-status')).to_have_text('未保存')
                page.get_by_role('button',name='保存',exact=True).click()
                expect(page.get_by_text('Not available in the visual-only test bridge: save_document',exact=False)).to_be_visible()
                expect(page.locator('.document-status')).to_have_text('未保存')
                page.close()
                checks.append('120 long filenames, empty library, source-read failure and rejected save preserve the unsaved editor')

                def open_new_document_dialog(page):
                    page.get_by_role('button',name='文件',exact=True).click()
                    page.get_by_role('button',name='新建文档').click()
                    expect(page.get_by_role('textbox',name='文档正文')).to_be_visible()
                    page.get_by_role('button',name='保存',exact=True).click()
                    dialog=page.get_by_role('dialog',name='保存文档')
                    expect(dialog).to_be_visible()
                    return dialog

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html?fixture=files',width,height)
                    web=page_at('/tests/visual/?fixture=files',width,height)
                    for page in (ref,web): open_new_document_dialog(page)
                    a=ref.get_by_role('dialog',name='保存文档').bounding_box()
                    b=web.get_by_role('dialog',name='保存文档').bounding_box()
                    for key in ('x','y','width','height'): assert abs(a[key]-b[key])<=1,(key,a,b)
                    if width==1600: web.screenshot(path=str(EVIDENCE / 'new-document-desktop.png'))
                    ref.close();web.close()
                checks.append('1600/1280 new-document save dialog compared with desktop reference')

                for width,height in ((375,720),(320,720),(320,480)):
                    page=page_at('/tests/visual/?fixture=files',width,height)
                    dialog=open_new_document_dialog(page)
                    name=dialog.get_by_role('textbox',name='文件名')
                    name.fill('')
                    expect(dialog.get_by_role('button',name='保存',exact=True)).to_be_disabled()
                    for invalid in ('CON','bad/name'):
                        name.fill(invalid)
                        dialog.get_by_role('button',name='保存',exact=True).click()
                        expect(dialog.get_by_role('alert')).to_contain_text('请输入有效的 Markdown 文件名')
                        assert name.input_value()==invalid
                    name.fill('虚构文档'+'X'*200)
                    dialog.get_by_role('button',name='展开示例知识库').click()
                    dialog.get_by_role('button',name='子目录',exact=True).click()
                    expect(dialog.locator('.save-folder-tree .selected')).to_contain_text('子目录')
                    if width==320 and height==720: page.screenshot(path=str(EVIDENCE / 'new-document-phone.png'))
                    page.evaluate('''() => {
                      const original=window.__TAURI_INTERNALS__.invoke;
                      window.__TAURI_INTERNALS__.invoke=(command,args)=>{
                        if(command==='save_document')window.__VISUAL_SAVE_ATTEMPT__=structuredClone(args);
                        return original(command,args);
                      };
                    }''')
                    dialog.get_by_role('button',name='保存',exact=True).click()
                    expect(page.get_by_text('Not available in the visual-only test bridge: save_document',exact=False)).to_be_visible()
                    expect(page.locator('.document-status')).to_have_text('未保存')
                    attempt=page.evaluate('window.__VISUAL_SAVE_ATTEMPT__')
                    assert attempt['path']=='/demo/示例知识库/子目录/虚构文档'+'X'*200+'.md',attempt
                    assert attempt['expectedHash'] is None,attempt
                    page.close()
                page=page_at('/tests/visual/?fixture=empty',320,720)
                dialog=open_new_document_dialog(page)
                expect(dialog.get_by_text('请先添加一个文件夹，再保存文档。')).to_be_visible()
                expect(dialog.get_by_role('button',name='保存',exact=True)).to_be_disabled()
                dialog.get_by_role('button',name='添加文件夹').click()
                picker=page.get_by_role('dialog',name='添加文件夹')
                expect(picker).to_be_visible()
                picker.get_by_role('button',name='取消',exact=True).click()
                expect(page.get_by_role('dialog',name='保存文档')).to_be_visible()
                page.close()
                checks.append('375/320 new-document location, blank/reserved/path names, long name, empty library and rejected save')

                def open_picker(page,width):
                    if width<960: page.get_by_role('button',name='展开侧边栏').click()
                    page.locator('.sidebar [aria-label="添加文件夹"]').click()
                    dialog=page.get_by_role('dialog',name='添加文件夹')
                    expect(dialog.get_by_role('checkbox',name='选择 项目资料')).to_be_visible()
                    return dialog

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html',width,height)
                    web=page_at('/tests/visual/',width,height)
                    for page in (ref,web): open_picker(page,width)
                    compare(picker_layout(ref),picker_layout(web))
                    if width==1600: web.screenshot(path=str(EVIDENCE / 'picker-desktop.png'))
                    ref.close();web.close()
                checks.append('1600/1280 folder picker geometry compared with the desktop reference')

                for width,height in ((375,720),(320,720),(320,480)):
                    page=page_at('/tests/visual/',width,height)
                    dialog=open_picker(page,width)
                    dialog.get_by_role('checkbox',name='选择 项目资料').check()
                    dialog.get_by_role('button',name='项目资料',exact=True).click()
                    expect(dialog.get_by_role('checkbox',name='选择 子资料')).to_be_visible()
                    expect(dialog.locator('.folder-picker-selection')).to_contain_text('/demo/项目资料')
                    dialog.get_by_role('button',name='返回上级文件夹').click()
                    dialog.get_by_role('checkbox',name='选择 示例文档').check()
                    dialog.get_by_text('显示隐藏文件夹').click()
                    expect(dialog.get_by_role('checkbox',name='选择 .隐藏示例')).to_be_visible()
                    dialog.get_by_role('button',name='索引选项').click()
                    dialog.get_by_role('checkbox',name='索引 代码').check()
                    if width==320 and height==720: page.screenshot(path=str(EVIDENCE / 'picker-options-phone.png'))
                    path=dialog.get_by_role('textbox',name='文件夹路径')
                    path.fill('/missing');path.press('Enter')
                    expect(dialog.get_by_role('alert')).to_contain_text('Synthetic folder unavailable')
                    expect(dialog.locator('.folder-picker-selection')).to_contain_text('/demo/项目资料')
                    dialog.get_by_role('button',name='用户目录').click()
                    dialog.get_by_role('button',name='添加 2 个文件夹').click()
                    expect(dialog.get_by_role('alert')).to_contain_text('Not available in the visual-only test bridge: add_root_with_options')
                    expect(dialog).to_be_visible()
                    dialog.get_by_role('button',name='取消',exact=True).click()
                    expect(page.get_by_role('button',name='展开侧边栏')).to_be_focused()
                    page.close()
                page=page_at('/tests/visual/?fixture=folders-many',320,720)
                dialog=open_picker(page,320)
                expect(dialog.locator('.folder-picker-row')).to_have_count(122)
                assert dialog.locator('.folder-picker-content').evaluate('(e)=>e.scrollHeight>e.clientHeight && e.scrollWidth<=e.clientWidth+1')
                page.close()
                checks.append('375/320 folder navigation, multi-selection, hidden items, options, 120 long folders and read/add failures')

                def open_settings(page,width,english=False):
                    if width<960: page.get_by_role('button',name='Expand sidebar' if english else '展开侧边栏').click()
                    page.locator('.sidebar-settings').click()
                    dialog=page.get_by_role('dialog',name='Settings' if english else '设置')
                    expect(dialog).to_be_visible()
                    return dialog

                for width,height in ((1600,900),(1280,850)):
                    ref=page_at('/tests/browser/reference.html',width,height)
                    web=page_at('/tests/visual/',width,height)
                    for page in (ref,web): open_settings(page,width)
                    compare(settings_layout(ref),settings_layout(web))
                    for page in (ref,web): page.locator('.settings-nav').get_by_role('button',name='外观',exact=True).click()
                    compare(settings_layout(ref),settings_layout(web))
                    if width==1600: web.screenshot(path=str(EVIDENCE / 'settings-desktop.png'))
                    ref.close();web.close()
                checks.append('1600/1280 general and appearance settings geometry compared with the desktop reference')

                categories=['通用','外观','文件设置','网页剪藏','快捷键','模型设置','问答设置','搜索设置','CLI设置','数据与隐私','关于']
                for width,height in ((375,720),(320,720),(320,480)):
                    page=page_at('/tests/visual/',width,height)
                    dialog=open_settings(page,width)
                    for category in categories:
                        dialog.locator('.settings-nav').get_by_role('button',name=category,exact=True).click()
                        expect(dialog.locator('.settings-page-heading h2')).to_have_text(category)
                        assert dialog.locator('.settings-content').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1'),category
                    expect(dialog.locator('.settings-about h3')).to_have_text('Super-SAG')
                    if width==320 and height==720: page.screenshot(path=str(EVIDENCE / 'settings-about-phone.png'))
                    dialog.locator('.settings-nav').get_by_role('button',name='外观',exact=True).click()
                    for thumbnail in dialog.locator('.theme-thumbnail').all():
                        box=thumbnail.bounding_box();panel=dialog.locator('.settings-content').bounding_box()
                        assert box and panel and box['x']>=panel['x'] and box['x']+box['width']<=panel['x']+panel['width']+1,(box,panel)
                    dialog.locator('.theme-choice[title=深色]').click()
                    expect(dialog.get_by_role('radio',name='深色')).to_be_checked()
                    assert page.locator('html').get_attribute('data-theme')=='dark'
                    if width==320 and height==720: page.screenshot(path=str(EVIDENCE / 'settings-appearance-phone.png'))
                    dialog.get_by_role('button',name='关闭设置').click()
                    expect(page.get_by_role('button',name='展开侧边栏')).to_be_focused()
                    assert page.locator('html').get_attribute('data-theme')=='light'
                    page.close()
                checks.append('375/320 settings categories, theme choices, preview and cancel restoration; Web about branding')

                page=page_at('/tests/visual/',320,720)
                dialog=open_settings(page,320)
                dialog.locator('.settings-nav').get_by_role('button',name='文件设置',exact=True).click()
                workers=dialog.get_by_role('spinbutton',name='索引并行数')
                for value,valid in [('0',False),('1',True),('64',True),('65',False)]:
                    workers.fill(value)
                    assert workers.evaluate('(e)=>e.validity.valid') is valid,(value,valid)
                workers.fill('64')
                dialog.get_by_role('button',name='保存设置').click()
                expect(dialog.locator('.settings-feedback .form-error')).to_contain_text('Not available in the visual-only test bridge: save_settings')
                assert workers.input_value()=='64'
                page.close()
                page=page_at('/tests/visual/?lang=en&theme=dark',320,720)
                dialog=open_settings(page,320,True)
                for category in ['General','Appearance','File settings','Web Clipper','Shortcuts','Model settings','Chat settings','Search settings','CLI settings','Data and privacy','About']:
                    dialog.locator('.settings-nav').get_by_role('button',name=category,exact=True).click()
                    expect(dialog.locator('.settings-page-heading h2')).to_have_text(category)
                expect(dialog.locator('.settings-about h3')).to_have_text('Super-SAG')
                page.close()
                checks.append('settings numeric bounds, rejected save retains input, and English/dark category navigation')

                # Empty and extreme fixture shapes; long titles stay inside the drawer.
                page=page_at('/tests/visual/?fixture=empty',375,720)
                expect(page.get_by_role('heading',name='你的文件，直接成为知识库。')).to_be_visible()
                expect(page.get_by_role('button',name='添加本地文件夹')).to_be_visible()
                page.close()
                page=page_at('/tests/visual/?fixture=long',375,720)
                page.get_by_role('button',name='展开侧边栏').click()
                expect(page.locator('.sidebar .tree-row')).to_have_count(120)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                assert page.locator('.sidebar .tree').evaluate('(e)=>e.scrollHeight>e.clientHeight')
                page.close()
                checks.append('empty library and 120 long folder names; scrollable sidebar without page overflow')

                # Theme/language and explicit startup failure and retry.
                page=page_at('/tests/visual/?theme=dark&lang=en',375,720)
                expect(page.get_by_role('heading',name='Ask your files')).to_be_visible()
                page.get_by_role('button',name='Expand sidebar').click()
                expect(page.locator('.brand')).to_have_text('Super-SAG')
                assert page.locator('.brand-row .brand-mark').evaluate('(e)=>getComputedStyle(e).filter')=='none'
                page.close()
                page=page_at('/tests/visual/?fixture=offline',1280,850)
                expect(page.get_by_text('无法连接本地 SAG 服务')).to_be_visible()
                expect(page.get_by_text('Synthetic service unavailable',exact=False)).to_be_visible()
                page.get_by_role('button',name='重试').click()
                expect(page.get_by_text('无法连接本地 SAG 服务')).to_be_visible()
                page.close()
                checks.append('English/dark brand; synthetic startup failure and retry remains failed')

                version=browser.version
                context.close();browser.close()
            if errors:
                raise AssertionError('Browser page errors: ' + '; '.join(errors))
            (EVIDENCE / 'result.json').write_text(json.dumps({
                'browser':'Chromium '+version,'reference_commit':'ded11e3f0f4719ea671678447f78be2248c04da2',
                'checks':checks,'page_errors':errors,
                'limitations':['Synthetic test fixture, no Web backend or real files',
                               'No Windows native installation or upgrade',
                               'Only workspace, navigation, sidebar and entry points; complete pages remain unaccepted']
            },ensure_ascii=False,indent=2)+'\n')
            print('Web workspace visual checks passed:',EVIDENCE)
            for check in checks: print(' -',check)
        finally:
            process.terminate()
            try: process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=5)


if __name__=='__main__':
    main()
