"""Load the real unpacked Chrome extension and save to isolated OPFS directories.

The directory handles are browser-managed test directories, not a Windows
Documents folder; native folder-picker and Windows upgrade acceptance remain open.
Run npm run build:clipper before this test.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[2]
extension=ROOT/'browser-extension/build/chrome'
assert (extension/'manifest.json').is_file(), 'Run npm run build:clipper first'
with tempfile.TemporaryDirectory(prefix='super-sag-extension-') as profile:
 with sync_playwright() as playwright:
  context=playwright.chromium.launch_persistent_context(profile,channel='chromium',headless=True,viewport={'width':760,'height':630},args=[f'--disable-extensions-except={extension}',f'--load-extension={extension}','--no-sandbox'])
  try:
   workers=context.service_workers
   if not workers: workers=[context.wait_for_event('serviceworker',timeout=30000)]
   extension_id=workers[0].url.split('/')[2]
   page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
   page.goto(f'chrome-extension://{extension_id}/options.html',wait_until='load')
   expect(page.locator('#destination option:checked')).to_contain_text('Documents/super-sag/clippings')
   if '--docs' in sys.argv:
    for language,suffix in (('zh-CN','zh'),('en','en')):
     page.select_option('#language',language)
     for scheme,ending in (('light',''),('dark','-dark')):
      page.emulate_media(color_scheme=scheme)
      page.screenshot(path=str(ROOT/f'docs-site/public/images/extension-web-clipper-{suffix}{ending}.jpg'),type='jpeg',quality=92)
     page.emulate_media(color_scheme='light')
     page.evaluate('''suffix => { window.showDirectoryPicker = async () =>
       (await navigator.storage.getDirectory()).getDirectoryHandle(`Example folder ${suffix}`,{create:true}); }''', suffix)
     page.select_option('#destination','folder')
     page.locator('#choose-folder').click()
     expect(page.locator('#destination option:checked')).to_contain_text('Example folder')
     page.locator('#apply').click()
     expect(page.locator('#folder-notice')).to_be_visible()
     page.screenshot(path=str(ROOT/f'docs-site/public/images/extension-web-clipper-custom-{suffix}.jpg'),type='jpeg',quality=92)
     page.select_option('#destination','default')
   result=page.evaluate('''async () => {
    const root=await navigator.storage.getDirectory();
    const oldRoot=await root.getDirectoryHandle('sag-wiki',{create:true});
    const old=await oldRoot.getDirectoryHandle('clippings',{create:true});
    const currentRoot=await root.getDirectoryHandle('super-sag',{create:true});
    const current=await currentRoot.getDirectoryHandle('clippings',{create:true});
    const keep=await old.getFileHandle('original.md',{create:true});
    const writer=await keep.createWritable();await writer.write('old data');await writer.close();
    const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('sag-web-clipper',1);r.onupgradeneeded=()=>r.result.createObjectStore('settings');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
    const setHandle=handle=>new Promise((resolve,reject)=>{const tx=db.transaction('settings','readwrite');tx.objectStore('settings').put(handle,'default-directory');tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error)});
    const clip={title:'Synthetic test page',url:'https://example.invalid/brand',content:'# Test\\n\\nIsolated content.'};
    await setHandle(old);await chrome.storage.local.set({destination:'default',defaultPath:'Documents/sag-wiki/clippings'});
    const oldResult=await chrome.runtime.sendMessage({type:'save',clip});
    if(!oldResult.ok)throw Error('legacy save: '+oldResult.error);
    const oldNames=[];for await(const [name] of old.entries())oldNames.push(name);
    const oldFile=await (await old.getFileHandle(oldNames.find(n=>n!=='original.md'))).getFile();
    const original=await (await keep.getFile()).text();
    await setHandle(current);await chrome.storage.local.set({defaultPath:'Documents/super-sag/clippings'});
    const newResult=await chrome.runtime.sendMessage({type:'save',clip});
    if(!newResult.ok)throw Error('new save: '+newResult.error);
    const newNames=[];for await(const [name] of current.entries())newNames.push(name);
    const newFile=await (await current.getFileHandle(newNames[0])).getFile();
    const failed=await chrome.runtime.sendMessage({type:'save',clip:{...clip,content:''}});
    db.close();return {oldResult,newResult,oldNames,newNames,original,oldText:await oldFile.text(),newText:await newFile.text(),failed};
   }''')
   assert result['original']=='old data'
   assert len(result['oldNames'])==2 and len(result['newNames'])==1
   assert 'Isolated content.' in result['oldText'] and 'Isolated content.' in result['newText']
   assert not result['failed']['ok']
   assert not errors,errors
   print(json.dumps({'status':'passed','extension':'real Chromium unpacked extension','cases':['fresh default label','legacy save and preserved original','new save','empty content failure'],'scope':'isolated browser storage; no native folder picker or Windows acceptance'},ensure_ascii=False))
  finally: context.close()
