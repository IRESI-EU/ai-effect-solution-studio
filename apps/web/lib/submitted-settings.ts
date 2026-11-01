// Historical values come only from the recorded submission and evidence.
export function submittedSettings(snapshot: any, evidence: any, node: any) {
  const requested = snapshot?.submitted?.request?.nodes?.find((item: any) => item.node_id === node.instance_id);
  const candidates = evidence?.instances?.filter((item: any) => item.instance_id === node.instance_id) || [];
  const candidate = candidates[0];
  const matching = candidates.length === 1 && candidate.task_id === node.task_id
    && (!node.node_key || candidate.node_key === node.node_key)
    && (!snapshot?.workflow_id || evidence.workflow_id === snapshot.workflow_id)
    && (!snapshot?.id || evidence.submission_id === snapshot.id);
  const proof = candidate && !matching
    ? { state: "conflicting", message: "Evidence belongs to a different submission, workflow or task." }
    : candidate;
  return {
    requested: requested?.configuration?.parameters ?? null,
    effective: node.configuration?.parameters ?? null,
    consumed: proof?.state === "available" ? proof.algorithm_consumed : null,
    proof,
  };
}

export function submittedEvidenceStatus(proof: any, evidence: any, kind: "parameters" | "input") {
  if (!proof && evidence?.state === "available") {
    return { label: "Unavailable", message: "No matching evidence was recorded for this instance." };
  }
  if (proof?.state === "available") {
    const verified = kind === "input" ? proof.input_binding_verified === true : proof.algorithm_consumed != null;
    return verified ? { label: "Verified", message: proof.message || "Verified from the recorded capture for this instance." }
      : { label: "Unavailable", message: kind === "input" ? "No validated input association was recorded for this instance." : "No validated consumed parameters were recorded for this instance." };
  }
  const state = proof?.state || evidence?.state || "unavailable";
  const labels: Record<string, string> = { pending: "Pending", delayed: "Pending", inaccessible: "Inaccessible", conflicting: "Conflicting", invalid: "Invalid", collection_failed: "Invalid", unavailable: "Unavailable" };
  return { label: labels[state] || "Unavailable", message: proof?.message || evidence?.message || "No validated evidence is available for this instance." };
}
