// Shared (server + client) types and helpers for adjustable service settings.

export type SettingProperty = {
  type: "string" | "integer" | "number" | "boolean" | "array" | "object";
  title?: string;
  description?: string;
  default?: unknown;
  minimum?: number;
  maximum?: number;
  enum?: unknown[];
  minLength?: number;
  maxLength?: number;
  unit?: string;
};

export type SettingsDefinition = {
  channel: "parameters" | "run_input";
  schema: { type: "object"; properties: Record<string, SettingProperty>; required?: string[] };
};

export type SettingsValues = Record<string, unknown>;

export function settingsDefinitionOf(service: { interface_contract?: Record<string, unknown> | null } | null | undefined) {
  const settings = service?.interface_contract?.settings as SettingsDefinition | undefined;
  return settings && settings.schema?.properties ? settings : null;
}

