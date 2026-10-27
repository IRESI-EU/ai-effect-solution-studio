export function referenceMessage(refs: unknown, status: string) {
  if (!Array.isArray(refs)) return "References unavailable through this API.";
  if (refs.length) return "";
  if (status === "failed") return "Execution failed; no artifact recorded.";
  if (!["completed", "failed"].includes(status)) return "Results pending.";
  return "No artifact recorded.";
}

export function artifactMessage(state: string) {
  if (state === "available") return "Available";
  if (state === "inaccessible") return "Artifact recorded but currently inaccessible.";
  if (state === "pending") return "Results pending.";
  return "No artifact recorded.";
}
