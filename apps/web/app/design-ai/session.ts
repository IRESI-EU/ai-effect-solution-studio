export type Message = { role: "user" | "assistant"; content: string };
export type Activity = { tool: string; status: string; summary: string };
export type Recommendation = { key: string; label: string; steps: { title: string; operation: string }[]; connection: string; expected_result_view: string[]; optional_downloads: string[]; availability: string; limitations: string[] };
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
  return item && item.key === "dutch" && typeof item.label === "string" && typeof item.connection === "string"
    && typeof item.availability === "string" && Array.isArray(item.steps)
    && item.steps.every(step => step && typeof step.title === "string" && typeof step.operation === "string")
    && [item.expected_result_view, item.optional_downloads, item.limitations].every(list => Array.isArray(list) && list.every(text => typeof text === "string")) ? item : null;
}

export function conversationForCopy(ownerId: string, draftId: string, source: Conversation | null, carryDiscovery: boolean): Conversation {
  const carry = carryDiscovery && source?.ownerId === ownerId && source.draftId === null;
  return { ownerId, draftId, messages: carry ? source.messages.map(message => ({...message})) : [],
    activity: carry ? source.activity.map(event => ({...event})) : [], prompt: "", seedInput: "42", historyUnavailable: false, recommendation: null };
}
