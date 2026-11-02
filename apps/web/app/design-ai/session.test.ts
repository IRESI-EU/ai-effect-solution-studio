import assert from "node:assert/strict";
import test from "node:test";
import { activeDraftId, conversationForCopy, conversationKey, designReturnUrl, draftUrl, readConversation, readRecommendation, recommendationCreation } from "./session.ts";

test("ordinary navigation never selects remembered work; explicit draft links survive refresh", () => {
  assert.equal(activeDraftId(new URLSearchParams()), null);
  assert.equal(activeDraftId(new URLSearchParams("draftId=")), null);
  const url = new URL(draftUrl("draft/with ?delimiters"), "http://local.test");
  assert.equal(activeDraftId(url.searchParams), "draft/with ?delimiters");
  assert.equal(activeDraftId(new URL(url.href).searchParams), "draft/with ?delimiters");
});

test("a stored qualified recommendation carries its reviewed seed and source without selecting a draft", () => {
  const recommendation = {key:"dutch",label:"Registered Dutch workflow",mechanism:"registered_workflow",source_revision:"a".repeat(64),recommended_seed:43,
    steps:[{title:"Create sample grid",operation:"ConfigureAndSynthesize"},{title:"Benchmark its grid",operation:"RunBenchmark"}],
    connection:"Use the grid produced by the first step",availability:"Only after execution and capture",expected_result_view:["recorded seed"],optional_downloads:["Grid JSON"],limitations:["Registered workflow, not arbitrary composition"]};
  assert.deepEqual(readRecommendation(recommendation),recommendation);
  for (const changed of [{recommended_seed:44},{recommended_seed:"43"},{source_revision:null},{mechanism:"arbitrary_graph"}]) {
    assert.equal(readRecommendation({...recommendation,...changed}),null);
  }
  assert.equal(activeDraftId(new URLSearchParams()),null);
});

test("conversation restoration cannot mix another owner or another draft", () => {
  const record = { ownerId: "designer", draftId: "first", messages: [{role:"user",content:"Explain this draft"}], activity: [], prompt: "Unsent question", seedInput: "42", historyUnavailable: false };
  const raw = JSON.stringify(record);
  assert.deepEqual(readConversation(raw, "designer", "first"), record);
  assert.equal(readConversation(raw, "designer", "second"), null);
  assert.equal(readConversation(raw, "another", "first"), null);
  assert.notEqual(conversationKey("designer", "first"), conversationKey("designer", "second"));
});

test("Builder returns to its saved draft while older solution links retain a safe starting route", () => {
  assert.equal(designReturnUrl({ draft_id: "saved-draft" }), "/design-ai?draftId=saved-draft");
  assert.equal(designReturnUrl(null), "/design-ai");
  assert.equal(designReturnUrl({draft_id:42}), "/design-ai");
});

test("missing or invalid legacy conversation is unavailable, never invented", () => {
  for (const raw of [null, "not JSON", "null", "{}", JSON.stringify({ownerId:"designer",draftId:"first",messages:[{role:"system",content:"wrong"}],activity:[],prompt:"",seedInput:"42",historyUnavailable:false})]) {
    assert.equal(readConversation(raw, "designer", "first"), null);
  }
});

test("discovery stays draft-free and follows only its explicitly created copy", () => {
  const source={ownerId:"designer",draftId:null,messages:[{role:"user" as const,content:"My objective"},{role:"assistant" as const,content:"Offline fixture recommendation"}],activity:[],prompt:"",seedInput:"42",historyUnavailable:false};
  assert.notEqual(conversationKey("designer",null),conversationKey("designer","first"));
  assert.deepEqual(readConversation(JSON.stringify(source),"designer",null),source);
  assert.equal(readConversation(JSON.stringify(source),"designer","first"),null);
  const copy=conversationForCopy("designer","first",source,true);
  assert.deepEqual(copy.messages,source.messages);
  assert.equal(copy.draftId,"first");
  assert.deepEqual(conversationForCopy("designer","second",source,false).messages,[]);
  assert.deepEqual(conversationForCopy("other","second",source,true).messages,[]);
  assert.deepEqual(conversationForCopy("designer","second",copy,true).messages,[]);
});

const catalogueRecommendation = {mechanism:"catalogue_service",candidate_id:`service-${"b".repeat(24)}`,label:"Synthetic demand study",purpose:"Study supplied observations",
  creation_supported:false,runtime_checked:false,input_requirements_known:true,required_inputs:[{name:"observations",purpose:"demand observations"}],
  steps:[],connection:"No established connections",expected_result_view:[],optional_downloads:[],availability:"Unchecked",limitations:["No creation path"]};

test("catalogue capability survives conversation refresh with creation disabled", () => {
  assert.deepEqual(readRecommendation(catalogueRecommendation),catalogueRecommendation);
  const item=readRecommendation(catalogueRecommendation);
  assert.equal(recommendationCreation(item),null);
  const record={ownerId:"designer",draftId:null,messages:[],activity:[],prompt:"",seedInput:"42",historyUnavailable:false,recommendation:catalogueRecommendation};
  assert.deepEqual(readConversation(JSON.stringify(record),"designer",null)?.recommendation,catalogueRecommendation);
});

test("only a validated registered recommendation supplies the generic explicit-create request", () => {
  const item={...catalogueRecommendation,mechanism:"registered_workflow",candidate_id:`workflow-${"a".repeat(24)}`,creation_supported:true,
    recommendation_revision:"c".repeat(64),recommended_seed:43,required_inputs:[{name:"seed"}]};
  assert.deepEqual(recommendationCreation(readRecommendation(item)),{candidate_id:item.candidate_id,recommendation_revision:item.recommendation_revision,recommended_seed:43});
  for(const change of [{creation_supported:false},{runtime_checked:true},{recommendation_revision:"stale"},{recommended_seed:44},{candidate_id:catalogueRecommendation.candidate_id}]) {
    assert.equal(readRecommendation({...item,...change}),null);
  }
});

test("malformed or injected discovery storage cannot enable creation", () => {
  for(const change of [{creation_supported:true},{mechanism:"arbitrary_graph"},{purpose:{instructions:"execute"}},{required_inputs:[{name:42}]},{candidate_id:"invented"}]) {
    assert.equal(readRecommendation({...catalogueRecommendation,...change}),null);
  }
});
