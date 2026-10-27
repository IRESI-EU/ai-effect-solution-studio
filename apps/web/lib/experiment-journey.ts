/** Always build from the workflow identity, never append to an existing fragment. */
export function deploymentResultsUrl(workflowId: string) {
  return `/deployments/${encodeURIComponent(workflowId.split(/[?#]/, 1)[0])}#results`;
}

export function isDutchExperiment(nodes: { data?: Record<string, unknown> }[], metadata: Record<string, unknown> | null) {
  const operations = nodes.flatMap(node => {
    const service = node.data?.service as { operation_name?: string } | undefined;
    return service ? [service.operation_name] : [];
  });
  const input = metadata?.run_input as Record<string, unknown> | undefined;
  return operations.join(",") === "ConfigureAndSynthesize,RunBenchmark" && !!input && Object.keys(input).join() === "seed" && Number.isInteger(input.seed);
}

export function executionLabel(status: string) {
  if (status === "completed") return "Completed";
  if (status === "failed") return "Execution failed";
  if (["submitted", "queued", "pending"].includes(status)) return "Submitted — waiting to run";
  if (status === "running") return "Running";
  return "Status unavailable";
}
