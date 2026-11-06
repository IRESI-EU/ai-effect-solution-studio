import assert from "node:assert/strict";
import test from "node:test";
import {readRecommendation,recommendationCreation,readConversation} from "./session.ts";
import {catalogueDesignOnly,nextReviewAction} from "../../lib/builder-review.ts";

const review={steps:[{title:"Synthetic generator",purpose:"Generate test observations",settings:{count:3}},
  {title:"Synthetic analyzer",purpose:"Analyze those observations",settings:{}}],
  connection:"Pass the complete observations reference",binding:{source_slot:"observations",target_slot:"observations",transport:"whole-output-v1",schema_fingerprint:"a".repeat(64)},
  unresolved_requirements:[],runtime_checked:false,execution_supported:false};
const rec={mechanism:"catalogue_composed",candidate_id:`pair-${"b".repeat(24)}`,label:"Synthetic composed design",purpose:"Design only",
  creation_supported:true,execution_supported:false,runtime_checked:false,recommendation_revision:"c".repeat(64),creation_request_id:"12345678-1234-4234-8234-123456789abc",
  composition_review:review,composition_settings:{first:[{name:"count",value:3}],second:[]},required_inputs:[],
  steps:[{title:"Synthetic generator",operation:"Fixture0"},{title:"Synthetic analyzer",operation:"Fixture1"}],connection:"One complete reference",
  expected_result_view:[],optional_downloads:[],availability:"Runtime and execution unverified",limitations:["Design only"]};

test("composed creation retains its nonce and selected values without template or graph JSON",()=>{
  const item=readRecommendation(rec);assert.ok(item);
  const request=recommendationCreation(item)!;
  assert.deepEqual(Object.keys(request).sort(),["candidate_id","composition_settings","creation_request_id","recommendation_revision"]);
  assert.deepEqual(recommendationCreation(item),request);
  assert.deepEqual(request.composition_settings,rec.composition_settings);
  const conversation={ownerId:"designer",draftId:null,messages:[],activity:[],prompt:"",seedInput:"42",historyUnavailable:false,recommendation:rec};
  const restored=readConversation(JSON.stringify(conversation),"designer",null);
  assert.deepEqual(recommendationCreation(restored!.recommendation!),request);
});

test("incomplete, ambiguous or executable composed recommendations cannot enable Create",()=>{
  for(const change of [{creation_request_id:undefined},{recommendation_revision:"old"},{runtime_checked:true},{execution_supported:true},
    {composition_review:{...review,steps:[...review.steps,review.steps[0]]}},
    {composition_review:{...review,unresolved_requirements:["count"]}},
    {composition_settings:{first:[{name:"count",value:{code:"execute"}}],second:[]}},
    {composition_settings:{first:[{name:"count",value:3},{name:"count",value:4}],second:[]}},
    {composition_settings:{first:[],second:[],nodes:[]}}]) {
    assert.equal(readRecommendation({...rec,...change}),null);
  }
});

test("composed provenance keeps Builder in review even when runtime flags say ready",()=>{
  assert.equal(catalogueDesignOnly({source:{kind:"catalogue_composed"}}),true);
  assert.equal(catalogueDesignOnly({execution_policy:"design_only_catalogue_pair"}),true);
  assert.equal(catalogueDesignOnly({guided_experiment:"qualified_dutch_grid"}),false);
  assert.equal(catalogueDesignOnly(null),false);
  assert.equal(nextReviewAction({steps:2,dirty:false,design:"valid",offline:catalogueDesignOnly({source:{kind:"catalogue_composed"}}),readiness:"ready",confirmationReady:true,submitted:false}),"review");
});
