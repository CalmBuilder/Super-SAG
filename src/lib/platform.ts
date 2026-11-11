import {invoke as desktopInvoke} from '@tauri-apps/api/core';
import {listen as desktopListen} from '@tauri-apps/api/event';
import type {EventCallback, EventName, Options, UnlistenFn} from '@tauri-apps/api/event';

/** Platform operations used by the shared desktop interface. */
export interface AppPlatform {
  invoke<T>(command: string, args?: Record<string, unknown>): Promise<T>;
  listen<T>(event: EventName, handler: EventCallback<T>, options?: Options): Promise<UnlistenFn>;
}

const desktopPlatform: AppPlatform = {
  invoke: (command, args) => desktopInvoke(command, args),
  listen: (event, handler, options) => desktopListen(event, handler, options),
};

let platform = desktopPlatform;

/** Install the platform before mounting an application; never expose it as a remote command proxy. */
export function setAppPlatform(next: AppPlatform): () => void {
  const previous = platform;
  platform = next;
  return () => { if (platform === next) platform = previous; };
}

export function invokePlatform<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  return platform.invoke<T>(command, args);
}

export function listen<T>(event: EventName, handler: EventCallback<T>, options?: Options): Promise<UnlistenFn> {
  return platform.listen(event, handler, options);
}
