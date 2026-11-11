import {mount, unmount} from 'svelte';
import App from '../App.svelte';
import {setAppPlatform, type AppPlatform} from '../lib/platform';
import {createBrowserPlatform} from './platform';
import '../tokens.css';
import '../prototype.css';
import '../app.css';
import '../native.css';
import '../styles/search.css';
import '../components/settings.css';
import '../components/ui/controls.css';
import './workspace.css';

/** Mount the same desktop workspace with a browser-specific platform. */
export function mountBrowser(target: Element, platform: AppPlatform = createBrowserPlatform()) {
  const restore = setAppPlatform(platform);
  try {
    const app = mount(App, {target, props: {surface: 'browser'}});
    return {app, async destroy() { try { await unmount(app); } finally { restore(); } }};
  } catch (error) {
    restore();
    throw error;
  }
}
