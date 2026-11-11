import {afterEach, describe, expect, it, vi} from 'vitest';
import type {AppPlatform} from '../src/lib/platform';

const native = vi.hoisted(() => ({
  invoke: vi.fn(async () => 'desktop-result'),
  listen: vi.fn(async () => () => {}),
}));
vi.mock('@tauri-apps/api/core', () => ({invoke: native.invoke}));
vi.mock('@tauri-apps/api/event', () => ({listen: native.listen}));

import {api} from '../src/lib/api';
import {listen, setAppPlatform} from '../src/lib/platform';
import {createBrowserPlatform} from '../src/bs/platform';

afterEach(() => vi.clearAllMocks());

describe('shared platform boundary', () => {
  it('continues forwarding desktop requests and event subscriptions to Tauri', async () => {
    const handler = vi.fn();
    expect(await api('list_roots', {scope: 'local'})).toBe('desktop-result');
    await listen('data-changed', handler);
    expect(native.invoke).toHaveBeenCalledWith('list_roots', {scope: 'local'});
    expect(native.listen).toHaveBeenCalledWith('data-changed', handler, undefined);
  });

  it('routes through an explicitly installed platform and restores the desktop platform', async () => {
    const invoke = vi.fn(async (_command: string, _args?: Record<string, unknown>) => 'browser-result');
    const subscribe = vi.fn(async () => () => {});
    const web: AppPlatform = {
      invoke: <T>(command: string, args?: Record<string, unknown>) => invoke(command, args) as Promise<T>,
      listen: subscribe,
    };
    const restore = setAppPlatform(web);
    try {
      expect(await api('list_roots')).toBe('browser-result');
      await listen('data-changed', () => {});
      expect(invoke).toHaveBeenCalledWith('list_roots', undefined);
      expect(subscribe).toHaveBeenCalledOnce();
      expect(native.invoke).not.toHaveBeenCalled();
      expect(native.listen).not.toHaveBeenCalled();
    } finally {
      restore();
    }
    expect(await api('list_roots')).toBe('desktop-result');
  });

  it('fails closed in the browser while the business service is not connected', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    const restore = setAppPlatform(createBrowserPlatform());
    try {
      await expect(api('read_document', {path: '/test/secret'})).rejects.toThrow('Web 服务尚未接通');
      await expect(api('unknown_command')).rejects.toThrow('Web 服务尚未接通');
      expect(native.invoke).not.toHaveBeenCalled();
      expect(fetchSpy).not.toHaveBeenCalled();
    } finally {
      restore();
      fetchSpy.mockRestore();
    }
  });
});
