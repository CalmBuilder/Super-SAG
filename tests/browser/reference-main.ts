// Read-only comparison: load the pinned desktop reference without building in pros/.
import {mount} from 'svelte';
import App from '../../pros/SAG-Wiki/src/App.svelte';
import '../../pros/SAG-Wiki/src/tokens.css';
import '../../pros/SAG-Wiki/src/prototype.css';
import '../../pros/SAG-Wiki/src/app.css';
import '../../pros/SAG-Wiki/src/native.css';
import '../../pros/SAG-Wiki/src/styles/search.css';
import '../../pros/SAG-Wiki/src/components/settings.css';
import '../../pros/SAG-Wiki/src/components/ui/controls.css';
mount(App,{target:document.getElementById('app')!});
