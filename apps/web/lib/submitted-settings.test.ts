import { strict as assert } from "node:assert";
import test from "node:test";
import { submittedEvidenceStatus, submittedSettings } from "./submitted-settings.ts";

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

test("evidence must match the immutable workflow, submission and task", () => {
  const node = { instance_id: "grid", task_id: "task_1", node_key: "synth:run", configuration: { parameters: { seed: 43 } } };
  const snapshot = { id: "submission-1", workflow_id: "wf-1" };
  const item = { instance_id: "grid", task_id: "task_1", node_key: "synth:run", state: "available", algorithm_consumed: { seed: 43 } };
  const evidence = { submission_id: "submission-1", workflow_id: "wf-1", instances: [item] };
  assert.deepEqual(submittedSettings(snapshot, evidence, node).consumed, { seed: 43 });
  for (const changed of [
    { ...evidence, workflow_id: "wf-other" }, { ...evidence, submission_id: "other" },
    { ...evidence, instances: [{ ...item, task_id: "task_other" }] },
    { ...evidence, instances: [{ ...item, node_key: "other:run" }] },
    { ...evidence, instances: [item, item] },
  ]) {
    const value = submittedSettings(snapshot, changed, node);
    assert.equal(value.consumed, null);
    assert.equal(value.proof.state, "conflicting");
  }
});

test("one available instance cannot verify another or infer a benchmark input", () => {
  const node = { instance_id: "benchmark", task_id: "task_b" };
  const evidence = { state: "available", instances: [{ instance_id: "generator", task_id: "task_a", state: "available", algorithm_consumed: { seed: 43 } }] };
  const value = submittedSettings(null, evidence, node);
  assert.equal(value.consumed, null);
  assert.equal(submittedEvidenceStatus(value.proof, evidence, "input").label, "Unavailable");
  assert.equal(submittedEvidenceStatus({ state: "available" }, evidence, "input").label, "Unavailable");
  assert.equal(submittedEvidenceStatus({ state: "available", input_binding_verified: true }, evidence, "input").label, "Verified");
});

test("pending, inaccessible, conflicting and invalid reasons remain distinct", () => {
  for (const [state, label] of [["pending", "Pending"], ["inaccessible", "Inaccessible"], ["conflicting", "Conflicting"], ["invalid", "Invalid"], ["unavailable", "Unavailable"]]) {
    assert.deepEqual(submittedEvidenceStatus({ state, message: "Specific recorded reason" }, null, "parameters"), { label, message: "Specific recorded reason" });
  }
});
