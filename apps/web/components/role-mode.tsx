export type RoleMode = "solution_designer" | "node_provider" | "platform_admin";

export const ROLE_MODE_STORAGE_KEY = "ai-effect-role-mode";
export const ROLE_MODE_CHANGE_EVENT = "ai-effect-role-mode-change";

export const roleModeOptions: Array<{ value: RoleMode; label: string }> = [
  { value: "solution_designer", label: "Solution Designer" },
  { value: "node_provider", label: "Node Provider" },
  { value: "platform_admin", label: "Platform Admin" },
];

export const roleModeLabels: Record<RoleMode, string> = {
  solution_designer: "Solution Designer",
  node_provider: "Node Provider",
  platform_admin: "Platform Admin",
};

export function isRoleMode(value: string | null): value is RoleMode {
  return roleModeOptions.some((option) => option.value === value);
}

export function getStoredRoleMode(): RoleMode {
  if (typeof window === "undefined") return "solution_designer";
  const storedRole = window.localStorage.getItem(ROLE_MODE_STORAGE_KEY);
  return isRoleMode(storedRole) ? storedRole : "solution_designer";
}

export function storeRoleMode(role: RoleMode) {
  window.localStorage.setItem(ROLE_MODE_STORAGE_KEY, role);
  window.dispatchEvent(new CustomEvent(ROLE_MODE_CHANGE_EVENT, { detail: role }));
}
