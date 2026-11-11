import {readFileSync} from 'node:fs';
import {describe, expect, it} from 'vitest';

const bytes = (path: string) => readFileSync(new URL(`../${path}`, import.meta.url));

describe('Super-SAG icon assets', () => {
  it('uses the same vector source for the browser extension', () => {
    expect(bytes('browser-extension/assets/toolbar-icon.svg')).toEqual(bytes('assets/branding/super-sag-icon.svg'));
  });

  it('keeps the Chrome, Safari and desktop icons consistent at their shared sizes', () => {
    expect(bytes('src/assets/brand-icon.png')).toEqual(bytes('assets/branding/super-sag-icon.png'));
    for (const size of [16, 32, 128]) {
      const safari = bytes(`browser-extension/assets/macos/icon-${size}.png`);
      const chrome = bytes(`browser-extension/static/icon-${size}.png`);
      expect(safari).toEqual(chrome);
      expect(safari.readUInt32BE(16)).toBe(size);
      expect(safari.readUInt32BE(20)).toBe(size);
    }
    for (const [size, filename] of [[32, '32x32.png'], [128, '128x128.png'], [256, '128x128@2x.png']] as const) {
      const reference = bytes(`src-tauri/icons/super-sag/${filename}`);
      expect(bytes(`src-tauri/icons/${filename}`)).toEqual(reference);
      expect(bytes(`src-tauri/icons/windows/${filename}`)).toEqual(reference);
      expect(bytes(`browser-extension/assets/macos/icon-${size}.png`)).toEqual(reference);
    }
    expect(bytes('src-tauri/icons/icon.ico')).toEqual(bytes('src-tauri/icons/super-sag/icon.ico'));
    expect(bytes('src-tauri/icons/windows/icon.ico')).toEqual(bytes('src-tauri/icons/super-sag/icon.ico'));
    expect(bytes('src-tauri/icons/icon.icns')).toEqual(bytes('src-tauri/icons/super-sag/icon.icns'));
  });
});
