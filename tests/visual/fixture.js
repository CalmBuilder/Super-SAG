(() => {
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname)) {
    throw new Error('The visual-only fixture is restricted to loopback.');
  }
  const params = new URLSearchParams(location.search);
  const scenario = params.get('fixture') || 'normal';
  const longName = '示例项目资料'.repeat(24);
  const hasConversation = scenario.startsWith('conversation');
  const hasSearch = scenario.startsWith('search');
  const hasFiles = scenario.startsWith('files');
  const hasStream = scenario==='stream';
  const extraFiles = scenario==='files-many' ? Array.from({length:120},(_,i)=>({
    id:i+4,path:`/demo/示例知识库/${i}-${'长文件名称'.repeat(20)}.txt`,
    name:`${i}-${'长文件名称'.repeat(20)}.txt`
  })) : [];
  const source = {id:1,document_id:2,path:'/demo/示例知识库/操作手册.txt',title:'操作手册.txt',
    heading:'示例流程',content:'示例流程：整理资料后进行复核。',start_line:1,end_line:1,
    source_ranges:[[1,1]],bm25:1,score:1,order:0,hash:'synthetic-document'};
  const message = {question:'示例项目的流程是什么？',answer:'示例流程先整理资料，再进行复核 [1]。',
    evidence:[source],model:'example-model',scope:[],references:[],status:'complete',error:null,
    retrieval_question:'示例项目的流程是什么？'};
  const conversations = hasConversation ? [{id:'synthetic-conversation',title:'示例流程讨论',updated:1735689600000,
    deleted:false,messages:scenario==='conversation-long'
      ? Array.from({length:40},(_,i)=>({...message,question:`${i+1} `+'A'.repeat(320),
          answer:`第 ${i+1} 条虚构回答。`+'长文本内容'.repeat(80)+' [1]。'}))
      : [message]},...(scenario==='conversation-many'?Array.from({length:120},(_,i)=>({
        id:`synthetic-${i}`,title:`${i}-${'虚构会话标题'.repeat(18)}`,updated:1735689600000,
        deleted:false,messages:[message]
      })):[])] : [];
  const roots = scenario === 'empty' ? [] : scenario === 'long'
    ? Array.from({length:120}, (_, i) => ({path:`/demo/${i}-${longName}`,name:`${i}-${longName}`,status:'ready',count:99999,error:null}))
    : [{path:'/demo/示例知识库',name:'示例知识库',status:'ready',count:hasFiles?3+extraFiles.length:2,error:null}];
  localStorage.setItem('sag.onboarding.seen', '1');
  let callback = 0;
  const callbacks = {};
  const listeners = {};
  let streamRun = null,streamAnswer='',streamHistory=[];
  const emit=(event,payload)=>{
    for(const handler of listeners[event]||[]) callbacks[handler]?.({event,id:handler,payload});
  };
  if(hasStream) window.__VISUAL_STREAM__ = {
    progress(delta) {
      if(!streamRun) throw new Error('No synthetic stream is running');
      streamAnswer+=delta;
      emit('query-progress',{id:streamRun.query.id,stage:'正在生成回答',delta,replace:false,tool:null,reasoning_delta:null,reasoning_block:null});
    },
    tool(finished=false,failed=false) {
      if(!streamRun) throw new Error('No synthetic stream is running');
      const call={id:'synthetic-tool',answer_offset:streamAnswer.length,query:'{"path":"/demo/虚构.txt"}',source_count:0,
        server_name:'虚构工具服务',tool_name:'read',elapsed_ms:finished?7:null,is_error:failed,
        error:failed?'Synthetic tool failed':null,result:finished&&!failed?{text:'虚构工具结果'}:null};
      emit('query-progress',{id:streamRun.query.id,stage:'正在调用',delta:null,tool:{call,finished},reasoning_delta:null,reasoning_block:null});
    },
    approval(length=16) {
      if(!streamRun) throw new Error('No synthetic stream is running');
      emit('tool-approval',{id:'synthetic-approval',query_id:streamRun.query.id,server_name:'虚构工具服务',
        tool_name:'read',arguments:{path:'/demo/虚构.txt',sample:'x'.repeat(length)}});
    },
    finish() {
      if(!streamRun) throw new Error('No synthetic stream is running');
      const current=streamRun,query=current.query;
      const completed={id:query.id,title:query.question,updated:1735689600000,deleted:false,messages:[{
        question:query.question,answer:streamAnswer,evidence:[],model:query.model,scope:[],references:[],
        status:'complete',error:null,retrieval_question:query.question
      }]};
      streamHistory=[completed];streamRun=null;current.resolve({terms:[],results:[],trace:[],conversation:completed});
    },
    fail() {
      if(!streamRun) throw new Error('No synthetic stream is running');
      const current=streamRun;streamRun=null;current.reject(new Error('Synthetic stream unavailable'));
    }
  };
  const settings = {
    theme:params.get('theme') === 'dark' ? 'dark' : 'light', language:params.get('lang') === 'en' ? 'en' : 'zh-CN', start_page:'ask', editor_size:15,
    watch:true, show_hidden:false, excluded:['.git'], index_workers:8, conversion_workers:1,
    answer:{url:'https://example.invalid/v1', model:'example-model', models:['example-model'], auth_mode:'bearer', has_key:true},
    jev:{url:'https://example.invalid/jev', model:'jev-latest', models:[], auth_mode:'bearer', has_key:false},
    retrieval:{candidate_k:50, seed_k:10, expansion_term_limit:20, max_hops:1, top_k:10, chunk_chars:512},
    timeout_secs:120, answer_context_tokens:65536, answer_output_tokens:2048,
    max_tool_calls:0, search_summary_enabled:false, search_summary_sources:10,
    file_types:{markdown:true, text:true, code:false, config:false},
    model_profiles:{}, mcp_servers:[], notes:{folder:null, ask_location:false}
  };
  window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {unregisterListener:(event,id)=>{
    listeners[event]=(listeners[event]||[]).filter(handler=>handler!==id);
  }};
  window.__TAURI_INTERNALS__ = {
    metadata:{currentWindow:{label:'main'}, currentWebview:{label:'main'}},
    transformCallback:fn=>{callbacks[++callback]=fn; return callback},
    unregisterCallback:id=>{delete callbacks[id]},
    convertFileSrc:path=>path,
    invoke:async(cmd,args={})=>{
      if(cmd==='plugin:event|listen') { (listeners[args.event]??=[]).push(args.handler);return args.handler; }
      if(cmd==='plugin:event|unlisten') return null;
      if(cmd==='plugin:window|is_maximized') return false;
      if(cmd==='get_settings') {
        if(scenario==='offline') throw new Error('Synthetic service unavailable');
        return structuredClone(settings);
      }
      if(cmd==='get_index_status') return {paused:false,tasks:[]};
      if(cmd==='get_docling_status') return {installed:false,running:false,stage:'',message:'',downloaded:0,total:null,error:null,formats:[]};
      if(cmd==='list_conversations') return structuredClone(hasStream?streamHistory:conversations);
      if(cmd==='run_query' && hasStream && args.query.kind==='ask') {
        if(streamRun) throw new Error('A synthetic stream is already running');
        streamAnswer='';return new Promise((resolve,reject)=>{streamRun={query:args.query,resolve,reject};});
      }
      if(cmd==='cancel_query' && hasStream) return null;
      if(cmd==='read_document' && (hasConversation||hasSearch||hasFiles) && args.path.startsWith('/demo/示例知识库/')) {
        if(scenario==='conversation-source-missing'||scenario==='search-source-missing'||scenario==='files-source-missing') throw new Error('Synthetic source unavailable');
        const body=hasFiles && args.path.endsWith('.md')?'# 虚构示例文档\n\n这是仅供界面预览的内容。':source.content;
        return {id:2,path:args.path,name:args.path.split('/').at(-1),body,hash:source.hash};
      }
      if(cmd==='run_query' && hasSearch && args.query.kind==='search') {
        const count=args.query.question==='示例流程'?(scenario==='search-many'?45:1):0;
        const page=args.query.page||1,pageSize=20;
        const all=Array.from({length:count},(_,i)=>({...source,id:i+1,document_id:i+1,
          path:count===1?source.path:`/demo/示例知识库/虚构资料${i+1}.txt`,
          title:count===1?source.title:`虚构资料${i+1}.txt`,order:i}));
        return {terms:['示例','流程'],results:all.slice((page-1)*pageSize,page*pageSize),trace:[],
          conversation:null,pagination:{total:count,page,page_size:pageSize},elapsed_ms:7};
      }
      if(cmd==='list_roots') return structuredClone(roots);
      if(cmd==='list_files') return scenario==='empty'?[]:[
        {id:1,path:'/demo/示例知识库/示例文档.md',name:'示例文档.md'},
        {id:2,path:'/demo/示例知识库/操作手册.txt',name:'操作手册.txt'},
        ...(hasFiles?[{id:3,path:'/demo/示例知识库/子目录/子文档.txt',name:'子文档.txt'},...extraFiles]:[])
      ];
      if(cmd==='list_entries' && hasFiles && args.path==='/demo/示例知识库/子目录') return [
        {path:'/demo/示例知识库/子目录/子文档.txt',name:'子文档.txt',directory:false,symlink:false}
      ];
      if(cmd==='list_entries') return scenario==='empty'?[]:[
        ...(hasFiles?[{path:'/demo/示例知识库/子目录',name:'子目录',directory:true,symlink:false}]:[]),
        {path:'/demo/示例知识库/示例文档.md',name:'示例文档.md',directory:false,symlink:false},
        {path:'/demo/示例知识库/操作手册.txt',name:'操作手册.txt',directory:false,symlink:false},
        ...extraFiles.map(({path,name})=>({path,name,directory:false,symlink:false}))
      ];
      if(cmd==='browse_folders') {
        const path=args.path||'/demo';
        const folders={
          '/':[{path:'/demo',name:'demo'}],
          '/demo':[{path:'/demo/项目资料',name:'项目资料'},{path:'/demo/示例文档',name:'示例文档'}],
          '/demo/项目资料':[{path:'/demo/项目资料/子资料',name:'子资料'}],
          '/demo/项目资料/子资料':[],
          '/demo/示例文档':[]
        };
        if(!Object.hasOwn(folders,path)) throw new Error('Synthetic folder unavailable');
        const listed=[...folders[path]];
        if(path==='/demo'&&scenario==='folders-many')listed.push(...Array.from({length:120},(_,i)=>({path:`/demo/文件夹-${i}-${longName}`,name:`文件夹-${i}-${longName}`})));
        if(path==='/demo'&&args.showHidden)listed.push({path:'/demo/.隐藏示例',name:'.隐藏示例'});
        const parent=path==='/'?null:path==='/demo'?'/':path.slice(0,path.lastIndexOf('/'))||'/';
        return {path,parent,home:'/demo',folders:listed};
      }
      if(cmd==='get_quick_search') return {preferences:{enabled:true,shortcut:'CommandOrControl+Shift+Space'},error:null};
      if(cmd==='quick_search_main_ready') return null;
      if(['list_removed_directories','list_notes','list_drafts'].includes(cmd)) return [];
      // Do not make unimplemented native operations appear successful.
      throw new Error('Not available in the visual-only test bridge: '+cmd);
    }
  };
})();
