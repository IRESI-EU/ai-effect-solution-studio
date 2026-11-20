// Exercise the actual component at explicit offline API boundaries. No browser
// acceptance or real model response is implied by rendered component tests.
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createRequire} = require('node:module');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const swc = require('next/dist/build/swc');
function load(file, imports = {}) {
  const code = swc.transformSync(fs.readFileSync(file, 'utf8'), {filename:file,jsc:{parser:{syntax:'typescript',tsx:true},target:'es2022',transform:{react:{runtime:'automatic'}}},module:{type:'commonjs'}}).code;
  const module={exports:{}}, native=createRequire(file);
  vm.runInThisContext(`(function(require,module,exports){${code}\n})`,{filename:file})(name=>Object.hasOwn(imports,name)?imports[name]:native(name),module,module.exports);
  return module.exports;
}
const message = load(path.join(__dirname,'conversation-message.tsx'));
const state={solution_id:'same-id',expected_updated_at:'version-1',conversation_revision:2,can_undo:true,
  messages:[{role:'assistant',content:'Review **three** topologies. <script>bad</script>'}],
  pending:{id:'proposal-1',base_updated_at:'version-1',changes:[{action:'set_node_parameters',step:'Generate',before:{count:1},after:{count:3}}]}};
function render({disabled=false,version='version-1',provider=true,workspace=true,pending=state}={}) {
  let index=0; const values=[{enabled:true,saved_solution_workspace:workspace,provider_configured:provider},pending,'Use three',false,''];
  const buttons=[], forms=[], mutations=[]; const runtime=require('react/jsx-runtime');
  const wrap=fn=>(type,props,...rest)=>{if(type==='button')buttons.push(props); if(type==='form')forms.push(props);return fn(type,props,...rest);};
  const Component=load(path.join(__dirname,'saved-solution-assistant.tsx'),{
    react:{...React,useState:()=>[values[index++],()=>{}],useEffect:()=>{},useRef:value=>({current:value})},
    'react/jsx-runtime':{...runtime,jsx:wrap(runtime.jsx),jsxs:wrap(runtime.jsxs)},
    './conversation-message':message,'../lib/solution-design':{apiErrorMessage:()=> 'Expected offline failure'},
  }).default;
  return {html:renderToStaticMarkup(React.createElement(Component,{solutionId:'same-id',savedVersion:version,disabled,onMutating:value=>mutations.push(value)})),buttons,forms,mutations};
}
test('review is concrete, escaped and separate from execution',()=>{
  const {html,buttons}=render();
  assert.match(html,/Apply and save reviewed changes/);assert.match(html,/&quot;count&quot;: 3/);assert.match(html,/&lt;script&gt;/);
  assert.ok(!buttons.some(b=>/Run|deploy/i.test(String(b.children))));
});
test('unsaved Builder work, stale versions and retained profiles block apply',()=>{
  for(const options of [{disabled:true},{version:'different'},{pending:{...state,pending:{...state.pending,base_updated_at:'older'}}}]) {
    const {buttons}=render(options);assert.equal(buttons.find(b=>b.children==='Apply and save reviewed changes').disabled,true);
  }
  assert.equal(render({workspace:false}).html,'');
  const disconnected=render({provider:false});assert.match(disconnected.html,/AI is not connected/);
  assert.equal(disconnected.buttons.find(b=>b.children==='Send message').disabled,true);
});
test('Apply targets the same canonical saved solution and reloads Builder; no execution request',async()=>{
  const {buttons,mutations}=render();const previousFetch=global.fetch, previousWindow=global.window;
  const calls=[],navigations=[];
  global.fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>({...state,expected_updated_at:'version-2',pending:null})};};
  global.window={location:{assign:url=>navigations.push(url)}};
  try {
    await buttons.find(b=>b.children==='Apply and save reviewed changes').onClick();
    assert.equal(calls.length,1);assert.equal(calls[0][0],'/api/design-ai/solutions/same-id/apply');
    assert.deepEqual(JSON.parse(calls[0][1].body),{expected_updated_at:'version-1',conversation_revision:2,proposal_id:'proposal-1'});
    assert.deepEqual(navigations,['/builder?solutionId=same-id']);assert.deepEqual(mutations,[true]);
  } finally {global.fetch=previousFetch;global.window=previousWindow;}
});
test('sending text only requests a proposal and never navigates or submits Run',async()=>{
  const {forms}=render();const previousFetch=global.fetch;const calls=[];
  global.fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>state};};
  try {await forms[0].onSubmit({preventDefault(){}});assert.equal(calls.length,1);assert.equal(calls[0][0],'/api/design-ai/solutions/same-id/chat');assert.equal(JSON.parse(calls[0][1].body).message,'Use three');}
  finally {global.fetch=previousFetch;}
});


test('complete cumulative review shows final settings and separate revision delta',()=>{
  const pending={...state,pending:{...state.pending,current:true,supersedes:'previous',candidate:{name:'Reviewed design',steps:[
    {node_id:'source-abcdefgh',target_ref:'source-ref',label:'Generator',service_id:'fixture-source',effective_settings:{count:3,enabled:true},requested_overrides:{count:3},setting_labels:{count:'Candidate maximum',enabled:'Enabled'},contract:{contract_version:'1.0.0'}},
    {node_id:'view-12345678',target_ref:'view-ref',label:'Alternative drawing',service_id:'fixture-view',effective_settings:{},requested_overrides:{},setting_labels:{},contract:{contract_version:'1.0.0'}}],
    connections:[{source:'source-ref',target:'view-ref',binding:{source_slot:'networks',target_slot:'networks'}}],assumptions:['View was proposed, not a catalogue default.'],workflow_input_selected:false}}};
  const {html}=render({pending});
  for(const text of ['Complete proposed design','Candidate maximum','3 (proposed override)','true (published default)','Alternative drawing','Changes since previous review','earlier proposal is superseded','No input is selected'])assert.ok(html.includes(text),text);
  assert.equal(render({pending:{...pending,pending:{...pending.pending,current:false,candidate:null}}}).buttons.find(b=>b.children==='Apply and save reviewed changes').disabled,true);
});


test('application diff is displayed as factual plain text, with applied notice only from server state',()=>{
  const fixture={...state,application_notice:'The reviewed changes were applied and saved. Run remains a separate action.',messages:[{role:'assistant',content:'Proposed setting changes: maximum 4 → 2. <script>bad</script>',change_summary:{source:'application_diff'}}]};
  const {html}=render({pending:fixture});
  assert.match(html,/Application change summary/);assert.match(html,/4 → 2/);assert.match(html,/&lt;script&gt;/);
  assert.match(html,/reviewed changes were applied and saved/);
});
