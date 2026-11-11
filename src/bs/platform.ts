import type {AppPlatform} from '../lib/platform';

/** Independent browser UI preferences; do not migrate the previous preview's storage. */
export const BROWSER_STORAGE_NAMESPACE = 'super-sag.web.v1.';

/** The visual stage has no server. Never turn desktop commands into HTTP calls. */
export function createBrowserPlatform(): AppPlatform {
  return {
    async invoke() { throw new Error('Web 服务尚未接通'); },
    async listen() { return () => {}; },
  };
}
