import assert from "node:assert/strict";
import test from "node:test";
import {designStage,nodeReview,supportedExamples,nextWorkspaceArea} from "./workspace-view.ts";

test("empty, pending, applied and saved describe design state without readiness claims",()=>{
  assert.equal(designStage(null),"Empty");
  assert.equal(designStage({pending:{},dirty:true,saved_solution_id:null}),"Proposed");
  assert.equal(designStage({pending:null,dirty:true,saved_solution_id:"saved-copy"}),"Applied · unsaved");
  assert.equal(designStage({pending:null,dirty:false,saved_solution_id:"saved-copy"}),"Saved");
});
test("step inspection uses declared purpose and configured values without mutating engineering state",()=>{
  const node={id:"instance",data:{label:"Generator",service:{name:"Registry name",description:"Declared test purpose"},configuration:{parameters:{count:3}},operation_contract:{contract_id:"pin",contract_version:"1"}}};
  const before=JSON.stringify(node);const review=nodeReview(node);
  assert.deepEqual(review,{title:"Generator",purpose:"Declared test purpose",settings:{count:3}});
  assert.equal(JSON.stringify(node),before);
  assert.equal(nodeReview({id:"other",data:{}}).purpose,"No purpose declared in the catalogue.");
});
test("prompt suggestions respect the active scope and disappear for disconnected fixtures",()=>{
  for(const scope of [undefined,"catalogue_pair","append_bound_operation","instance_settings"])assert.deepEqual(supportedExamples(scope,false,false),[]);
  assert.deepEqual(supportedExamples("catalogue_pair",true,false),["Explain the proposed steps, settings and connection"]);
  for(const value of supportedExamples(undefined,true,false))assert.ok(!/seed|Dutch|benchmark|execute|GitHub/i.test(value));
});
test("narrow workspace navigation supports arrow, Home and End keys without changing drafts",()=>{
  assert.equal(nextWorkspaceArea("library","ArrowLeft"),"assistant");
  assert.equal(nextWorkspaceArea("assistant","ArrowRight"),"library");
  assert.equal(nextWorkspaceArea("canvas","Home"),"library");
  assert.equal(nextWorkspaceArea("canvas","End"),"assistant");
  assert.equal(nextWorkspaceArea("canvas","Tab"),"canvas");
});
