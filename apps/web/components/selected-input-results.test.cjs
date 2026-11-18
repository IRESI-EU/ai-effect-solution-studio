// Render actual components at offline hook boundaries; no browser claim.
const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),swc=require('next/dist/build/swc');
function load(file,imports={}){
 const code=swc.transformSync(fs.readFileSync(file,'utf8'),{filename:file,jsc:{parser:{syntax:'typescript',tsx:true},target:'es2022',transform:{react:{runtime:'automatic'}}},module:{type:'commonjs'}}).code;
 const module={exports:{}},native=createRequire(file);
 vm.runInThisContext(`(function(require,module,exports){${code}\n})`,{filename:file})(name=>Object.hasOwn(imports,name)?imports[name]:native(name),module,module.exports);return module.exports;
}
const selected=load(path.join(__dirname,'../lib/selected-input.ts')),settings=load(path.join(__dirname,'../lib/submitted-settings.ts'));
function picker(value=null){
 let input;const changes=[],errors=[],buttons=[],runtime=require('react/jsx-runtime');
 const wrap=fn=>(type,props,...rest)=>{if(type==='input')input=props;if(type==='button')buttons.push(props);return fn(type,props,...rest);};
 const Component=load(path.join(__dirname,'selected-csv-input.tsx'),{
  react:{...React,useState:()=>['',e=>errors.push(e)],useRef:v=>({current:v})},
  'react/jsx-runtime':{...runtime,jsx:wrap(runtime.jsx),jsxs:wrap(runtime.jsxs)},'../lib/selected-input':selected,
 }).default;
 const html=renderToStaticMarkup(React.createElement(Component,{value,onChange:v=>changes.push(v)}));
 return {html,input,changes,errors,buttons};
}
const file=(name,content)=>({name,size:new TextEncoder().encode(content).length,arrayBuffer:async()=>new TextEncoder().encode(content).buffer});
const event=chosen=>({currentTarget:{files:[chosen]}});
test('CSV picker selects actual text without upload, AI call or execution',async()=>{
 const p=picker();const old=global.fetch;global.fetch=()=>{throw Error('Selection must not dispatch');};
 try{await p.input.onChange(event(file('sample.csv','x,y\n1,2\n')));assert.deepEqual(p.changes,[selected.csvInput('sample.csv','x,y\n1,2\n')]);assert.match(p.html,/Save the solution before running/);assert.equal(p.buttons.length,0);}finally{global.fetch=old;}
});
test('invalid file preserves the saved selection, removal is explicit, names are escaped',async()=>{
 const p=picker(selected.csvInput('<sample>.csv','x\n1\n'));
 assert.match(p.html,/&lt;sample&gt;.csv/);
 await p.input.onChange(event({name:'too-big.csv',size:60001,arrayBuffer:()=>{throw Error('Must not read oversized input');}}));
 assert.equal(p.changes.length,0);assert.match(p.errors.at(-1),/60,000/);
 p.buttons[0].onClick();assert.deepEqual(p.changes,[null]);
});
test('late file reads cannot replace a newer selection',async()=>{
 const p=picker();let release;
 const pending=p.input.onChange(event({name:'old.csv',size:4,arrayBuffer:()=>new Promise(resolve=>{release=resolve;})}));
 await p.input.onChange(event(file('new.csv','x\n2\n')));release(new TextEncoder().encode('x\n1\n').buffer);await pending;
 assert.equal(p.changes.length,1);assert.equal(selected.selectedCsv(p.changes[0]).name,'new.csv');
});
function results({consumed,conflicting=false}={}){
 const node={instance_id:'train',task_id:'task-1',node_key:'service:Train',operation_name:'Train',configuration:{parameters:{batch_size:16}},input_bindings:[]};
 const snapshot={id:'sub-1',workflow_id:'wf-1',submitted:{request:{nodes:[{node_id:'train',configuration:{parameters:{batch_size:16}}}],run_input:selected.csvInput('chosen.csv','x\n1\n')},compiled:{solution_studio_metadata:{execution_instances:[node]}}}};
 const proof={...node,state:'available',evidence_level:'authenticated_runtime_receipt',delivered_parameters:{batch_size:16},algorithm_consumption:'Independent model evidence required',input_references_verified:true,summary:{observed_sequence_count:3,csv_data_rows:12},...(consumed?{algorithm_consumed:consumed}:{})};
 let i=0;const values=[snapshot,{workflow_id:conflicting?'other':'wf-1',submission_id:'sub-1',instances:[proof]},''];
 const Component=load(path.join(__dirname,'submitted-configuration.tsx'),{react:{...React,useEffect:()=>{},useState:()=>[values[i++],()=>{}]},'../lib/selected-input':selected,'../lib/submitted-settings':settings}).default;
 return renderToStaticMarkup(React.createElement(Component,{workflowId:'wf-1',status:'completed',onConfigured:()=>{}}));
}
test('delivery and CSV counts are visible without claiming algorithm consumption',()=>{
 const html=results();assert.match(html,/Selected CSV:/);assert.match(html,/chosen.csv/);assert.match(html,/Delivered to service:/);assert.match(html,/Generated sequences: 3/);assert.match(html,/CSV rows: 12/);assert.match(html,/Algorithm consumed: Unavailable/);assert.ok(!html.includes('Algorithm consumed: Verified'));
});
test('separately verified clamped values remain different from submitted values',()=>{
 const html=results({consumed:{batch_size:8}});assert.match(html,/Validated submitted settings:/);assert.match(html,/Algorithm consumed: Verified/);assert.match(html,/&quot;batch_size&quot;:16/);assert.match(html,/&quot;batch_size&quot;:8/);
 const bad=results({conflicting:true});assert.ok(!bad.includes('Delivered to service:'));assert.ok(!bad.includes('Generated sequences: 3'));
});
