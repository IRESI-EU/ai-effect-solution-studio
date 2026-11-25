"use client";

import { useEffect, useState } from "react";

import { settingsDefinitionOf, type SettingProperty, type SettingsDefinition, type SettingsValues } from "../lib/service-settings";

export { settingsDefinitionOf };
export type { SettingProperty, SettingsDefinition, SettingsValues };

/** Returns an error message for a value, mirroring the API's checks. */
export function validateSetting(name: string, value: unknown, prop: SettingProperty): string | null {
  const label = prop.title || name;
  const typeOk =
    (prop.type === "string" && typeof value === "string") ||
    (prop.type === "boolean" && typeof value === "boolean") ||
    (prop.type === "integer" && Number.isInteger(value)) ||
    (prop.type === "number" && typeof value === "number" && Number.isFinite(value)) ||
    (prop.type === "array" && Array.isArray(value)) ||
    (prop.type === "object" && typeof value === "object" && value !== null && !Array.isArray(value));
  if (!typeOk) return `${label} must be ${prop.type === "integer" ? "a whole number" : `a ${prop.type}`}.`;
  if (prop.enum && !prop.enum.some((option) => JSON.stringify(option) === JSON.stringify(value))) {
    return `${label} must be one of the listed options.`;
  }
  if (typeof value === "number") {
    if (prop.minimum !== undefined && value < prop.minimum) return `${label} must be at least ${prop.minimum}.`;
    if (prop.maximum !== undefined && value > prop.maximum) return `${label} must be at most ${prop.maximum}.`;
  }
  if (typeof value === "string") {
    if (prop.minLength !== undefined && value.length < prop.minLength) return `${label} needs at least ${prop.minLength} characters.`;
    if (prop.maxLength !== undefined && value.length > prop.maxLength) return `${label} allows at most ${prop.maxLength} characters.`;
  }
  return null;
}

export function settingsErrors(definition: SettingsDefinition | null, values: SettingsValues | undefined): string[] {
  if (!definition || !values) return [];
  return Object.entries(values).flatMap(([name, value]) => {
    const prop = definition.schema.properties[name];
    if (!prop) return [`${name} is no longer a setting of this service.`];
    const error = validateSetting(name, value, prop);
    return error ? [error] : [];
  });
}

function formatDefault(value: unknown) {
  if (value === undefined) return "no default";
  return typeof value === "string" ? value : JSON.stringify(value);
}

function JsonField({ value, onChange, ariaLabel }: { value: unknown; onChange: (v: unknown, error: string | null) => void; ariaLabel: string }) {
  const [text, setText] = useState(value === undefined ? "" : JSON.stringify(value, null, 2));
  useEffect(() => {
    setText(value === undefined ? "" : JSON.stringify(value, null, 2));
  }, [value]);
  return (
    <textarea
      aria-label={ariaLabel}
      rows={4}
      value={text}
      onChange={(event) => {
        setText(event.target.value);
        if (!event.target.value.trim()) return onChange(undefined, null);
        try {
          onChange(JSON.parse(event.target.value), null);
        } catch {
          onChange(undefined, "Enter valid JSON.");
        }
      }}
      style={{ width: "100%", padding: 8, fontFamily: "monospace", fontSize: 12, boxSizing: "border-box" }}
    />
  );
}

type Props = {
  definition: SettingsDefinition | null;
  values: SettingsValues | undefined;
  onChange: (values: SettingsValues) => void;
  isStartNode: boolean;
  /** "run" = values apply to one run only and fall back to the saved values. */
  mode?: "saved" | "run";
  title?: string;
  /** Keeps field ids unique when several panels are on one page. */
  idPrefix?: string;
};

export function NodeSettingsPanel({ definition, values, onChange, isStartNode, mode = "saved", title = "Settings", idPrefix = "setting" }: Props) {
  const [jsonErrors, setJsonErrors] = useState<Record<string, string>>({});

  if (!definition) {
    return (
      <section aria-label="Service settings" style={{ borderTop: "1px solid #eaecf0", paddingTop: 12 }}>
        <h4 style={{ margin: "0 0 6px" }}>Settings</h4>
        <p style={{ color: "#667085", fontSize: 13, margin: 0 }}>
          Fixed settings: this service runs with the values chosen by its provider.
        </p>
      </section>
    );
  }

  const current = values || {};
  const properties = Object.entries(definition.schema.properties);
  const setValue = (name: string, value: unknown) => {
    const next = { ...current };
    if (value === undefined) delete next[name];
    else next[name] = value;
    onChange(next);
  };

  return (
    <section aria-label="Service settings" style={{ borderTop: "1px solid #eaecf0", paddingTop: 12, display: "grid", gap: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h4 style={{ margin: 0 }}>{title}</h4>
        {Object.keys(current).length > 0 && (
          <button type="button" onClick={() => onChange({})} style={{ ...secondaryButton, fontSize: 12, padding: "4px 8px" }}>
            Reset to defaults
          </button>
        )}
      </div>
      {definition.channel === "run_input" && !isStartNode && (
        <p role="alert" style={{ color: "#b42318", fontSize: 13, margin: 0 }}>
          These settings are read from the workflow input, so this service must be a first step (no incoming connection from another service).
        </p>
      )}
      {properties.map(([name, prop]) => {
        const id = `${idPrefix}-${name}`;
        const label = prop.title || name;
        const value = current[name];
        const error = jsonErrors[name] || (value !== undefined ? validateSetting(name, value, prop) : null);
        let field;
        if (prop.type === "boolean") {
          field = (
            <select id={id} value={value === undefined ? "" : String(value)} onChange={(e) => setValue(name, e.target.value === "" ? undefined : e.target.value === "true")} style={{ width: "100%", padding: 8 }}>
              <option value="">Default ({formatDefault(prop.default)})</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          );
        } else if (prop.enum) {
          field = (
            <select id={id} value={value === undefined ? "" : JSON.stringify(value)} onChange={(e) => setValue(name, e.target.value === "" ? undefined : JSON.parse(e.target.value))} style={{ width: "100%", padding: 8 }}>
              <option value="">Default ({formatDefault(prop.default)})</option>
              {prop.enum.map((option) => (
                <option key={JSON.stringify(option)} value={JSON.stringify(option)}>{formatDefault(option)}</option>
              ))}
            </select>
          );
        } else if (prop.type === "integer" || prop.type === "number") {
          field = (
            <input id={id} type="number" step={prop.type === "integer" ? 1 : "any"} min={prop.minimum} max={prop.maximum}
              value={value === undefined ? "" : String(value)} placeholder={`Default: ${formatDefault(prop.default)}`}
              onChange={(e) => setValue(name, e.target.value === "" ? undefined : Number(e.target.value))}
              style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
          );
        } else if (prop.type === "string") {
          field = (
            <input id={id} type="text" value={value === undefined ? "" : String(value)} placeholder={`Default: ${formatDefault(prop.default)}`}
              onChange={(e) => setValue(name, e.target.value === "" ? undefined : e.target.value)}
              style={{ width: "100%", padding: 8, boxSizing: "border-box" }} />
          );
        } else {
          field = (
            <JsonField ariaLabel={label} value={value} onChange={(parsed, parseError) => {
              setJsonErrors((prev) => {
                const next = { ...prev };
                if (parseError) next[name] = parseError;
                else delete next[name];
                return next;
              });
              if (!parseError) setValue(name, parsed);
            }} />
          );
        }
        return (
          <div key={name} style={{ display: "grid", gap: 4 }}>
            <label htmlFor={id} style={{ fontWeight: 600, fontSize: 13 }}>
              {label}{prop.unit ? ` (${prop.unit})` : ""}
            </label>
            {field}
            {prop.description && <small style={{ color: "#667085" }}>{prop.description}</small>}
            {(prop.minimum !== undefined || prop.maximum !== undefined) && (
              <small style={{ color: "#667085" }}>
                Allowed: {prop.minimum ?? "…"} to {prop.maximum ?? "…"}
              </small>
            )}
            {error && <small role="alert" style={{ color: "#b42318" }}>{error}</small>}
          </div>
        );
      })}
      <small style={{ color: "#667085" }}>
        {mode === "run"
          ? "Empty fields keep the solution's saved value (or the provider's default). These values apply to this run only."
          : "Empty fields use the provider's default. Values are saved with the solution."}
      </small>
    </section>
  );
}

const primaryButton = {
  background: "linear-gradient(135deg, #5b2cf2, #4320ca)", color: "white", padding: "8px 12px",
  borderRadius: 10, border: "none", fontWeight: 700, cursor: "pointer",
} as const;

const secondaryButton = {
  background: "white", color: "#5635ce", padding: "8px 12px",
  borderRadius: 10, border: "1px solid #d1c8f3", fontWeight: 700, cursor: "pointer",
} as const;
