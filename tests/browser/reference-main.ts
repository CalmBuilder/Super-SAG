// Read-only comparison: load the pinned desktop reference without building in pros/.
import {mount} from 'svelte';
import App from '@visual-reference/src/App.svelte';
import '@visual-reference/src/tokens.css';
import '@visual-reference/src/prototype.css';
import '@visual-reference/src/app.css';
import '@visual-reference/src/native.css';
import '@visual-reference/src/styles/search.css';
import '@visual-reference/src/components/settings.css';
import '@visual-reference/src/components/ui/controls.css';
mount(App,{target:document.getElementById('app')!});
