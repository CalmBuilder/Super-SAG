import {mountBrowser} from './mount';

const target = document.getElementById('app');
if (!target) throw new Error('Super-SAG application container is missing');
mountBrowser(target);
