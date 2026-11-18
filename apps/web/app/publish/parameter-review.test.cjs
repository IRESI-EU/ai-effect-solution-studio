// Actual provider form, explicit offline API boundaries. Not browser acceptance.
const assert=require('node:assert/strict');
const test=require('node:test');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {createRequire}=require('node:module');
const React=require('react');
const {renderToStaticMarkup}=require('react-dom/server');
const swc=require('next/dist/build/swc');
function load(file,imports={}) {
  const code=swc.transformSync(fs.readFileSync(file,'utf8'),{filename:file,jsc:{parser:{syntax:'typescript',tsx:file.endsWith('.tsx')},target:'es2022',transform:{react:{runtime:'automatic'}}},module:{type:'commonjs'}}).code;
  const module={exports:{}},native=createRequire(file);
  vm.runInThisContext(`(function(require,module,exports){${code}\n})`,{filename:file})(name=>Object.hasOwn(imports,name)?imports[name]:native(name),module,module.exports);
  return module.exports;
}
const helper=load(path.join(__dirname,'../../lib/parameter-discovery.ts'));
const source=JSON.parse(fs.readFileSync(path.join(__dirname,'../../../../docs/parameter-onboarding/portugal-source-openapi.json'),'utf8'));
function render({operationId='',draft=false}={}) {
  const state={operation_name:'TrainModel',service_status:'pending_review',interface_type:draft?'grpc':'control',reviews:{},discovery:draft?{revision:'source-review',source_reference:'source@commit',source_sha256:'source-hash',candidates:[]}:null};
  const row={name:'epochs',source_pointer:'#/paths/~1train/post/parameters/6/schema',source_location:'query',selected:true,supported:true,classification:'setting',
    definition:{type:'integer',title:'Epochs',description:'Number of epochs for training',default:10},defaultText:'10',minimumText:'',maximumText:'',enumText:'',mapping:'configuration.parameters.epochs -> query.epochs'};
  const values=[state,[],draft?[row]:[],draft?'':JSON.stringify(source),'source@commit',operationId,'urn:test:training','1.0.0',false,'',''];
  let index=0;const buttons=[],runtime=require('react/jsx-runtime');
  const wrap=fn=>(type,props,...rest)=>{if(type==='button')buttons.push(props);return fn(type,props,...rest);};
  const {ParameterReview}=load(path.join(__dirname,'parameter-review.tsx'),{
    react:{...React,useState:()=>[values[index++],()=>{}],useEffect:()=>{}},'react/jsx-runtime':{...runtime,jsx:wrap(runtime.jsx),jsxs:wrap(runtime.jsxs)},'../../lib/parameter-discovery':helper,
  });
  return {state,buttons,html:renderToStaticMarkup(React.createElement(ParameterReview,{serviceId:'any-node-service'}))};
}
test('provider explicitly selects an actual source operation instead of guessing the runtime method',async()=>{
  const start=render();assert.match(start.html,/POST \/train/);assert.match(start.html,/GET \/generate/);
  assert.equal(start.buttons.find(b=>b.children==='Discover candidate settings').disabled,true);
  const id=source.paths['/train'].post.operationId;
  const ready=render({operationId:id});const button=ready.buttons.find(b=>b.children==='Discover candidate settings');assert.equal(button.disabled,false);
  const before=global.fetch,calls=[];global.fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>({revision:'new',candidates:[]})};};
  try {await button.onClick();assert.equal(calls.length,1);const body=JSON.parse(calls[0][1].body);assert.equal(body.operation_id,id);assert.deepEqual(body.document,source);}
  finally {global.fetch=before;}
});
test('an unqualified interface can save reviewed definitions without fabricated runtime confirmation',async()=>{
  const view=render({draft:true});const button=view.buttons.find(b=>b.children==='Save reviewed settings as draft');
  assert.equal(button.disabled,false);assert.match(view.html,/Publication requires a declared and qualified HTTP Control/);
  const before=global.fetch,calls=[];global.fetch=async(url,options)=>{calls.push([url,options]);return {ok:true,json:async()=>options?{id:'draft'}:url.endsWith('operation-contracts')?[]:view.state};};
  try {await button.onClick();const [url,options]=calls[0];assert.match(url,/any-node-service\/parameter-onboarding\/review$/);const body=JSON.parse(options.body);
    assert.equal(body.runtime_support_confirmed,false);assert.equal(body.normal_configuration_tested,false);assert.equal(body.invalid_configuration_tested,false);assert.equal(body.evidence_reference,'');
    assert.equal(body.parameters[0].definition.default,10);assert.ok(!calls.some(([path])=>/activate|execute|submit/.test(path)));
  } finally {global.fetch=before;}
});
