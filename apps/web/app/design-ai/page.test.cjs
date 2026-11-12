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
for (const [name, config, expected, args] of [
  ['disconnected',{provider_mode:'openai',provider_configured:false},'AI disconnected · existing controls available',[false,false,false]],
  ['allowance paused',{provider_mode:'openai',provider_configured:true,test_allowance:{can_request:false,message:'Allowance exhausted'}},'AI messages paused · existing controls available',[false,false,true]],
  ['synthetic',{provider_mode:'test',provider_configured:false},'Prepared walkthrough · chat unavailable',[true,false,false]],
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
    if (name !== 'synthetic') assert.ok(!html.includes('Prepared walkthrough'));
  } finally { global.fetch = originalFetch; }
});
