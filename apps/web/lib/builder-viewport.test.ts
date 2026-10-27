import assert from "node:assert/strict";
import test from "node:test";
import { getNodesBounds } from "@xyflow/react";
import { BuilderViewportSession, initialViewport, layoutFingerprint, readViewport, validViewport, viewportKey, type Viewport } from "./builder-viewport.ts";

const nodes = [30, 300, 580, 900].map((x, i) => ({ id: String(i), position: { x, y: 180 }, measured: { width: 150, height: 40 }, data: { parameters: { how_many: i === 2 ? 4 : 1 } } }));
const input = { ready: true, width: 754, height: 700, bounds: getNodesBounds(nodes), layout: layoutFingerprint(nodes) };
const key = viewportKey("owner", "solution-a")!;
function memory() {
  const entries = new Map<string, string>();
  return { entries, getItem: (k: string) => entries.get(k) ?? null, setItem: (k: string, v: string) => { entries.set(k, v); } };
}

test("first view waits for graph measurements and positive canvas dimensions, then initializes once at readable scale", () => {
  const storage = memory(), session = new BuilderViewportSession(storage, key), applied: Viewport[] = [];
  const apply = (v: Viewport) => { applied.push(v); };
  session.remember({ x: 0, y: 0, zoom: 1 }); // Ignore mount-time moves before ready.
  assert.equal(storage.entries.size, 0);
  assert.equal(session.initialize({ ...input, ready: false }, apply), false);
  assert.equal(session.initialize({ ...input, width: 0 }, apply), false);
  assert.equal(session.initialize({ ...input, height: NaN }, apply), false);
  assert.equal(session.initialize({ ...input, bounds: { ...input.bounds, width: 0 } }, apply), false);
  assert.equal(session.initialize(input, apply), true);
  assert.equal(applied.length, 1);
  assert.equal(applied[0].zoom, 0.9);
  assert.equal(applied[0].x + input.bounds.x * applied[0].zoom, 32);
  assert.equal(session.initialize({ ...input, width: 390 }, apply), false);
  assert.equal(applied.length, 1);
  assert.equal(initialViewport({ x: 0, y: 0, width: 200, height: 80 }, 750, 700).zoom, 1);
});

test("pan/zoom and explicit overview are restored exactly after a new page session", () => {
  const storage = memory(), original = new BuilderViewportSession(storage, key);
  original.initialize(input, () => {});
  const adjusted = { x: -120.5, y: 240, zoom: 1.3 };
  original.remember(adjusted);
  const restored: Viewport[] = [];
  new BuilderViewportSession(storage, key).initialize(input, v => restored.push(v));
  assert.deepEqual(restored, [adjusted]);
  const overview = { x: 20, y: 180, zoom: 0.3 };
  original.remember(overview);
  assert.deepEqual(readViewport(storage, key, input.layout), overview);
});

test("solution/user switches use separate keys; returning restores each view; unsaved work is not persisted", () => {
  const storage = memory();
  const scopes = [["owner", "solution-a"], ["owner", "solution-b"], ["other", "solution-a"]];
  scopes.forEach(([user, solution], i) => {
    const session = new BuilderViewportSession(storage, viewportKey(user, solution));
    session.initialize(input, v => assert.equal(v.zoom, 0.9));
    session.remember({ x: i * 100, y: 20, zoom: 1 + i / 10 });
  });
  scopes.forEach(([user, solution], i) => {
    new BuilderViewportSession(storage, viewportKey(user, solution)).initialize(input, v => assert.equal(v.x, i * 100));
  });
  assert.notEqual(viewportKey("a:b", "c"), viewportKey("a", "b:c"));
  const unsaved = new BuilderViewportSession(storage, viewportKey("owner", null));
  unsaved.initialize(input, () => {}); unsaved.remember({ x: 5, y: 5, zoom: 1 });
  assert.equal(storage.entries.size, 3);
});

test("malformed, obsolete, expired, out-of-bounds and non-finite browser values fall back safely", () => {
  const storage = memory(), now = Date.now(), good = { version: 1, layout: input.layout, savedAt: now, viewport: { x: 20, y: 30, zoom: 1 } };
  const invalid = ["{", "null", "[]", "x".repeat(1025),
    ...[{ ...good, version: 0 }, { ...good, layout: "different-layout" }, { ...good, savedAt: now + 1000 },
      { ...good, savedAt: now - 91 * 86400000 }, { ...good, savedAt: "today" },
      ...[null, {}, { x: "20", y: 30, zoom: 1 }, { x: 1e20, y: 0, zoom: 1 }, { x: 0, y: 0, zoom: 0 },
        { x: 0, y: 0, zoom: 3 }, { x: null, y: 0, zoom: 1 }].map(viewport => ({ ...good, viewport }))].map(v => JSON.stringify(v)),
    '{"version":1,"layout":"' + input.layout + '","savedAt":' + now + ',"viewport":{"x":1e400,"y":0,"zoom":1}}'];
  for (const raw of invalid) {
    storage.setItem(key, raw);
    assert.equal(readViewport(storage, key, input.layout, now), null, raw);
    new BuilderViewportSession(storage, key).initialize(input, v => assert.equal(v.zoom, 0.9));
  }
  for (const value of [NaN, Infinity, -Infinity]) assert.equal(validViewport({ x: value, y: 0, zoom: 1 }), false);
  const blocked = { getItem: () => { throw Error("blocked"); }, setItem: () => { throw Error("full"); } };
  const session = new BuilderViewportSession(blocked, key);
  session.initialize(input, v => assert.equal(v.zoom, 0.9));
  assert.doesNotThrow(() => session.remember({ x: 0, y: 0, zoom: 1 }));
});

test("viewport-only events, selection and resize leave workflow data, dirty/revision and pending protection unchanged", () => {
  const workflow = { nodes: structuredClone(nodes), edges: [{ id: "a-b", source: "0", target: "1" }],
    revision: 3, dirty: false, pending: null, ownership: "owner", contract: "pinned-v1" };
  const before = structuredClone(workflow), storage = memory();
  const session = new BuilderViewportSession(storage, key);
  let viewport = { x: 0, y: 0, zoom: 1 };
  const apply = (v: Viewport) => { viewport = v; };
  session.initialize({ ...input, bounds: getNodesBounds(workflow.nodes) }, apply);
  for (const changed of [{ x: -300, y: 200, zoom: 1.5 }, { x: 30, y: 200, zoom: 0.5 }]) {
    apply(changed); session.remember(changed);
    // React rerenders on selection, measurements and ordinary container resizing.
    session.initialize({ ...input, width: 375 }, apply);
    assert.deepEqual(viewport, changed);
  }
  assert.deepEqual(workflow, before);
  const record = JSON.parse(storage.getItem(key)!);
  assert.deepEqual(Object.keys(record).sort(), ["layout", "savedAt", "version", "viewport"]);
  assert.equal(layoutFingerprint([...nodes].reverse()), input.layout);
  assert.notEqual(layoutFingerprint(nodes.map(n => ({ ...n, position: { x: n.position.x + 10, y: n.position.y } }))), input.layout);
});
