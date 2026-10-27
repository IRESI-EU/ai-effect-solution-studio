import assert from "node:assert/strict";
import test from "node:test";
import { deploymentResultsUrl, executionLabel, isDutchExperiment } from "./experiment-journey.ts";

test("results navigation contains exactly one fragment and the submitted workflow", () => {
  for (const id of ["wf-d642cb742578", "wf-d642cb742578#results", "wf-d642cb742578#results#results"]) {
    assert.equal(deploymentResultsUrl(id), "/deployments/wf-d642cb742578#results");
  }
});

test("execution transition fixtures never imply completed or available results on submission", () => {
  assert.equal(executionLabel("submitted"), "Submitted — waiting to run");
  assert.equal(executionLabel("running"), "Running");
  assert.equal(executionLabel("completed"), "Completed");
  assert.equal(executionLabel("failed"), "Execution failed");
  assert.equal(executionLabel("unreachable"), "Status unavailable");
});

test("plain saved input review is limited to the supported Dutch chain", () => {
  const nodes = ["ConfigureAndSynthesize", "RunBenchmark"].map(operation_name => ({data:{service:{operation_name}}}));
  assert.equal(isDutchExperiment(nodes, {run_input:{seed:43}}), true);
  assert.equal(isDutchExperiment(nodes, {run_input:{dataset:"upload"}}), false);
  assert.equal(isDutchExperiment(nodes.slice(1), {run_input:{seed:42}}), false);
});
