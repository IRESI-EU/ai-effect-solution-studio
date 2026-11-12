// Render the actual route with settled config state. Effects/network are forbidden.
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createRequire} = require('node:module');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const compilerRequire = createRequire(require.resolve('next/package.json'));
const target = process.platform === 'win32' ? `win32-${process.arch}-msvc` : process.platform === 'darwin' ? `darwin-${process.arch}` : `linux-${process.arch}-gnu`;
compilerRequire.resolve(`@next/swc-${target}`);
const swc = require('next/dist/build/swc');
function load(file, imports = {}) {
  const code = swc.transformSync(fs.readFileSync(file, 'utf8'), {filename:file,
    jsc:{parser:{syntax:'typescript',tsx:file.endsWith('.tsx')},target:'es2022',transform:{react:{runtime:'automatic'}}},module:{type:'commonjs'}}).code;
  const module = {exports:{}}, nativeRequire = createRequire(file);
  vm.runInThisContext(`(function(require,module,exports){${code}\n})`, {filename:file})(
    name => Object.hasOwn(imports,name) ? imports[name] : name.endsWith('.css') ? {} : nativeRequire(name),module,module.exports);
  return module.exports;
}
const view = load(path.join(__dirname,'workspace-view.ts'));
const session = load(path.join(__dirname,'session.ts'));
const allowance = load(path.join(__dirname,'allowance.ts'));
const conversationMessage = load(path.join(__dirname,'../../components/conversation-message.tsx'));
for (const [name, config, expected, args] of [
  ['disconnected',{provider_mode:'openai',provider_configured:false},'AI disconnected · existing controls available',[false,false,false]],
  ['allowance paused',{provider_mode:'openai',provider_configured:true,test_allowance:{can_request:false,message:'Allowance exhausted'}},'AI messages paused · existing controls available',[false,false,true]],
  ['synthetic',{provider_mode:'test',provider_configured:false},'Prepared walkthrough · chat unavailable',[true,false,false]],
  ['local pilot',{provider_mode:'real',provider_configured:false,pilot_notice:'Restricted local design-only pilot'},'AI disconnected · existing controls available',[false,false,false]],
]) test(`actual page renders ${name} through promptPlaceholder without network`, () => {
  let states = 0, calls = [];
  const noop = () => null;
  const Page = load(path.join(__dirname,'page.tsx'), {
    react:{...React,useState: initial => [states++ === 0 ? {enabled:true,...config} : (typeof initial === 'function' ? initial() : initial),noop],useEffect:noop,useMemo:fn=>fn(),useRef:value=>({current:value})},
    'next/navigation':{useSearchParams:()=>new URLSearchParams(),useRouter:()=>({push:()=>assert.fail('navigation during render')})},
    'next/link':{__esModule:true,default:({children,href})=>React.createElement('a',{href},children)},
    '@xyflow/react':{Position:{Top:'top',Bottom:'bottom'},ReactFlow:noop,Background:noop,Controls:noop},
    '../../components/auth-context':{useAuth:()=>({user:{id:'render-only'}})},
    '../../lib/solution-design':{apiErrorMessage:()=>assert.fail('unexpected API error')},
    './session':session,'./allowance':allowance,
    '../../components/conversation-message':conversationMessage,
    './workspace-view':{...view,promptPlaceholder:(...values)=>{calls.push(values);return view.promptPlaceholder(...values);}},
    './workspace-viewport':{__esModule:true,default:noop},'../../components/review-dialog':{__esModule:true,default:noop},
    '../../components/discovery-recommendation':{__esModule:true,default:noop},'../../components/experiment-execution':{__esModule:true,default:noop},
    '../../components/composition-review':{__esModule:true,default:noop},'../../components/structural-review':{__esModule:true,default:noop},'../../components/instance-setting-review':{__esModule:true,default:noop},
  }).default;
  const originalFetch = global.fetch;
  global.fetch = () => assert.fail('render must never make a provider or API request');
  try {
    const html = renderToStaticMarkup(React.createElement(Page));
    assert.deepEqual(calls,[args]);
    assert.equal(html.match(/<textarea[^>]*placeholder="([^"]*)"/)?.[1],expected);
    assert.match(html,/<button[^>]*aria-label="Send request"[^>]*disabled=""/);
    assert.match(html,/>New conversation<\/button>/);
    assert.equal(html.includes('Restricted local design-only pilot'), name === 'local pilot');
    if (name !== 'synthetic') assert.ok(!html.includes('Prepared walkthrough'));
  } finally { global.fetch = originalFetch; }
});

function routeHarness({messages=[],prompt="",clarification=null,params=new URLSearchParams()}={}) {
  let count=0,form,newConversation;
  const state=[];
  const noop=()=>null;
  const runtime=require('react/jsx-runtime');
  function wrap(fn) {return (type,props,...rest)=>{
    if(type==='form' && props.className==='ai-composer')form=props;
    if(type==='button' && props.children==='New conversation')newConversation=props;
    return fn(type,props,...rest);
  };}
  const pushes=[];
  const Page=load(path.join(__dirname,'page.tsx'),{
    react:{...React,useState:initial=>{
      const index=count++;
      const values={0:{enabled:true,provider_configured:true,provider_mode:'real'},9:messages,11:prompt,21:clarification};
      state[index]=Object.hasOwn(values,index)?values[index]:typeof initial==='function'?initial():initial;
      return [state[index],value=>{state[index]=typeof value==='function'?value(state[index]):value;}];
    },useEffect:noop,useMemo:fn=>fn(),useRef:value=>({current:value})},
    'react/jsx-runtime':{...runtime,jsx:wrap(runtime.jsx),jsxs:wrap(runtime.jsxs)},
    'next/navigation':{useSearchParams:()=>params,useRouter:()=>({push:value=>pushes.push(value)})},
    'next/link':{__esModule:true,default:({children,href})=>React.createElement('a',{href},children)},
    '@xyflow/react':{Position:{Top:'top',Bottom:'bottom'},ReactFlow:noop,Background:noop,Controls:noop},
    '../../components/auth-context':{useAuth:()=>({user:{id:'render-only'}})},
    '../../lib/solution-design':{apiErrorMessage:()=>assert.fail('unexpected API error')},
    './session':session,'./allowance':allowance,'./workspace-view':view,
    '../../components/conversation-message':conversationMessage,
    './workspace-viewport':{__esModule:true,default:noop},'../../components/review-dialog':{__esModule:true,default:noop},
    '../../components/discovery-recommendation':{__esModule:true,default:noop},'../../components/experiment-execution':{__esModule:true,default:noop},
    '../../components/composition-review':{__esModule:true,default:noop},'../../components/structural-review':{__esModule:true,default:noop},'../../components/instance-setting-review':{__esModule:true,default:noop},
  }).default;
  return {html:renderToStaticMarkup(React.createElement(Page)),state,pushes,form:()=>form,newConversation:()=>newConversation};
}

test('actual page safely formats explanatory answers without Create or remote content',()=>{
  const text='A **seed** controls randomness, not quality.\n\nWhich sample?\n- **42** is a supported choice\n- `Save` stores the design\n![remote](https://remote.invalid/image.png)\n[unsafe](javascript:alert)\n<script>alert(1)</script>';
  const html=routeHarness({messages:[{role:'assistant',content:text}]}).html;
  assert.match(html,/<strong>seed<\/strong>/);
  assert.match(html,/<code>Save<\/code>/);
  assert.match(html,/<ul>/);
  assert.match(html,/&lt;script&gt;/);
  assert.ok(!html.includes('<img') && !html.includes('<script>') && !html.includes('href="javascript:'));
  assert.ok(!html.includes('href="https://remote.invalid') && !html.includes('Create this experiment'));
  assert.equal(html.match(/Which sample\?/g).length,1);
  assert.ok(!html.includes('**seed**'));
});

test('actual form sends one numeric answer with complete history and pending clarification; no real network',async()=>{
  const messages=[
    {role:'user',content:'I want to understand the existing benchmark'},
    {role:'assistant',content:'It needs the upstream sample. Which seed?'},
    {role:'user',content:'What do those numbers mean?'},
    {role:'assistant',content:'They control generation randomness, not quality.'},
    {role:'user',content:'Does saving run it?'},
    {role:'assistant',content:'No, Save stores a design.'},
    {role:'user',content:'Can I still choose the sample?'},
    {role:'assistant',content:'Yes, your earlier choice is still pending.'},
  ];
  const pending={request:messages[0].content,question:'Which seed?'},calls=[];
  const old=global.fetch;
  global.fetch=async(url,options)=>{calls.push({url,body:options?.body&&JSON.parse(options.body)});return {ok:true,json:async()=>url.endsWith('/chat')?{message:'OFFLINE response',recommendation:null,draft:null,activity:[],clarification:null}:{enabled:true,provider_configured:true}};};
  try {
    const ui=routeHarness({messages,prompt:'42',clarification:pending});
    ui.form().onSubmit({preventDefault(){}});
    await new Promise(resolve=>setImmediate(resolve));
    const chat=calls.filter(v=>v.url.endsWith('/chat'));
    assert.equal(chat.length,1);
    assert.equal(chat[0].body.message,'42');
    assert.deepEqual(chat[0].body.history,messages);
    assert.deepEqual(chat[0].body.clarification,pending);
    assert.equal(ui.state[21],null);
    assert.equal(ui.state[9].filter(m=>m.content==='42').length,1);
  } finally {global.fetch=old;}
});

test('actual form refuses oversized history without truncation, request or clearing the choice',async()=>{
  const old=global.fetch;global.fetch=()=>assert.fail('No request when history exceeds bounds');
  try {
    const ui=routeHarness({messages:Array.from({length:13},()=>({role:'user',content:'Retain this'})),prompt:'42'});
    ui.form().onSubmit({preventDefault(){}});
    await new Promise(resolve=>setImmediate(resolve));
    assert.match(ui.state[13],/no AI request/);
    assert.equal(ui.state[11],'42');
    assert.equal(ui.state[9].length,13);
  } finally {global.fetch=old;}
});
