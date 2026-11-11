/** Isolated visual fixtures; this module is never imported by the product entry. */
import type {EventCallback, EventName, Options, UnlistenFn} from '@tauri-apps/api/event';
import {mountBrowser} from '../../src/bs/mount';
import type {AppPlatform} from '../../src/lib/platform';
import type {Root, Settings} from '../../src/lib/types';

const params = new URLSearchParams(location.search);
const scenario = params.get('scenario') ?? 'normal';
const lang = params.get('lang') === 'en' ? 'en' : 'zh-CN';
let settings: Settings = {
  language: lang, theme: params.get('theme') === 'dark' ? 'dark' : 'light', start_page: 'ask',
  editor_size: 15, show_hidden: false, watch: true, index_workers: 8, excluded: ['.git'],
  answer: {url: '', model: '', models: [], has_key: false},
  jev: {url: '', model: '', models: [], has_key: false},
  retrieval: {candidate_k: 50, seed_k: 10, expansion_term_limit: 20, max_hops: 1, top_k: 10, chunk_chars: 512},
  timeout_secs: 120, answer_context_tokens: 65536, answer_output_tokens: 2048,
  max_tool_calls: 0, file_types: {markdown: true, text: true, code: false, config: false},
  model_profiles: {}, mcp_servers: [],
};
const roots: Root[] = scenario === 'empty' ? [] : scenario === 'many'
  ? Array.from({length: 120}, (_, index) => ({
      path: `/test/folder-${index}`, name: `${index}-${'示例文件夹'.repeat(18)}`,
      status: 'ready', count: index, error: null,
    }))
  : [{path: '/test/library', name: '示例知识库', status: 'ready', count: 1, error: null}];
const calls: string[] = [];
const pageErrors: string[] = [];
window.addEventListener('error', event => pageErrors.push(event.message));
window.addEventListener('unhandledrejection', event => pageErrors.push(String(event.reason)));
let nextId = 0;
const listeners = new Map<string, Map<number, EventCallback<unknown>>>();
const emit = (event: string, payload: unknown) => {
  for (const [id, handler] of listeners.get(event) ?? []) handler({event, id, payload});
};
const platform: AppPlatform = {
  async listen<T>(event: EventName, handler: EventCallback<T>, _options?: Options): Promise<UnlistenFn> {
    const id = ++nextId;
    const registered = listeners.get(event) ?? new Map<number, EventCallback<unknown>>();
    registered.set(id, handler as EventCallback<unknown>);
    listeners.set(event, registered);
    return () => { registered.delete(id); };
  },
  async invoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
    calls.push(command);
    if (scenario === 'offline' && command === 'get_settings') throw new Error('测试服务不可用');
    let result: unknown;
    switch (command) {
      case 'get_settings': result = settings; break;
      case 'save_settings':
        settings = structuredClone(args?.settings as Settings);
        emit('settings-changed', null);
        result = null;
        break;
      case 'list_roots': result = roots; break;
      case 'list_files': result = scenario === 'empty' ? [] : [{id: 1, path: '/test/library/example.md', name: 'example.md'}]; break;
      case 'list_entries': result = []; break;
      case 'get_index_status': result = {paused: false, tasks: []}; break;
      case 'list_removed_directories':
      case 'get_index_history':
      case 'list_conversations':
      case 'list_notes':
      case 'list_drafts': result = []; break;
      case 'get_docling_status': result = {installed: false, running: false, stage: '', message: '', downloaded: 0, total: null, error: null, formats: []}; break;
      default: throw new Error(`测试替身未实现：${command}`);
    }
    return structuredClone(result) as T;
  },
};

// Test server uses an isolated origin and browser profile; this does not touch desktop data.
localStorage.setItem('sag.onboarding.seen', '1');
Object.assign(window, {__BS_TEST__: {calls, scenario, pageErrors}});
const target = document.getElementById('app');
if (!target) throw new Error('Missing visual test container');
mountBrowser(target, platform);
