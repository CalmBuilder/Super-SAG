import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync, mkdirSync, copyFileSync, readFileSync, writeFileSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join, resolve} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const root=resolve(fileURLToPath(new URL('..',import.meta.url)));
test('Windows template preflight accepts the pinned tool and rejects drift',()=>{
  const temporary=mkdtempSync(join(tmpdir(),'super-sag-template-'));
  try{
    for(const dir of ['scripts','node_modules/@tauri-apps/cli','src-tauri/windows'])mkdirSync(join(temporary,dir),{recursive:true});
    copyFileSync(join(root,'scripts/check-windows-template.mjs'),join(temporary,'scripts/check-windows-template.mjs'));
    const template=readFileSync(join(root,'src-tauri/windows/installer.nsi'),'utf8');
    const templatePath=join(temporary,'src-tauri/windows/installer.nsi');
    const cliPath=join(temporary,'node_modules/@tauri-apps/cli/package.json');
    const windowsConfigPath=join(temporary,'src-tauri/tauri.windows.conf.json');
    const windowsConfig=JSON.parse(readFileSync(join(root,'src-tauri/tauri.windows.conf.json'),'utf8'));
    writeFileSync(templatePath,template);
    writeFileSync(windowsConfigPath,JSON.stringify(windowsConfig));
    const run=()=>spawnSync(process.execPath,[join(temporary,'scripts/check-windows-template.mjs')],{encoding:'utf8'});
    writeFileSync(cliPath,JSON.stringify({version:'2.12.2'}));
    assert.equal(run().status,0);
    writeFileSync(cliPath,JSON.stringify({version:'2.12.3'}));
    const wrongVersion=run();assert.notEqual(wrongVersion.status,0);assert.match(wrongVersion.stderr,/requires Tauri CLI 2\.12\.2/);
    writeFileSync(cliPath,JSON.stringify({version:'2.12.2'}));
    writeFileSync(templatePath,template.replace('Uninstall\\SAG Wiki','Uninstall\\Super-SAG'));
    const wrongIdentity=run();assert.notEqual(wrongIdentity.status,0);assert.match(wrongIdentity.stderr,/upgrade identity/);
    writeFileSync(templatePath,template);
    windowsConfig.app.windows=windowsConfig.app.windows.filter(window=>window.label!=='quick-search');
    writeFileSync(windowsConfigPath,JSON.stringify(windowsConfig));
    const missingQuickSearch=run();assert.notEqual(missingQuickSearch.status,0);assert.match(missingQuickSearch.stderr,/quick-search windows/);
  }finally{rmSync(temporary,{recursive:true,force:true});}
});
