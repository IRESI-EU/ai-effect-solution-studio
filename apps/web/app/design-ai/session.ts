export type Message = { role: "user" | "assistant"; content: string };
export type Activity = { tool: string; status: string; summary: string };
export type Recommendation = { mechanism?: "registered_workflow" | "catalogue_service"; source_revision?: string; recommended_seed?: 42 | 43; key?: string; label: string; steps: { title: string; operation: string }[]; connection: string; expected_result_view: string[]; optional_downloads: string[]; availability: string; limitations: string[];
  candidate_id?: string; recommendation_revision?: string; creation_supported?: boolean; purpose?: string; contract_resolution?: string; input_requirements_known?: boolean; runtime_checked?: boolean;
  required_inputs?: { name: string; purpose?: string; choices?: number[] }[]; supported_settings?: { name: string; title: string; description: string }[] };
export type Conversation = { ownerId: string; draftId: string | null; messages: Message[]; activity: Activity[]; prompt: string; seedInput: string; historyUnavailable: boolean; recommendation?: Recommendation | null };

// Only an explicit URL selects active work. The legacy last-draft pointer is retained,
// but is never used to activate a draft on the starting page.
export function activeDraftId(params: Pick<URLSearchParams, "get">): string | null {
  return params.get("draftId")?.trim() || null;
}

export function draftUrl(id: string): string {
  return `/design-ai?draftId=${encodeURIComponent(id)}`;
}

export function designReturnUrl(metadata: Record<string, unknown> | null): string {
  return typeof metadata?.draft_id === "string" && metadata.draft_id ? draftUrl(metadata.draft_id) : "/design-ai";
}

export function conversationKey(ownerId: string, draftId: string | null): string {
  return draftId === null ? `design-ai-discovery:${ownerId}` : `design-ai-conversation:${ownerId}:${draftId}`;
}

export function readConversation(raw: string | null, ownerId: string, draftId: string | null): Conversation | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw);
    if (value.ownerId !== ownerId || value.draftId !== draftId || typeof value.prompt !== "string" || typeof value.seedInput !== "string" || typeof value.historyUnavailable !== "boolean"
      || !Array.isArray(value.messages) || !Array.isArray(value.activity)
      || !value.messages.every((m: Message) => m && ["user", "assistant"].includes(m.role) && typeof m.content === "string")
      || !value.activity.every((a: Activity) => a && typeof a.tool === "string" && typeof a.status === "string" && typeof a.summary === "string")) return null;
    return { ...value, ...(value.recommendation === undefined ? {} : { recommendation: readRecommendation(value.recommendation) }) };
  } catch { return null; }
}

export function readRecommendation(value: unknown): Recommendation | null {
  const item = value as Recommendation | null;
  const generic = item && typeof item.candidate_id === "string" && /^(service|workflow)-[a-f0-9]{24}$/.test(item.candidate_id)
    && typeof item.creation_supported === "boolean" && item.runtime_checked === false
    && (item.purpose === undefined || typeof item.purpose === "string")
    && (item.supported_settings === undefined || Array.isArray(item.supported_settings) && item.supported_settings.every(setting => setting && typeof setting.name === "string" && typeof setting.title === "string" && typeof setting.description === "string"))
    && Array.isArray(item.required_inputs) && item.required_inputs.every(input => input && typeof input.name === "string" && (input.purpose === undefined || typeof input.purpose === "string"))
    && (item.mechanism === "catalogue_service" && item.candidate_id.startsWith("service-") && !item.creation_supported
      || item.mechanism === "registered_workflow" && item.candidate_id.startsWith("workflow-") && item.creation_supported && typeof item.recommendation_revision === "string" && /^[a-f0-9]{64}$/.test(item.recommendation_revision) && [42, 43].includes(item.recommended_seed!));
  const legacy = item && item.candidate_id === undefined && item.key === "dutch" && (!item.mechanism || (item.mechanism === "registered_workflow" && typeof item.source_revision === "string" && [42, 43].includes(item.recommended_seed!)));
  return item && (generic || legacy) && typeof item.label === "string" && typeof item.connection === "string"
    && typeof item.availability === "string" && Array.isArray(item.steps)
    && item.steps.every(step => step && typeof step.title === "string" && typeof step.operation === "string")
    && [item.expected_result_view, item.optional_downloads, item.limitations].every(list => Array.isArray(list) && list.every(text => typeof text === "string")) ? item : null;
}

/** Browser storage is untrusted; the server independently revalidates this request. */
export function recommendationCreation(item: Recommendation | null): Record<string, unknown> | null {
  if (!item || !readRecommendation(item) || item.mechanism !== "registered_workflow") return null;
  return item.candidate_id
    ? { candidate_id: item.candidate_id, recommendation_revision: item.recommendation_revision, recommended_seed: item.recommended_seed }
    : { template_key: item.key, guided: true, recommendation_revision: item.source_revision, recommended_seed: item.recommended_seed };
}

export function conversationForCopy(ownerId: string, draftId: string, source: Conversation | null, carryDiscovery: boolean): Conversation {
  const carry = carryDiscovery && source?.ownerId === ownerId && source.draftId === null;
  return { ownerId, draftId, messages: carry ? source.messages.map(message => ({...message})) : [],
    activity: carry ? source.activity.map(event => ({...event})) : [], prompt: "", seedInput: "42", historyUnavailable: false, recommendation: null };
}
