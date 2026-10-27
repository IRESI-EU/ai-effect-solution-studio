import { getViewportForBounds } from "@xyflow/react";

export type Viewport = { x: number; y: number; zoom: number };
type Bounds = { x: number; y: number; width: number; height: number };
type Storage = Pick<globalThis.Storage, "getItem" | "setItem">;
export const MIN_ZOOM = 0.1;
export const MAX_ZOOM = 2;
const MAX_AGE = 90 * 24 * 60 * 60 * 1000;

export function viewportKey(userId: string, solutionId: string | null) {
  return solutionId ? `builder-viewport:v1:${encodeURIComponent(userId)}:${encodeURIComponent(solutionId)}` : null;
}

// A layout-only fingerprint: settings and artifact contents never enter storage.
export function layoutFingerprint(nodes: { id: string; position: { x: number; y: number } }[]) {
  const layout = JSON.stringify(nodes.map(n => [n.id, n.position.x, n.position.y]).sort((a, b) => String(a[0]).localeCompare(String(b[0]))));
  let hash = 2166136261;
  for (let i = 0; i < layout.length; i++) hash = Math.imul(hash ^ layout.charCodeAt(i), 16777619);
  return (hash >>> 0).toString(16);
}

export function validViewport(value: unknown): value is Viewport {
  if (!value || typeof value !== "object") return false;
  const { x, y, zoom } = value as Viewport;
  return [x, y, zoom].every(n => typeof n === "number" && Number.isFinite(n))
    && Math.abs(x) <= 10_000_000 && Math.abs(y) <= 10_000_000 && zoom >= MIN_ZOOM && zoom <= MAX_ZOOM;
}

export function readViewport(storage: Storage, key: string | null, layout: string, now = Date.now()): Viewport | null {
  if (!key) return null;
  try {
    const raw = storage.getItem(key);
    if (!raw || raw.length > 1024) return null;
    const record = JSON.parse(raw);
    if (record?.version !== 1 || record.layout !== layout || !Number.isFinite(record.savedAt)
      || record.savedAt > now || now - record.savedAt > MAX_AGE || !validViewport(record.viewport)) return null;
    const { x, y, zoom } = record.viewport;
    return { x, y, zoom };
  } catch { return null; }
}

export function initialViewport(bounds: Bounds, width: number, height: number): Viewport {
  const viewport = getViewportForBounds(bounds, width, height, 0.9, 1, 0.12);
  // If a readable overview cannot fit, start at the beginning, with the minimap
  // and explicit Fit workflow control providing navigation to the rest.
  if (bounds.width * viewport.zoom > width - 64) viewport.x = 32 - bounds.x * viewport.zoom;
  if (bounds.height * viewport.zoom > height - 64) viewport.y = 32 - bounds.y * viewport.zoom;
  return viewport;
}

// Only viewport adapters are accepted: no graph setter, Save or revision callback.
export class BuilderViewportSession {
  private initialized = false;
  private layout = "";
  private storage: Storage;
  private key: string | null;
  constructor(storage: Storage, key: string | null) { this.storage = storage; this.key = key; }

  initialize(input: { ready: boolean; width: number; height: number; bounds: Bounds; layout: string }, apply: (viewport: Viewport) => void) {
    const { ready, width, height, bounds, layout } = input;
    if (this.initialized || !ready || ![width, height, ...Object.values(bounds)].every(Number.isFinite)
      || width <= 0 || height <= 0 || bounds.width <= 0 || bounds.height <= 0) return false;
    this.initialized = true;
    this.layout = layout;
    apply(readViewport(this.storage, this.key, layout) ?? initialViewport(bounds, width, height));
    return true;
  }

  remember(viewport: Viewport) {
    if (!this.initialized || !this.key || !validViewport(viewport)) return;
    try {
      const { x, y, zoom } = viewport;
      this.storage.setItem(this.key, JSON.stringify({ version: 1, layout: this.layout, savedAt: Date.now(), viewport: { x, y, zoom } }));
    } catch { /* Blocked/full browser storage must not prevent canvas navigation. */ }
  }
}
