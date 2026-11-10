// Test-only entry: the fixture is supplied by index.html, never by the workspace.
import { mount } from 'svelte';
import App from '../../src/App.svelte';
import '../../src/tokens.css';
import '../../src/prototype.css';
import '../../src/app.css';
import '../../src/native.css';
import '../../src/styles/search.css';
import '../../src/components/settings.css';
import '../../src/components/ui/controls.css';
import '../../src/web/visual-shell.css';

mount(App,{target:document.getElementById('app')!,props:{surface:'web'}});
