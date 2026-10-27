import assert from "node:assert/strict";
import test from "node:test";
import { activeDraftId, conversationForCopy, conversationKey, designReturnUrl, draftUrl, readConversation } from "./session.ts";

test("ordinary navigation never selects remembered work; explicit draft links survive refresh", () => {
  assert.equal(activeDraftId(new URLSearchParams()), null);
  assert.equal(activeDraftId(new URLSearchParams("draftId=")), null);
  const url = new URL(draftUrl("draft/with ?delimiters"), "http://local.test");
  assert.equal(activeDraftId(url.searchParams), "draft/with ?delimiters");
  assert.equal(activeDraftId(new URL(url.href).searchParams), "draft/with ?delimiters");
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
