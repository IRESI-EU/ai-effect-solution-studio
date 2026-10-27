import assert from "node:assert/strict";
import test from "node:test";
import { artifactMessage, referenceMessage } from "./results.ts";

test("missing API fields differ from explicitly empty references and pending/failed tasks", () => {
  assert.equal(referenceMessage(undefined, "completed"), "References unavailable through this API.");
  assert.equal(referenceMessage([], "completed"), "No artifact recorded.");
  assert.equal(referenceMessage([], "running"), "Results pending.");
  assert.equal(referenceMessage([], "failed"), "Execution failed; no artifact recorded.");
  assert.equal(referenceMessage([{}], "completed"), "");
});

test("an inaccessible recorded artifact is distinct from no recorded artifact", () => {
  assert.equal(artifactMessage("inaccessible"), "Artifact recorded but currently inaccessible.");
  assert.equal(artifactMessage("not_recorded"), "No artifact recorded.");
  assert.equal(artifactMessage("pending"), "Results pending.");
});
