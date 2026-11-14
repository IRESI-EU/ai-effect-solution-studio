import assert from "node:assert/strict";
import test from "node:test";
import { designFingerprint, nextReviewAction, offlineReview, workflowReview, reviewInput, withRunInput, trainingInputMessage } from "./builder-review.ts";

const producer = {id:"p", position:{x:20,y:40}, data:{label:"Stored producer",service:{id:"service-p",name:"Generate sample images"},configuration:{parameters:{seed:42}},operation_contract:{contract_id:"p-pin",contract_version:"1"}}};
const consumer = {id:"c",position:{x:400,y:40},data:{service:{id:"service-c",name:"Score images"}}};
const nodes = [consumer,producer,{id:"output",data:{label:"Output"},position:{x:700,y:40}}];
const edges=[{id:"bound",source:"p",target:"c",data:{binding:{source_slot:"images",target_slot:"images"}}},{id:"end",source:"c",target:"output"}];
const saved=designFingerprint("Example",nodes,edges);
const state={steps:2,dirty:false,design:null as "valid"|"invalid"|null,offline:false,confirmationReady:false,submitted:false};

test("purpose and processing order follow the recorded graph, not catalogue or array order",()=>{
  const before=structuredClone({nodes,edges});
  assert.equal(workflowReview(nodes,edges).purpose,"Generate sample images, then Score images.");
  assert.deepEqual(workflowReview(nodes,edges).steps.map(n=>n.id),["p","c"]);
  assert.equal(workflowReview([producer],[]).purpose,"Generate sample images.");
  assert.deepEqual({nodes,edges},before);
});

test("branches, disconnected nodes, cycles and missing labels do not invent a linear story",()=>{
  assert.equal(workflowReview(nodes,[]).linear,false);
  assert.match(workflowReview(nodes,[]).purpose,/Review their saved connections/);
  assert.equal(workflowReview(nodes,[...edges,{id:"cycle",source:"c",target:"p"}]).linear,false);
  const extra={id:"other",data:{service:{name:"Review images"}},position:{x:20,y:100}};
  assert.equal(workflowReview([...nodes,extra],[...edges,{id:"fork",source:"p",target:"other"}]).linear,false);
  assert.match(workflowReview([{id:"unknown",data:{service:{}},position:{x:0,y:0}}],[]).purpose,/Unnamed processing step/);
});

test("view-only selection, measurement, focus and viewport changes do not create unsaved content",()=>{
  const displayed=nodes.map(n=>({...n,selected:true,measured:{width:220,height:50},width:220,height:50,dragging:false,resizing:false}));
  assert.equal(designFingerprint("Example",displayed,edges.map(e=>({...e,selected:true}))),saved);
  const reordered=edges.map(e=>({...e,data:e.data?{binding:{target_slot:"images",source_slot:"images"}}:undefined}));
  assert.equal(designFingerprint("Example",nodes,reordered),saved);
});

test("actual settings, positions, names and bindings remain unsaved; a pending save records its own snapshot",()=>{
  const editedProducer=structuredClone(producer);editedProducer.data.configuration.parameters.seed=43;
  const edited=nodes.map(n=>n.id===producer.id?editedProducer:n);
  assert.notEqual(designFingerprint("Example",edited,edges),saved);
  assert.notEqual(designFingerprint("Renamed",nodes,edges),saved);
  assert.notEqual(designFingerprint("Example",nodes.map(n=>({...n,position:{x:100,y:0}})),edges),saved);
  assert.notEqual(designFingerprint("Example",nodes,edges.map(e=>({...e,target:"other"}))),saved);
  assert.equal(designFingerprint("Example",nodes,edges),saved);
});

test("next action requires Save, validation, readiness and explicit confirmation independently",()=>{
  assert.equal(nextReviewAction({...state,steps:0}),"add");
  assert.equal(nextReviewAction({...state,dirty:true,design:"valid",readiness:"ready",confirmationReady:true}),"save");
  assert.equal(nextReviewAction(state),"validate");
  assert.equal(nextReviewAction({...state,design:"invalid"}),"validate");
  assert.equal(nextReviewAction({...state,design:"valid"}),"prepare");
  assert.equal(nextReviewAction({...state,design:"valid",readiness:"blocked"}),"prepare");
  assert.equal(nextReviewAction({...state,design:"valid",readiness:"ready"}),"prepare");
  assert.equal(nextReviewAction({...state,design:"valid",readiness:"ready",confirmationReady:true}),"confirm");
  assert.equal(nextReviewAction({...state,design:"valid",submitted:true}),"results");
  for(const readiness of [undefined,"blocked","ready"] as const)
    assert.equal(nextReviewAction({...state,offline:true,design:"valid",readiness,confirmationReady:true}),"review");
});

test("offline restrictions follow explicit profile evidence, never workflow names or saved connections",()=>{
  assert.equal(offlineReview({provider_mode:"test",provider_name:"OFFLINE structural provider-boundary fixtures"}),true);
  assert.equal(offlineReview(null,"OFFLINE AIE-41 usability review — no execution"),true);
  assert.equal(offlineReview({provider_mode:"real",provider_name:"Normal provider"}),false);
  assert.equal(offlineReview({provider_mode:"test",provider_name:"Other fixture"}),false);
  assert.equal(offlineReview(),false);
});


test("saved run input participates in dirty state without treating JSON formatting as an edit",()=>{
  assert.equal(designFingerprint("Example",nodes,edges,{seed:42}),designFingerprint("Example",nodes,edges,reviewInput("json",'{ "seed": 42 }')));
  assert.notEqual(designFingerprint("Example",nodes,edges,{seed:42}),designFingerprint("Example",nodes,edges,reviewInput("json",'{"seed":43}')));
  assert.equal(reviewInput("json",""),null);
  assert.deepEqual(reviewInput("prompt"," make a grid "),{prompt:"make a grid"});
  assert.deepEqual(reviewInput("json","invalid"),{unparsed_input:"invalid",mode:"json"});
});

test("fresh null metadata persists input; Save/reload/copy retains binding, pins and authority",()=>{
  const input={dataset_ref:"sandbox-test"};
  const metadata=withRunInput(null,input);
  assert.deepEqual(metadata,{run_input:input});
  const draft={name:"Manual",nodes,edges,design_metadata:metadata};
  const reloaded=JSON.parse(JSON.stringify(draft));
  assert.equal(designFingerprint(draft.name,nodes,edges,input),designFingerprint(reloaded.name,reloaded.nodes,reloaded.edges,reloaded.design_metadata.run_input));
  assert.deepEqual(reloaded.edges,edges);
  assert.deepEqual(reloaded.nodes,nodes);
  const authority={source:{kind:"catalogue_composed"},execution_policy:"design_only_catalogue_pair",draft_id:"original"};
  assert.deepEqual(withRunInput(authority,input),{...authority,run_input:input});
  assert.deepEqual(authority,{source:{kind:"catalogue_composed"},execution_policy:"design_only_catalogue_pair",draft_id:"original"});
});

test("workflow input changes are dirty for fresh designs and empty forms normalize equally",()=>{
  const empty=designFingerprint("Manual",nodes,edges);
  for (const input of [undefined,null,{},reviewInput("prompt","  "),reviewInput("json","{}")])
    assert.equal(designFingerprint("Manual",nodes,edges,input),empty);
  const selected=reviewInput("json",'{"dataset_ref":"approved"}');
  assert.notEqual(designFingerprint("Manual",nodes,edges,selected),empty);
  assert.equal(nextReviewAction({...state,dirty:true,design:"valid"}),"save");
  assert.equal(nextReviewAction({...state,design:null}),"validate");
  assert.equal(withRunInput(null,{}),null);
  assert.deepEqual(withRunInput({draft_id:"protected"},undefined),{draft_id:"protected",run_input:null});
});

test("missing training input has an actionable instruction instead of only a compiler error",()=>{
  for (const input of [null,{}, {dataset_ref:""},{dataset_ref:"   "}])
    assert.equal(trainingInputMessage(true,input),"Select a training CSV before validating.");
  assert.equal(trainingInputMessage(true,{dataset_ref:"approved"}),"");
  assert.equal(trainingInputMessage(false,null),"");
});
