"use client";
import { useEffect, useState } from "react";
import { submittedSettings } from "../lib/submitted-settings";

export default function SubmittedConfiguration({ workflowId, status, onConfigured, resultsAvailable = false }: { workflowId: string; status: string; resultsAvailable?: boolean; onConfigured: (value: boolean) => void }) {
  const [snapshot, setSnapshot] = useState<any>(null);
  const [evidence, setEvidence] = useState<any>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!workflowId) return;
    let active = true;
    setSnapshot(null); setEvidence(null); setError("");
    Promise.allSettled(["submitted-configuration", "instance-evidence"].map(async route => {
      const response = await fetch(`/api/workflows/${workflowId}/${route}`, { cache: "no-store" });
      if (!response.ok) throw new Error(response.status === 404 ? "No submitted instance settings were recorded for this historical run." : "Recorded instance settings are unavailable.");
      return response.json();
    })).then(([recorded, proof]) => {
      if (!active) return;
      if (recorded.status === "fulfilled") {
        const value = recorded.value;
        setSnapshot(value);
        onConfigured(value.submitted.compiled.solution_studio_metadata.execution_instances.some((n: any) => n.configuration != null));
      } else setError(recorded.reason.message);
      if (proof.status === "fulfilled") setEvidence(proof.value);
      else if (recorded.status === "fulfilled") setError("Algorithm evidence is unavailable. Submitted settings remain recorded below.");
    });
    return () => { active = false; };
  }, [workflowId, status, onConfigured]);
  const configured = snapshot?.submitted.compiled.solution_studio_metadata.execution_instances.some((n: any) => n.configuration != null);
  return <section id={configured && !resultsAvailable ? "results" : "instance-settings"} className="card" style={{ padding: 26, marginTop: 20, scrollMarginTop: 90 }} aria-label="Recorded instance settings">
    <h2>Recorded instance settings</h2>
    {error && <p role="status">{error}</p>}
    {snapshot && <>
      <p>Validated settings from the immutable submission. Algorithm consumption is verified separately for each instance.</p>
      {snapshot.submitted.compiled.solution_studio_metadata.capability_bindings?.status === "verified" && <details><summary>Recorded data connections</summary><ul>{snapshot.submitted.compiled.solution_studio_metadata.capability_bindings.bindings.map((binding: any, index: number) => <li key={index}>{binding.source} / {binding.source_slot} → {binding.target} / {binding.target_slot}<br />Schema: {binding.schema_ref}</li>)}</ul></details>}
      {snapshot.submitted.compiled.solution_studio_metadata.execution_instances.map((node: any) => {
        const { requested, effective, consumed, proof } = submittedSettings(snapshot, evidence, node);
        const metadata = snapshot.submitted.compiled.solution_studio_metadata;
        const published = metadata.capability_bindings?.contracts?.[node.instance_id];
        const noEditableSettings = published && !published.definition.execution_parameters;
        const label = metadata.nodes?.find((item: any) => item.node_id === node.instance_id)?.service_name || node.operation_name;
        return <div key={node.instance_id} style={{ marginTop: 18 }}>
          <h3>{label}</h3>
          <details><summary>Execution identifiers</summary><p style={{ overflowWrap: "anywhere" }}>Instance {node.instance_id} · Task {node.task_id}</p></details>
          {noEditableSettings ? <>
            <p>This operation has no editable settings.</p>
            {node.input_bindings.length > 0 && <p>Data input: {proof?.state === "available" && proof.input_binding_verified
              ? "Verified from the upstream output captured for this run." : "Unverified — associated input evidence is unavailable."}</p>}
          </> : <>
          <p>Requested overrides: {requested != null ? <code>{JSON.stringify(requested)}</code> : "Not recorded"}</p>
          <p>Validated effective settings: {effective != null ? <code>{JSON.stringify(effective)}</code> : "Legacy caller — service defaults were not recorded as instance parameters"}</p>
          <p>Algorithm consumed: {consumed != null ? <code>{JSON.stringify(consumed)}</code> : "Unverified — no validated algorithm evidence available"}</p>
          </>}
          {proof?.summary?.topology_count != null && <p>Topologies generated: {proof.summary.topology_count}</p>}
          {proof?.state === "available" && <details><summary>Evidence details</summary><p>{proof.instrumentation}</p><p style={{ overflowWrap: "anywhere" }}>Output SHA-256: {proof.output_sha256}</p></details>}
        </div>;
      })}
    </>}
  </section>;
}
