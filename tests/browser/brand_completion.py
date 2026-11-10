"""Desktop UI brand regression in real Chromium with synthetic Tauri responses.

This is not a Windows installer, native filesystem, or business acceptance test.
Use --docs to replace affected documentation screenshots with sanitized fixtures.
"""
from __future__ import annotations
import json
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
OUTPUT = Path(os.environ.get('SAG_BRAND_COMPLETION_EVIDENCE_DIR', ROOT / '.cache/brand-completion'))
OUTPUT.mkdir(parents=True, exist_ok=True)
fixture = (ROOT / 'tests/visual/fixture.js').read_text()
mock = r'''
window.__BRAND_ACTIONS__=[];
const originalBrandInvoke=window.__TAURI_INTERNALS__.invoke;
const installedBrandSkills=new Set();
window.__TAURI_INTERNALS__.invoke=async(command,args={})=>{
 window.__BRAND_ACTIONS__.push({command,args});
 if(command==='list_roots') return [{path:'/demo/Documents/sag-wiki',name:'Super-SAG',status:new URLSearchParams(location.search).get('fixture')==='brand-partial'?'partial':'ready',count:3,error:new URLSearchParams(location.search).get('fixture')==='brand-partial'?'Failed to read /demo/Documents/sag-wiki/example.txt':null}];
 if(command==='get_web_clipper') return {packages:['chrome']};
 if(command==='get_cli_settings') {
  if(new URLSearchParams(location.search).get('fixture')==='cli-error' && !window.__BRAND_RETRIED__){window.__BRAND_RETRIED__=true;throw Error('Synthetic CLI unavailable');}
  return {access:{enabled:true},install_error:null,skill_url:'http://127.0.0.1:59598/super-sag.md',installations:['cli','claude-code','codex','opencode'].map(name=>({name,path:`/home/demo/skills/super-sag/${name}/SKILL.md`,installed:installedBrandSkills.has(name),version:null}))};
 }
 if(command==='install_cli_integration') {args.uninstall?installedBrandSkills.delete(args.target):installedBrandSkills.add(args.target);return 'ok';}
 return originalBrandInvoke(command,args);
};
'''
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
origin = f'http://127.0.0.1:{port}'
results, errors = [], []
with tempfile.TemporaryFile(mode='w+') as log:
    server = subprocess.Popen([str(ROOT / 'node_modules/.bin/vite'), '--host', '127.0.0.1', '--port', str(port), '--strictPort'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    try:
        for _ in range(150):
            if server.poll() is not None: raise RuntimeError('Vite exited before browser testing')
            try:
                with urlopen(origin, timeout=1): break
            except OSError: time.sleep(.2)
        else: raise RuntimeError('Vite did not start')
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
            for lang, labels in [('zh-CN', ('设置','关于','网页剪藏','CLI设置','Skill 安装指南','CLI 使用指南','复制 Codex 安装命令','安装 Codex','卸载 Codex')),
                                 ('en', ('Settings','About','Web Clipper','CLI settings','Skill installation guide','CLI usage guide','Copy the install command for Codex','Install Codex','Uninstall Codex'))]:
                for width,height,theme in [(960,600,'light'),(1280,850,'light'),(1920,1080,'dark')]:
                    ctx=browser.new_context(viewport={'width':width,'height':height},locale=lang,reduced_motion='reduce',permissions=['clipboard-read','clipboard-write'])
                    ctx.add_init_script(fixture+'\n'+mock)
                    page=ctx.new_page(); page.on('pageerror',lambda e:errors.append(str(e)))
                    page.goto(f'{origin}/?fixture=conversation&lang={lang}&theme={theme}',wait_until='networkidle')
                    root=page.locator('.tree-name').filter(has_text='Super-SAG').first
                    expect(root).to_be_visible(); assert 'sag-wiki' in root.get_attribute('title')
                    page.get_by_role('button',name=labels[0],exact=True).click()
                    dialog=page.get_by_role('dialog'); expect(dialog).to_be_visible()
                    dialog.get_by_role('button',name=labels[1],exact=True).click()
                    expect(dialog.locator('.settings-about h3')).to_have_text('Super-SAG')
                    expect(dialog.locator('.settings-about a')).to_have_count(0)
                    if width==1280:
                        p=OUTPUT/f'about-{lang}.png'; page.screenshot(path=str(p))
                        if '--docs' in sys.argv: (ROOT/'docs-site/public/images'/('product-about-cn.png' if lang=='zh-CN' else 'product-about-en.png')).write_bytes(p.read_bytes())
                    dialog.get_by_role('button',name=labels[2],exact=True).click()
                    expect(dialog.locator('.settings-content')).to_contain_text('super-sag/clippings')
                    if width==1280:
                        p=OUTPUT/f'clipper-{lang}.jpg'; dialog.screenshot(path=str(p),type='jpeg',quality=92)
                        if '--docs' in sys.argv: (ROOT/'docs-site/public/images'/('product-web-clipper-zh.jpg' if lang=='zh-CN' else 'product-web-clipper-en.jpg')).write_bytes(p.read_bytes())
                    dialog.get_by_role('button',name=labels[3],exact=True).click()
                    expect(dialog.locator('.settings-content')).to_contain_text('Super-SAG')
                    for command in ('super-sag install claude-code', 'super-sag install codex',
                                    'super-sag install opencode'):
                        expect(dialog.locator('.cli-settings')).to_contain_text(command)
                    expect(dialog.locator('.cli-settings')).to_contain_text('/super-sag.md')
                    dialog.get_by_role('button',name=labels[6],exact=True).click()
                    assert page.evaluate('navigator.clipboard.readText()')=='super-sag install codex'
                    dialog.get_by_role('button',name=labels[7],exact=True).click()
                    expect(dialog.get_by_role('button',name=labels[8],exact=True)).to_be_visible()
                    dialog.get_by_role('button',name=labels[8],exact=True).click()
                    expect(dialog.get_by_role('button',name=labels[7],exact=True)).to_be_visible()
                    dialog.get_by_role('button',name=labels[4],exact=True).click()
                    expect(dialog.locator('.cli-skill-path').first).to_contain_text('/super-sag/')
                    dialog.get_by_role('button',name=labels[5],exact=True).click()
                    for command in ('super-sag add', 'super-sag check', 'super-sag remove ./docs',
                                    'super-sag add ./docs', 'super-sag list', 'super-sag status',
                                    'super-sag config', 'super-sag service status',
                                    'super-sag service restart', 'super-sag --help', '-m 5', '--json'):
                        expect(dialog.locator('.cli-guide-content')).to_contain_text(command)
                    if width==1280:
                        dialog.get_by_role('button',name=labels[4],exact=True).click()
                        dialog.get_by_role('button',name=labels[5],exact=True).click()
                        dialog.locator('.settings-content').evaluate('(el)=>el.scrollTop=0')
                        p=OUTPUT/f'cli-{lang}.png'; dialog.screenshot(path=str(p))
                        if '--docs' in sys.argv: (ROOT/'docs-site/public/images'/('product-cli-settings-cn.png' if lang=='zh-CN' else 'product-cli-settings-en.png')).write_bytes(p.read_bytes())
                    results.append({'language':lang,'width':width,'height':height,'theme':theme,'case':'brand UI, copy, skill controls and guides'})
                    ctx.close()
            for lang,settings,chat in [('zh-CN','设置','问答设置'),('en','Settings','Chat settings')]:
                ctx=browser.new_context(viewport={'width':1280,'height':900},locale=lang,reduced_motion='reduce')
                ctx.add_init_script(fixture+'\n'+mock)
                page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(f'{origin}/?fixture=brand-partial&lang={lang}',wait_until='networkidle')
                expect(page.locator('.index-status-primary')).to_contain_text('Super-SAG')
                if '--docs' in sys.argv:
                    page.locator('.sidebar').screenshot(path=str(ROOT/'docs-site/public/images'/('product-index-status-cn.png' if lang=='zh-CN' else 'product-index-status-en.png')))
                page.locator('.index-status-link').click()
                expect(page.locator('.index-issues-dialog')).to_be_visible()
                if '--docs' in sys.argv:
                    page.locator('.index-issues-dialog').screenshot(path=str(ROOT/'docs-site/public/images'/('product-index-failure-cn.png' if lang=='zh-CN' else 'product-index-failure-en.png')))
                page.get_by_role('button',name='关闭索引详情' if lang=='zh-CN' else 'Close index details').click()
                page.get_by_role('button',name='隐藏索引状态' if lang=='zh-CN' else 'Hide indexing status').click()
                page.reload(wait_until='networkidle')
                expect(page.locator('.index-status-link')).to_have_count(0)
                page.get_by_role('button',name='文件' if lang=='zh-CN' else 'Files',exact=True).click()
                if '--docs' in sys.argv:
                    page.screenshot(path=str(ROOT/'docs-site/public/images'/('product-index-status-dismissed-cn.png' if lang=='zh-CN' else 'product-index-status-dismissed-en.png')))
                page.get_by_role('button',name=settings,exact=True).click()
                dialog=page.get_by_role('dialog');dialog.get_by_role('button',name=chat,exact=True).click()
                tools=dialog.locator('.sag-tools');tools.scroll_into_view_if_needed()
                expect(tools).to_contain_text('Super-SAG')
                if '--docs' in sys.argv:
                    dialog.screenshot(path=str(ROOT/'docs-site/public/images'/('product-tools-cn.png' if lang=='zh-CN' else 'product-tools-en.png')))
                results.append({'language':lang,'case':'index status, failure details and built-in tool branding'})
                ctx.close()
            ctx=browser.new_context(viewport={'width':1280,'height':850},locale='zh-CN',reduced_motion='reduce')
            ctx.add_init_script(fixture+'\n'+mock)
            page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(f'{origin}/?fixture=cli-error&lang=zh-CN',wait_until='networkidle')
            page.get_by_role('button',name='设置',exact=True).click()
            dialog=page.get_by_role('dialog')
            dialog.get_by_role('button',name='CLI设置',exact=True).click()
            expect(dialog.locator('.cli-feedback[role=alert]')).to_contain_text('Synthetic CLI unavailable')
            dialog.get_by_role('button',name='重试',exact=True).click()
            expect(dialog.locator('.cli-settings')).to_contain_text('super-sag install codex')
            results.append({'language':'zh-CN','case':'CLI error and retry'})
            ctx.close()
            assert not errors, errors
            browser_version=browser.version;browser.close()
        (OUTPUT/'result.json').write_text(json.dumps({'scope':'Chromium with synthetic Tauri responses; not native Windows or business acceptance','browser':browser_version,'cases':results,'page_errors':errors},ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'browser':browser_version,'passed_cases':len(results),'evidence':str(OUTPUT)},ensure_ascii=False))
    finally:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill();server.wait()
