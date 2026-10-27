import type { Node, Edge } from "@xyflow/react";

export function copyInstance(node: Node, edges: Edge[], id: string): { node: Node; edges: Edge[] } {
  const copy = structuredClone(node);
  copy.id = id;
  copy.selected = false;
  if (typeof copy.data.label === "string") copy.data.label += " (copy)";
  copy.position = { x: node.position.x + 60, y: node.position.y + 90 };
  return { node: copy, edges: edges.filter(edge => edge.target === node.id && edge.source !== node.id).map(edge => ({
    ...structuredClone(edge), id: `${edge.id}-copy-${id}`, target: id, selected: false,
  })) };
}
