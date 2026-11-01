import assert from "node:assert/strict";
import test from "node:test";
import { activeDraftId, conversationForCopy, conversationKey, designReturnUrl, draftUrl, readConversation, readRecommendation } from "./session.ts";

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
