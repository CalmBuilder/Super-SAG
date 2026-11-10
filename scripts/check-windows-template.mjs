import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';

const root = resolve(fileURLToPath(new URL('..', import.meta.url)));
const version = JSON.parse(readFileSync(resolve(root, 'node_modules/@tauri-apps/cli/package.json'), 'utf8')).version;
if (version !== '2.12.2') {
  throw new Error(`Windows installer template requires Tauri CLI 2.12.2, found ${version}. Review and update the pinned template before building.`);
}
const template = readFileSync(resolve(root, 'src-tauri/windows/installer.nsi'), 'utf8');
for (const required of [
  '!define UNINSTKEY "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\SAG Wiki"',
  '!define MANUPRODUCTKEY "${MANUKEY}\\SAG Wiki"',
]) {
  if (!template.includes(required)) throw new Error('The Windows installer template no longer preserves the legacy upgrade identity.');
}
// Platform-specific arrays replace the base array during Tauri configuration
// merging, so both windows must be explicitly present in the Windows config.
const config = JSON.parse(readFileSync(resolve(root, 'src-tauri/tauri.windows.conf.json'), 'utf8'));
const baseConfig = JSON.parse(readFileSync(resolve(root, 'src-tauri/tauri.conf.json'), 'utf8'));
const windows = config.app?.windows ?? [];
const main = windows.find(window => window.label === 'main');
const quick = windows.find(window => window.label === 'quick-search');
if (!main || !quick || quick.url !== 'index.html?quick-search' || quick.visible !== false || quick.skipTaskbar !== true) {
  throw new Error('Windows configuration must retain the main and hidden quick-search windows.');
}
const licenseFiles = baseConfig.bundle.resources.filter(path => path.startsWith('licenses/'));
for (const license of licenseFiles) {
  if (config.bundle?.resources?.[license] !== license) {
    throw new Error(`Windows installer must include the bundled license ${license}.`);
  }
}
console.log('Windows installer template and Tauri CLI version checked.');
