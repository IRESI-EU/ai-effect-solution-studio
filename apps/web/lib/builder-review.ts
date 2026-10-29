/** Read-only presentation of the recorded graph and current review state. */
type GraphNode = { id: string; data: Record<string, unknown>; [key: string]: unknown };
type GraphEdge = { source: string; target: string; [key: string]: unknown };
const name = (node: GraphNode) => {
  const service = node.data.service as { name?: string } | undefined;
  return service?.name || (typeof node.data.label === "string" ? node.data.label : "Unnamed processing step");
};

export function workflowReview<T extends GraphNode>(nodes: T[], edges: GraphEdge[]) {
  const steps = nodes.filter(node => node.data.service);
  const links = edges.filter(edge => steps.some(n => n.id === edge.source) && steps.some(n => n.id === edge.target));
  const starts = steps.filter(node => !links.some(edge => edge.target === node.id));
  const ordered: T[] = [];
  if (starts.length === 1) {
    let current: T | undefined = starts[0];
    while (current && !ordered.includes(current)) {
      ordered.push(current);
      const next = links.filter(edge => edge.source === current!.id);
      if (next.length !== 1) break;
      current = steps.find(node => node.id === next[0].target);
    }
  }
  const linear = ordered.length === steps.length && links.length === steps.length - 1
    && steps.every(node => links.filter(e => e.target === node.id).length <= 1 && links.filter(e => e.source === node.id).length <= 1);
  return { steps: linear ? ordered : steps, linear,
    purpose: !steps.length ? "Add a processing step to start this workflow." : linear
      ? `${ordered.map(name).join(", then ")}.` : `${steps.length} processing steps. Review their saved connections below.` };
}

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  return value && typeof value === "object" ? Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, canonical(v)])) : value;
}
export function designFingerprint(name: string, nodes: GraphNode[], edges: GraphEdge[], runInput?: unknown) {
  const clean = (value: Record<string, unknown>, ignored: string[]) => Object.fromEntries(Object.entries(value).filter(([key]) => !ignored.includes(key)));
  return JSON.stringify(canonical({ name, runInput, nodes: nodes.map(n => clean(n, ["selected", "dragging", "measured", "width", "height", "resizing", "positionAbsolute"])),
    edges: edges.map(e => clean(e, ["selected"])) }));
}
export function offlineReview(config?: { provider_mode?: string; provider_name?: string } | null, environment = "") {
  return environment.startsWith("OFFLINE") || (config?.provider_mode === "test" && config.provider_name === "OFFLINE structural provider-boundary fixtures");
}
export type ReviewAction = "add" | "save" | "validate" | "review" | "prepare" | "confirm" | "results";
export function nextReviewAction(state: { steps: number; dirty: boolean; design: "valid" | "invalid" | null;
  offline: boolean; readiness?: "ready" | "blocked"; confirmationReady: boolean; submitted: boolean }): ReviewAction {
  if (!state.steps) return "add";
  if (state.dirty) return "save";
  if (state.design !== "valid") return "validate";
  if (state.offline) return "review";
  if (state.submitted) return "results";
  return state.readiness === "ready" && state.confirmationReady ? "confirm" : "prepare";
}

export function reviewInput(mode: "prompt" | "json", text: string): unknown {
  if (!text.trim()) return null;
  if (mode === "prompt") return {prompt:text.trim()};
  try { return JSON.parse(text); } catch { return {unparsed_input:text, mode}; }
}
