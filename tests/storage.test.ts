// @vitest-environment happy-dom
import {afterEach, describe, expect, it} from 'vitest';
import {appStorage, setStorageNamespace} from '../src/lib/storage';
import {BROWSER_STORAGE_NAMESPACE} from '../src/bs/platform';

afterEach(() => localStorage.clear());

describe('UI preference storage isolation', () => {
  it('keeps the existing desktop keys and only clears the requested desktop prefix', () => {
    localStorage.setItem('sag.sidebar.expanded', '["desktop"]');
    localStorage.setItem('unrelated', 'keep');
    expect(appStorage.getItem('sag.sidebar.expanded')).toBe('["desktop"]');
    appStorage.setItem('sag.search.mode', 'search');
    expect(localStorage.getItem('sag.search.mode')).toBe('search');
    appStorage.removePrefix('sag.');
    expect(localStorage.getItem('sag.sidebar.expanded')).toBeNull();
    expect(localStorage.getItem('unrelated')).toBe('keep');
  });

  it('ignores and preserves old same-origin keys during browser reads, writes and clearing', () => {
    localStorage.setItem('sag.sidebar.expanded', '{old invalid value');
    localStorage.setItem('sag.search.history', '["old"]');
    localStorage.setItem('unrelated', 'keep');
    const restore = setStorageNamespace(BROWSER_STORAGE_NAMESPACE);
    try {
      expect(appStorage.getItem('sag.sidebar.expanded')).toBeNull();
      appStorage.setItem('sag.sidebar.expanded', '["new"]');
      appStorage.setItem('sag.search.history', '["new"]');
      appStorage.setItem('other', 'browser-only');
      expect(() => appStorage.removePrefix('')).toThrow();
      expect(localStorage.getItem(`${BROWSER_STORAGE_NAMESPACE}sag.sidebar.expanded`)).toBe('["new"]');
      appStorage.removePrefix('sag.');
      expect(appStorage.getItem('sag.sidebar.expanded')).toBeNull();
      expect(appStorage.getItem('other')).toBe('browser-only');
      expect(localStorage.getItem('sag.sidebar.expanded')).toBe('{old invalid value');
      expect(localStorage.getItem('sag.search.history')).toBe('["old"]');
      expect(localStorage.getItem('unrelated')).toBe('keep');
    } finally {
      restore();
    }
    expect(appStorage.getItem('sag.search.history')).toBe('["old"]');
  });
});
