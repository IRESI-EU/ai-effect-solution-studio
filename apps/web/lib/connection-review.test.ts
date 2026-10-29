import assert from "node:assert/strict";
import test from "node:test";
import { bindingSignature, connectionState, connectionSummary, dataLabel, savedBindingSignatures, stepLabel, stepPurpose, type Contract } from "./connection-review.ts";

const source: Contract = {id:"producer-contract",contract_version:"1.0.0",definition:{binding_transport:"whole-output-v1",inputs:[],outputs:[{name:"captured_grid",schema_ref:"urn:test:grid"}]}};
const target: Contract = {id:"consumer-contract",contract_version:"1.0.0",definition:{binding_transport:"whole-output-v1",inputs:[{name:"captured_grid",schema_ref:"urn:test:grid"}],outputs:[]}};
const sourcePin = {contract_id:source.id,contract_version:source.contract_version};
const targetPin = {contract_id:target.id,contract_version:target.contract_version};
const nodes = [{id:"producer",position:{x:30,y:0},data:{label:"Generate synthetic power grid",service:{id:"producer-service",name:"Producer"},operation_contract:sourcePin,configuration:{parameters:{seed:42}}}},
  {id:"consumer",position:{x:300,y:180},data:{label:"Benchmark generated grid",service:{id:"consumer-service",name:"Consumer"},operation_contract:targetPin}}];
const binding = {source_slot:"captured_grid",target_slot:"captured_grid"};
const edge = {id:"connection",source:"producer",target:"consumer",data:{binding}};
const signature = bindingSignature(nodes,edge);
const input = {binding,sourcePin,targetPin,source,target,loaded:true,signature};

test("summary follows actual endpoints and metadata, including other operations and unknown metadata", () => {
  assert.equal(connectionSummary(stepLabel(nodes[0]),stepLabel(nodes[1]),binding),"Benchmark generated grid uses the grid from Generate synthetic power grid.");
  assert.equal(connectionSummary("Topology generator","Drawing renderer",{source_slot:"topology_options",target_slot:"networks"}),"Drawing renderer uses the topology options from Topology generator.");
  assert.equal(stepLabel({id:"unknown",data:{}}),"Unknown step");
  assert.equal(dataLabel("urn:unknown"),"data");
  assert.equal(connectionSummary("Unknown step","Consumer",{source_slot:"urn:unknown",target_slot:"data"}),"Consumer uses data from Unknown step.");
  assert.match(connectionSummary("Producer","Consumer"),/Choose its data connection/);
});

test("configured, persisted and checked states remain independent", () => {
  assert.deepEqual(connectionState({...input,binding:undefined}),{configured:false,persistence:"No binding selected",check:"Compatibility not checked",attention:false});
  assert.equal(connectionState(input).persistence,"Binding configured · not saved");
  assert.equal(connectionState(input).check,"Compatibility not checked");
  assert.equal(connectionState({...input,savedSignature:signature}).check,"Compatibility not checked");
  assert.equal(connectionState({...input,checkedSignature:signature}).persistence,"Binding configured · not saved");
  assert.equal(connectionState({...input,checkedSignature:signature}).check,"Compatibility checked successfully");
  assert.equal(connectionState({...input,checkedSignature:"old graph"}).check,"Compatibility not checked");
});

test("unknown definitions, changed pins and wrong slots require attention without rebinding", () => {
  const before = structuredClone({nodes,edge,source,target});
  for (const changed of [{source:undefined},{sourcePin:{...sourcePin,contract_version:"2.0.0"}},
    {binding:{...binding,target_slot:"missing"}},{target:{...target,id:"replacement"}}]) {
    assert.equal(connectionState({...input,...changed,checkedSignature:signature}).check,"Connection requires attention");
  }
  assert.equal(connectionState({...input,loaded:false,source:undefined,target:undefined}).check,"Compatibility not checked");
  assert.deepEqual({nodes,edge,source,target},before);
});

test("selection, measurement and viewport presentation leave binding persistence/checks intact", () => {
  const before=structuredClone({nodes,edge});
  const displayed=nodes.map(n=>({...n,selected:true,measured:{width:220,height:70},dragging:false}));
  assert.equal(bindingSignature(displayed,edge),signature);
  assert.deepEqual(savedBindingSignatures(displayed,[edge]),{connection:signature});
  assert.equal(connectionState({...input,savedSignature:signature,checkedSignature:bindingSignature(displayed,edge)}).check,"Compatibility checked successfully");
  assert.deepEqual({nodes,edge},before);
});

test("real endpoint, pin and slot edits invalidate their exact checked/saved identity; property order does not", () => {
  const changed={...edge,data:{binding:{...binding,target_slot:"different"}}};
  assert.notEqual(bindingSignature(nodes,changed),signature);
  assert.notEqual(bindingSignature(nodes.map(n=>n.id==="producer"?{...n,data:{...n.data,operation_contract:{...sourcePin,contract_version:"2.0.0"}}}:n),edge),signature);
  assert.notEqual(bindingSignature(nodes,{...edge,target:"other"}),signature);
  assert.equal(bindingSignature(nodes,{...edge,data:{binding:{target_slot:"captured_grid",source_slot:"captured_grid"}}}),signature);
});


test("step purpose uses catalogue input/output metadata and honest missing-metadata fallback", () => {
  assert.equal(stepPurpose({input_type:"None",output_type:"Captured Dutch grid"}),"Produces Captured Dutch grid.");
  assert.equal(stepPurpose({input_type:"Image",output_type:"Score"}),"Uses Image to produce Score.");
  assert.equal(stepPurpose({input_type:"Unknown",description:"Inspect a supplied network."}),"Inspect a supplied network.");
  assert.match(stepPurpose({}),/technical details/);
});
