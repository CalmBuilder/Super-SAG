import type {AppPlatform} from '../lib/platform';

/** The visual stage has no server. Never turn desktop commands into HTTP calls. */
export function createBrowserPlatform(): AppPlatform {
  return {
    async invoke() { throw new Error('Web 服务尚未接通'); },
    async listen() { return () => {}; },
  };
}
