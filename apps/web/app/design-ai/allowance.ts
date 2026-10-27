export type TestAllowance = {
  can_request: boolean;
  blocked_reason: string | null;
  message: string;
  remaining_usd?: number;
  remaining_calls?: number;
  next_reservation_usd?: number;
  task_allowance?: { remaining_calls: number; limit_usd: number; reserved_usd: number };
};

export function allowanceFromError(body: unknown): TestAllowance | null {
  const detail = (body as { detail?: { code?: string; message?: string; allowance?: TestAllowance } } | null)?.detail;
  if (detail?.code !== "design_ai_allowance_paused") return null;
  return detail.allowance || { can_request: false, blocked_reason: "paused", message: detail.message || "AI testing is paused by the local test allowance." };
}

export function startingPrompts(templates: { key: string; label: string; available: boolean }[]): string[] {
  const prompts: Record<string, string> = {
    denmark: "Help me design a topology with Danish SysLAB",
    dutch: "Find a Dutch grid synthesis and benchmark workflow",
  };
  return templates.filter((item) => item.available).map((item) => prompts[item.key] || `Find an existing ${item.label} workflow`);
}
