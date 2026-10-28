"use client";

import { useEffect, useState } from "react";
import type { Node, Edge } from "@xyflow/react";

type Slot = { name: string; schema_ref?: string; semantic_concept: string };
type Contract = { id: string; contract_version: string; definition: {
  binding_transport?: string; inputs: Slot[]; outputs: Slot[];
} };

export default function CapabilityBindings({ nodes, edges, onBind }: {
  nodes: Node[]; edges: Edge[];
  onBind: (edgeId: string, source: Contract, target: Contract, sourceSlot: string, targetSlot: string) => void;
}) {
  const [contracts, setContracts] = useState<Record<string, Contract>>({});
  const [error, setError] = useState("");
  const ids = [...new Set(nodes.map(n => (n.data.service as { id?: string } | undefined)?.id).filter(Boolean))].sort().join(",");
  useEffect(() => {
    let active = true;
    setContracts({}); setError("");
    Promise.all(ids.split(",").filter(Boolean).map(async id => {
      const response = await fetch(`/api/services/${id}/operation-contract-resolution`);
      if (!response.ok) throw new Error("Connection definitions are unavailable. Reload to review them.");
      const value = await response.json();
      return [id, value.contract] as const;
    })).then(values => { if (active) setContracts(Object.fromEntries(values.filter(([, c]) => c))); })
      .catch(reason => { if (active) setError(reason.message); });
    return () => { active = false; };
  }, [ids]);
  const links = edges.flatMap(edge => {
    const source = nodes.find(n => n.id === edge.source), target = nodes.find(n => n.id === edge.target);
    const a = source?.data.service as { id: string; name: string } | undefined;
    const b = target?.data.service as { id: string; name: string } | undefined;
    return a && b ? [{ edge, a, b }] : [];
  });
  return <section aria-label="Data connections" style={{ marginTop: 24 }}>
    <h3>Data connections</h3>
    <p>Choose a published output and input, then validate the design. Matching catalogue labels alone do not verify compatibility.</p>
    {error && <p role="alert">{error}</p>}
    {links.length === 0 && <p>Connect services on the canvas to review their data flow.</p>}
    {links.map(({ edge, a, b }) => {
      const source = contracts[a.id], target = contracts[b.id];
      const supported = source?.definition.binding_transport === "whole-output-v1" && target?.definition.binding_transport === "whole-output-v1";
      const output = source?.definition.outputs[0], input = target?.definition.inputs[0];
      const binding = edge.data?.binding as { source_slot: string; target_slot: string } | undefined;
      return <div key={edge.id} style={{ borderTop: "1px solid #ddd", padding: "12px 0", overflowWrap: "anywhere" }}>
        <strong>{a.name} → {b.name}</strong>
        <p>{binding ? `${binding.source_slot.replaceAll("_", " ")} → ${binding.target_slot.replaceAll("_", " ")}. Validate to check the saved contract versions.` : "No explicit data binding selected."}</p>
        {supported && output && input ? <>
          <button type="button" onClick={() => onBind(edge.id, source, target, output.name, input.name)}>Use published connection</button>
          <details><summary>Contract details</summary>
            <p>Output {output.name}, version {source.contract_version}: {output.schema_ref || "Schema unknown"}</p>
            <p>Input {input.name}, version {target.contract_version}: {input.schema_ref || "Schema unknown"}</p>
            <p>The complete output reference is forwarded unchanged. No conversion is performed.</p>
          </details>
        </> : <p>Runtime binding support is not established for these operations. Ask the service owner to publish a verified contract.</p>}
      </div>;
    })}
  </section>;
}
