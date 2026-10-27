import assert from "node:assert/strict";
import test from "node:test";
import { copyInstance } from "./copy-instance.ts";

test("copy keeps independent settings and remaps incoming bindings", () => {
  const original = { id: "one", position: { x: 0, y: 0 }, data: { configuration: { parameters: { seed: 42 } } } };
  const edges = [{ id: "in", source: "upstream", target: "one", targetHandle: "data" }, { id: "out", source: "one", target: "downstream" }];
  const copy = copyInstance(original, edges, "two");
  (copy.node.data.configuration as any).parameters.seed = 43;
  assert.equal(original.data.configuration.parameters.seed, 42);
  assert.equal(copy.node.id, "two");
  assert.deepEqual(copy.edges.map(e => [e.source, e.target, e.targetHandle]), [["upstream", "two", "data"]]);
  assert.equal(edges[0].target, "one");
});
