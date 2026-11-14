/** Presentation only. The registry/compiler remains the compatibility authority. */
export type Pin = { contract_id: string; contract_version: string };
export type Binding = { source_slot: string; target_slot: string };
export type Slot = { name: string; required?: boolean; schema_ref?: string; semantic_concept?: string; data_reference_protocols?: string[]; content_types?: string[]; value_representation?: string; source_requirement?: string; min_cardinality?: number; max_cardinality?: number };
export type Contract = { id: string; contract_version: string; definition: { binding_transport?: string; inputs: Slot[]; outputs: Slot[] } };
export type ReviewNode = { id: string; data: { label?: unknown; service?: unknown; operation_contract?: unknown } };
export type ReviewEdge = { id: string; source: string; target: string; data?: Record<string, unknown> };

export function stepLabel(node?: ReviewNode) {
  const service = node?.data.service as { name?: string } | undefined;
  return typeof node?.data.label === "string" && node.data.label.trim() ? node.data.label : service?.name || "Unknown step";
}

export function dataLabel(slot?: string) {
  // A display formatter, never an authority for binding compatibility.
  return slot && /^[a-z][a-z0-9_]{0,50}$/i.test(slot) ? slot.replace(/^captured_/, "").replaceAll("_", " ") : "data";
}

export function connectionSummary(source: string, target: string, binding?: Binding) {
  if (!binding) return `${source} → ${target}. No data binding selected.`;
  const noun = dataLabel(binding.source_slot);
  return `${source} → ${target}: sends ${noun === "data" ? "data" : `the ${noun}`}.`;
}

/** Presentation hint only; Save/compiler/runtime checks remain authoritative. */
export function publishedConnection(source?: Contract, target?: Contract) {
  if (source?.definition.binding_transport !== "whole-output-v1" || target?.definition.binding_transport !== "whole-output-v1")
    return { supported: false, reason: "These versions do not declare a supported output-to-input binding." };
  const output = source.definition.outputs[0], input = target.definition.inputs[0];
  if (source.definition.outputs.length !== 1 || target.definition.inputs.length !== 1 || !output || !input)
    return { supported: false, reason: "One published output and input slot are required." };
  if (!["upstream_operation", "upstream_or_workflow_input"].includes(input.source_requirement || ""))
    return { supported: false, reason: `Input ${input.name} requires separate workflow input; it does not accept this upstream output.` };
  const matches = output.value_representation === "data_reference" && input.value_representation === "data_reference"
    && output.semantic_concept && output.semantic_concept === input.semantic_concept && output.schema_ref && output.schema_ref === input.schema_ref
    && output.data_reference_protocols?.length && output.data_reference_protocols.every(p => input.data_reference_protocols?.includes(p))
    && output.content_types?.length && output.content_types.every(t => input.content_types?.includes(t))
    && output.min_cardinality === 1 && output.max_cardinality === 1 && input.max_cardinality === 1;
  return { supported: !!matches, reason: matches ? `Required ${input.name} connection: select the published binding, then save and validate.` : "Published meaning, schema, representation, protocol, format or cardinality differs. No conversion is available." };
}

export function stepPurpose(service: { input_type?: string; output_type?: string; description?: string }) {
  const meaningful = (value?: string) => value?.trim() && !/^(none|unknown|not declared|n\/a)$/i.test(value.trim()) ? value.trim() : undefined;
  const input = meaningful(service.input_type), output = meaningful(service.output_type);
  if (input && output) return `Uses ${input} to produce ${output}.`;
  if (output) return `Produces ${output}.`;
  if (input) return `Uses ${input}.`;
  const description = service.description?.trim();
  return description ? description.length > 180 ? `${description.slice(0, 177)}…` : description : "Select a setting or review the step's technical details.";
}

export function bindingSignature(nodes: ReviewNode[], edge: ReviewEdge) {
  return JSON.stringify([edge.source, edge.target, ...[edge.source, edge.target].map(id => {
    const data = nodes.find(n => n.id === id)?.data;
    const pin = data?.operation_contract as Pin | undefined;
    return [(data?.service as {id?: string} | undefined)?.id, pin?.contract_id, pin?.contract_version];
  }), edge.data?.binding ? [(edge.data.binding as Binding).source_slot, (edge.data.binding as Binding).target_slot] : null]);
}

export function savedBindingSignatures(nodes: ReviewNode[], edges: ReviewEdge[]) {
  return Object.fromEntries(edges.filter(e => e.data?.binding).map(e => [e.id, bindingSignature(nodes, e)]));
}

export function connectionState(input: { binding?: Binding; sourcePin?: Pin; targetPin?: Pin; source?: Contract; target?: Contract;
  loaded: boolean; signature: string; savedSignature?: string; checkedSignature?: string }) {
  const { binding, source, target, sourcePin, targetPin } = input;
  if (!binding) return { configured: false, persistence: "No binding selected", check: "Compatibility not checked", attention: false };
  const drift = input.loaded && (!source || !target || sourcePin?.contract_id !== source.id || targetPin?.contract_id !== target.id
    || sourcePin?.contract_version !== source.contract_version || targetPin?.contract_version !== target.contract_version
    || !source.definition.outputs.some(s => s.name === binding.source_slot) || !target.definition.inputs.some(s => s.name === binding.target_slot));
  return { configured: true, persistence: input.savedSignature === input.signature ? "Saved binding" : "Binding configured · not saved",
    check: drift ? "Connection requires attention" : input.checkedSignature === input.signature ? "Compatibility checked successfully" : "Compatibility not checked",
    attention: drift };
}
