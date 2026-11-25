import type { Node } from "@xyflow/react";

export function isServiceNode(node: Node): boolean {
  const data = node.data as Record<string, unknown> | undefined;
  const service = data?.service as Record<string, unknown> | undefined;
  return data?.node_kind === "service" || Boolean(service?.id);
}

export function countServiceNodes(nodes: Node[]): number {
  return nodes.filter(isServiceNode).length;
}

export function countServiceConnections(nodes: Node[], edges: { source: string; target: string }[]): number {
  const serviceNodeIds = new Set(nodes.filter(isServiceNode).map((node) => node.id));
  return edges.filter((edge) => serviceNodeIds.has(edge.source) && serviceNodeIds.has(edge.target)).length;
}

export function apiErrorMessage(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    const ids = (detail as { service_ids?: unknown }).service_ids;
    const action = (detail as { recommended_action?: unknown }).recommended_action;
    return [
      typeof message === "string" ? message : fallback,
      Array.isArray(ids) && ids.length ? `Missing/inaccessible service IDs: ${ids.join(", ")}.` : "",
      typeof action === "string" ? action : "",
    ].filter(Boolean).join(" ");
  }
  return fallback;
}
