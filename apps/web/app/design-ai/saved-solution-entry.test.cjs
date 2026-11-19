// Actual fresh-goal entry component at offline boundaries; no model request.
const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {createRequire}=require('node:module'),React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),swc=require('next/dist/build/swc');
function render(goal){
 const file=path.join(__dirname,'saved-solution-entry.tsx'),code=swc.transformSync(fs.readFileSync(file,'utf8'),{filename:file,jsc:{parser:{syntax:'typescript',tsx:true},target:'es2022',transform:{react:{runtime:'automatic'}}},module:{type:'commonjs'}}).code;
 const module={exports:{}},native=createRequire(file),runtime=require('react/jsx-runtime');let index=0,form,button;
 const states=['normal',[],'',false,goal];const wrap=fn=>(type,props,...rest)=>{if(type==='form')form=props;if(type==='button')button=props;return fn(type,props,...rest);};
 const imports={react:{...React,useState:()=>[states[index++],()=>{}],useEffect:()=>{},useRef:v=>({current:v})},'react/jsx-runtime':{...runtime,jsx:wrap(runtime.jsx),jsxs:wrap(runtime.jsxs)},'next/link':{__esModule:true,default:()=>null},'../../components/auth-context':{useAuth:()=>({user:{id:'fixture'}})},'../../lib/solution-design':{apiErrorMessage:()=> 'fixture error'}};
 vm.runInThisContext(`(function(require,module,exports){${code}\n})`,{filename:file})(name=>imports[name]||native(name),module,module.exports);
 const html=renderToStaticMarkup(React.createElement(module.exports.default,{legacy:null}));return {html,form,button};
}
test('fresh goal creates one canonical saved solution without a chat or Run request',async()=>{
 const {html,form}=render('Compare heating layouts');assert.match(html,/What would you like to build/);
 const oldFetch=global.fetch,oldWindow=global.window,calls=[],routes=[];
 global.fetch=async(url,options)=>{calls.push([url,JSON.parse(options.body)]);return {ok:true,json:async()=>({id:'same-solution'})};};
 global.window={location:{assign:url=>routes.push(url)}};
 try{await form.onSubmit({preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(calls.length,1);assert.equal(calls[0][0],'/api/solutions');assert.equal(calls[0][1].design_metadata.assistant_goal,'Compare heating layouts');
 assert.deepEqual(calls[0][1].nodes,[]);assert.deepEqual(routes,['/builder?solutionId=same-solution']);
 }finally{global.fetch=oldFetch;global.window=oldWindow;}
});
test('an empty goal cannot start a solution',()=>{assert.equal(render(' ').button.disabled,true);});
