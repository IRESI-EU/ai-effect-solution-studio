"use client";
import { useEffect, useState } from "react";
import ReviewDialog from "./review-dialog";
import type { Node, Edge } from "@xyflow/react";
import { bindingSignature, connectionState, connectionSummary, stepLabel, type Binding, type Contract, type Pin } from "../lib/connection-review";

export default function CapabilityBindings({ nodes, edges, onBind, saved, checked, selectedEdgeId }: {
  nodes: Node[]; edges: Edge[]; saved: Record<string, string>; checked: Record<string, string>; selectedEdgeId: string | null;
  onBind: (edgeId: string, source: Contract, target: Contract, sourceSlot: string, targetSlot: string) => void;
}) {
  const [detailsEdge, setDetailsEdge] = useState<string | null>(null);
  const [contracts, setContracts] = useState<Record<string, Contract>>({});
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const ids = [...new Set(nodes.map(n => (n.data.service as { id?: string } | undefined)?.id).filter(Boolean))].sort().join(",");
  useEffect(() => {
    let active = true;
    setContracts({}); setError(""); setLoaded(false);
    Promise.all(ids.split(",").filter(Boolean).map(async id => {
      const response = await fetch(`/api/services/${id}/operation-contract-resolution`);
      if (!response.ok) throw new Error("Connection definitions are unavailable. Reload to review them.");
      const value = await response.json();
      return [id, value.contract] as const;
    })).then(values => { if (active) { setContracts(Object.fromEntries(values.filter(([, c]) => c))); setLoaded(true); } })
      .catch(reason => { if (active) { setError(reason.message); setLoaded(true); } });
    return () => { active = false; };
  }, [ids]);
  const links = edges.flatMap(edge => {
    const a = nodes.find(n => n.id === edge.source), b = nodes.find(n => n.id === edge.target);
    return a?.data.service && b?.data.service ? [{ edge, a, b }] : [];
  });
  return <section aria-label="Data connections" className="connection-review">
    <h3>Data connections</h3>
    {error && <p role="alert">{error}</p>}
    {!links.length && <p>Connect two steps on the canvas to review their data flow.</p>}
    {links.map(({ edge, a, b }) => {
      const source = contracts[(a.data.service as {id: string}).id], target = contracts[(b.data.service as {id: string}).id];
      const binding = edge.data?.binding as Binding | undefined;
      const state = connectionState({ binding, source, target, sourcePin: a.data.operation_contract as Pin | undefined,
        targetPin: b.data.operation_contract as Pin | undefined, loaded, signature: bindingSignature(nodes, edge),
        savedSignature: saved[edge.id], checkedSignature: checked[edge.id] });
      const supported = source?.definition.binding_transport === "whole-output-v1" && target?.definition.binding_transport === "whole-output-v1"
        && source.definition.outputs.length === 1 && target.definition.inputs.length === 1;
      const output = source?.definition.outputs.find(s => s.name === binding?.source_slot) || source?.definition.outputs[0];
      const input = target?.definition.inputs.find(s => s.name === binding?.target_slot) || target?.definition.inputs[0];
      const setup = supported && output && input ? <button type="button" onClick={() => onBind(edge.id, source, target, output.name, input.name)}>Use published connection</button> :
        <p>Published connection setup is unavailable. Ask the service owner to review its contract.</p>;
      return <article key={edge.id} className={`connection-card ${selectedEdgeId === edge.id ? "is-selected" : ""}`}>
        <p className="connection-sentence">{connectionSummary(stepLabel(a), stepLabel(b), binding)}</p>
        <p className="connection-state"><span>{state.persistence}</span>{state.attention && <span className="connection-attention">{state.check}</span>}</p>
        {state.attention && <p role="alert">The selected slots or contract pins need review. Viewing this panel does not update them.</p>}
        <button type="button" className="connection-details-button" onClick={() => setDetailsEdge(edge.id)}>Technical details for this connection</button>
        <ReviewDialog open={detailsEdge === edge.id} onClose={() => setDetailsEdge(null)} title="Connection technical details">
          <p><strong>{state.persistence} · {state.check}</strong></p>
          <p>From <strong>{stepLabel(a)}</strong> to <strong>{stepLabel(b)}</strong>.</p>
          <p>Validate design to check compatibility. Runtime availability is checked separately.</p>
          <section aria-label="Exact connection mapping">
            <dl><dt>Output slot</dt><dd>{binding?.source_slot || "Not selected"}</dd><dt>Input slot</dt><dd>{binding?.target_slot || "Not selected"}</dd>
              <dt>Source contract pin</dt><dd>{JSON.stringify(a.data.operation_contract || "Not selected")}</dd>
              <dt>Target contract pin</dt><dd>{JSON.stringify(b.data.operation_contract || "Not selected")}</dd>
              <dt>Current output schema</dt><dd>{output?.schema_ref || "Unknown"}</dd><dt>Current input schema</dt><dd>{input?.schema_ref || "Unknown"}</dd>
              <dt>Protocols</dt><dd>{output?.data_reference_protocols?.join(", ") || "Unknown"} → {input?.data_reference_protocols?.join(", ") || "Unknown"}</dd>
              <dt>Content types</dt><dd>{output?.content_types?.join(", ") || "Unknown"} → {input?.content_types?.join(", ") || "Unknown"}</dd>
              <dt>Current published versions</dt><dd>{source?.contract_version || "Unknown"} → {target?.contract_version || "Unknown"}</dd>
              <dt>Instances</dt><dd>{edge.source} → {edge.target}</dd></dl>
            <p>{supported ? "whole-output-v1 forwards one complete reference. No projection, conversion or merge." : "Supported runtime transport is unknown."}</p>
          </section>
          {binding ? <details><summary>Edit connection</summary><p>This explicit action selects current published pins and slots. Review changes before Save; compatibility must be checked again.</p>{setup}</details> : setup}
        </ReviewDialog>
        {!binding && supported && <p>Open the connection details to set up its binding.</p>}
      </article>;
    })}
  </section>;
}
