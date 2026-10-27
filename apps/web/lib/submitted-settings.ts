// Historical values come only from the recorded submission and evidence.
export function submittedSettings(snapshot: any, evidence: any, node: any) {
  const requested = snapshot?.submitted?.request?.nodes?.find((item: any) => item.node_id === node.instance_id);
  const proof = evidence?.instances?.find((item: any) => item.instance_id === node.instance_id);
  return {
    requested: requested?.configuration?.parameters ?? null,
    effective: node.configuration?.parameters ?? null,
    consumed: proof?.state === "available" ? proof.algorithm_consumed : null,
    proof,
  };
}
