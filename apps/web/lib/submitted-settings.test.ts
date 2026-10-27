import { strict as assert } from "node:assert";
import test from "node:test";
import { submittedSettings } from "./submitted-settings.ts";

test("requested defaults, validated values and algorithm evidence stay distinct", () => {
  const node = { instance_id: "first", configuration: { parameters: { seed: 42 } } };
  const snapshot = { submitted: { request: { nodes: [{ node_id: "first", configuration: { parameters: {} } }] } } };
  const evidence = { instances: [{ instance_id: "first", state: "available", algorithm_consumed: { seed: 42 } }] };
  assert.deepEqual(submittedSettings(snapshot, evidence, node), {
    requested: {}, effective: { seed: 42 }, consumed: { seed: 42 }, proof: evidence.instances[0],
  });
  assert.equal(submittedSettings(snapshot, { instances: [{ instance_id: "other", state: "available" }] }, node).consumed, null);
  assert.deepEqual(submittedSettings(snapshot, null, node).effective, { seed: 42 });
});
