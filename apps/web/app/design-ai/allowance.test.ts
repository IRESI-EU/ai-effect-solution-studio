import assert from "node:assert/strict";
import test from "node:test";
import { allowanceFromError, startingPrompts } from "./allowance.ts";

test("local allowance pauses are explicit; transient failures retain retry behavior", () => {
  const allowance = { can_request: false, blocked_reason: "call_limit", message: "AI testing is paused by the local test allowance." };
  assert.equal(allowanceFromError({ detail: { code: "design_ai_allowance_paused", allowance } }), allowance);
  assert.equal(allowanceFromError({ detail: "The AI provider timed out. Your draft is unchanged." }), null);
  assert.equal(allowanceFromError({ detail: { code: "rate_limit", message: "Provider rate limited" } }), null);
});

test("starting prompts target only enabled templates", () => {
  const prompts = startingPrompts([
    { key: "denmark", label: "Danish SysLAB", available: false },
    { key: "dutch", label: "Dutch Node", available: true },
    { key: "germany", label: "Germany", available: false },
  ]);
  assert.deepEqual(prompts, ["Find a Dutch grid synthesis and benchmark workflow"]);
  assert.deepEqual(startingPrompts([]), []);
});
