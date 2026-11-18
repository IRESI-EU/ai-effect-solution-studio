// Presentation only. The API resolves and validates the selected real operation.
export function suppliedOperations(text: string): { id: string; label: string }[] {
  try {
    const document = JSON.parse(text);
    if (!document?.openapi || !document.paths || typeof document.paths !== "object") return [];
    return Object.entries(document.paths).flatMap(([path, value]) => {
      if (!value || typeof value !== "object") return [];
      return Object.entries(value).flatMap(([method, operation]) => {
        if (!["get", "post", "put", "patch", "delete", "options", "head", "trace"].includes(method.toLowerCase()) || !operation || typeof operation !== "object") return [];
        const id = (operation as { operationId?: unknown }).operationId;
        return typeof id === "string" && id ? [{ id, label: `${method.toUpperCase()} ${path} · ${id}` }] : [];
      });
    });
  } catch { return []; }
}
