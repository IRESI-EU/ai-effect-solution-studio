"use client";

import { useState } from "react";
import { useAuth } from "./auth-context";
import type { SettingProperty, SettingsDefinition } from "./node-settings";

export type SettingRow = Row;

type Row = {
  name: string;
  title: string;
  type: SettingProperty["type"];
  defaultText: string;
  minimum: string;
  maximum: string;
  options: string;
  unit: string;
  description: string;
};

const TYPE_LABELS: Record<string, string> = {
  integer: "Whole number",
  number: "Decimal number",
  boolean: "Yes / No",
  string: "Text",
  array: "List (JSON)",
  object: "Structured value (JSON)",
};

export function toRows(definition: SettingsDefinition | null): Row[] {
  if (!definition) return [];
  return Object.entries(definition.schema.properties).map(([name, p]) => ({
    name,
    title: p.title || "",
    type: p.type,
    defaultText: p.default === undefined ? "" : typeof p.default === "string" ? p.default : JSON.stringify(p.default),
    minimum: p.minimum === undefined ? "" : String(p.minimum),
    maximum: p.maximum === undefined ? "" : String(p.maximum),
    options: p.enum ? p.enum.map((o) => (typeof o === "string" ? o : JSON.stringify(o))).join(", ") : "",
    unit: p.unit || "",
    description: p.description || "",
  }));
}

function parseTyped(text: string, type: Row["type"]): unknown {
  const value = text.trim();
  if (type === "string") return value;
  if (type === "integer" || type === "number") return Number(value);
  if (type === "boolean") return value.toLowerCase() === "true" || value.toLowerCase() === "yes";
  return JSON.parse(value);
}

export function toDefinition(channel: SettingsDefinition["channel"], rows: Row[]): SettingsDefinition {
  const properties: Record<string, SettingProperty> = {};
  for (const row of rows) {
    const name = row.name.trim();
    if (!name) throw new Error("Every setting needs the name the service reads (e.g. num_records).");
    if (properties[name]) throw new Error(`The setting name "${name}" is used twice.`);
    const prop: SettingProperty = { type: row.type };
    if (row.title.trim()) prop.title = row.title.trim();
    if (row.description.trim()) prop.description = row.description.trim();
    if (row.unit.trim()) prop.unit = row.unit.trim();
    if (row.type === "integer" || row.type === "number") {
      if (row.minimum.trim()) prop.minimum = Number(row.minimum);
      if (row.maximum.trim()) prop.maximum = Number(row.maximum);
    }
    if (row.options.trim()) {
      prop.enum = row.options.split(",").map((o) => parseTyped(o, row.type));
    }
    if (row.defaultText.trim()) {
      try {
        prop.default = parseTyped(row.defaultText, row.type);
      } catch {
        throw new Error(`The default for "${name}" is not valid JSON.`);
      }
    }
    properties[name] = prop;
  }
  return { channel, schema: { type: "object", properties } };
}

export const emptyRow = (): Row => ({
  name: "", title: "", type: "integer", defaultText: "", minimum: "", maximum: "", options: "", unit: "", description: "",
});

function describe(p: SettingProperty) {
  const parts = [TYPE_LABELS[p.type] || p.type];
  if (p.default !== undefined) parts.push(`default ${typeof p.default === "string" ? p.default : JSON.stringify(p.default)}`);
  if (p.minimum !== undefined || p.maximum !== undefined) parts.push(`range ${p.minimum ?? "…"} to ${p.maximum ?? "…"}`);
  if (p.enum) parts.push(`options: ${p.enum.map((o) => (typeof o === "string" ? o : JSON.stringify(o))).join(", ")}`);
  return parts.join(" · ");
}

export function ServiceSettingsEditor({
  serviceId,
  ownerNode,
  initial,
}: {
  serviceId: string;
  ownerNode: string | null;
  initial: SettingsDefinition | null;
}) {
  const { user } = useAuth();
  const [definition, setDefinition] = useState<SettingsDefinition | null>(initial);
  const [editing, setEditing] = useState(false);
  const [channel, setChannel] = useState<SettingsDefinition["channel"]>(initial?.channel || "parameters");
  const [rows, setRows] = useState<Row[]>(toRows(initial));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState("");

  const canEdit =
    user?.role === "platform_admin" || (user?.role === "node_manager" && !!ownerNode && user.node === ownerNode);

  function startEditing() {
    setChannel(definition?.channel || "parameters");
    setRows(definition ? toRows(definition) : [emptyRow()]);
    setError("");
    setSaved("");
    setEditing(true);
  }

  async function save(clear = false) {
    setError("");
    setSaved("");
    let body: SettingsDefinition | null = null;
    try {
      body = clear || rows.length === 0 ? null : toDefinition(channel, rows);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Please check the settings.");
      return;
    }
    setSaving(true);
    try {
      const res = await fetch(`/api/services/${encodeURIComponent(serviceId)}/settings`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(body),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(typeof data?.detail === "string" ? data.detail : `Could not save (HTTP ${res.status}).`);
      setDefinition(data.settings);
      setEditing(false);
      setSaved(data.settings ? "Settings saved. Designers can now adjust them in the Builder." : "Settings removed. The service now runs with fixed settings.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save settings.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="ae-card service-section" aria-label="Adjustable settings">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 className="section__title">Adjustable settings</h2>
        {canEdit && !editing && (
          <button type="button" className="ae-btn ae-btn--secondary" onClick={startEditing}>
            {definition ? "Edit settings" : "Declare settings"}
          </button>
        )}
      </div>

      {!editing && (
        definition ? (
          <ul className="service-list">
            {Object.entries(definition.schema.properties).map(([name, p]) => (
              <li key={name}>
                <strong>{p.title || name}</strong> <code>{name}</code>: {describe(p)}
                {p.description ? `. ${p.description}` : ""}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted" style={{ margin: 0 }}>
            Fixed settings: this service runs with the values chosen by its provider.
            {canEdit && " If the service reads values from its request, declare them so designers can adjust them."}
          </p>
        )
      )}

      {editing && (
        <div style={{ display: "grid", gap: 14 }}>
          <p className="muted" style={{ margin: 0 }}>
            Declare only settings your service already reads. <strong>Name</strong> must match the key in your code exactly
            (for example <code>request.parameters.get(&quot;num_records&quot;)</code> means the name is <code>num_records</code>).
          </p>
          <SettingsRowsEditor channel={channel} onChannel={setChannel} rows={rows} onRows={setRows} />
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" className="ae-btn ae-btn--primary" disabled={saving} onClick={() => save(false)}>
              {saving ? "Saving..." : "Save settings"}
            </button>
            <button type="button" className="ae-btn ae-btn--secondary" disabled={saving} onClick={() => setEditing(false)}>
              Cancel
            </button>
            {definition && (
              <button type="button" disabled={saving} onClick={() => save(true)} className="ae-btn ae-btn--ghost" style={{ color: "var(--danger-600)" }}>
                Remove all settings
              </button>
            )}
          </div>
        </div>
      )}

      {error && <p role="alert" className="ae-field__error">{error}</p>}
      {saved && <p role="status" style={{ color: "var(--success-600)", margin: 0 }}>{saved}</p>}
    </section>
  );
}

/** Channel choice and one card per setting, with an "Add setting" button. State lives with the caller. */
export function SettingsRowsEditor({
  channel,
  onChannel,
  rows,
  onRows,
}: {
  channel: SettingsDefinition["channel"];
  onChannel: (channel: SettingsDefinition["channel"]) => void;
  rows: Row[];
  onRows: (update: (current: Row[]) => Row[]) => void;
}) {
  const setChannel = onChannel;
  const setRows = onRows;
  const update = (index: number, patch: Partial<Row>) =>
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
  return (
    <>
          <label className="ae-field" style={{ maxWidth: 520 }}>
        <span className="ae-field__label">Where the service reads them</span>
        <select value={channel} onChange={(e) => setChannel(e.target.value as SettingsDefinition["channel"])} className="ae-select">
          <option value="parameters">From the request&apos;s &quot;parameters&quot; field (any step)</option>
          <option value="run_input">From its input JSON (first steps only)</option>
        </select>
      </label>

      {rows.map((row, index) => (
        <fieldset key={index} style={{ border: "1px solid var(--border)", borderRadius: "var(--radius-lg)", padding: "var(--space-4)", display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
          <legend className="ae-field__label" style={{ padding: "0 6px" }}>Setting {index + 1}</legend>
          <Field label="Name (key in code)" value={row.name} onChange={(v) => update(index, { name: v })} placeholder="num_records" />
          <Field label="Label shown to designers" value={row.title} onChange={(v) => update(index, { title: v })} placeholder="Records to generate" />
          <label className="ae-field">
            <span className="ae-field__label">Type</span>
            <select value={row.type} onChange={(e) => update(index, { type: e.target.value as Row["type"] })} className="ae-select">
              {Object.entries(TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <Field label="Default (what your service uses when empty)" value={row.defaultText} onChange={(v) => update(index, { defaultText: v })} placeholder={row.type === "boolean" ? "true / false" : "10"} />
          {(row.type === "integer" || row.type === "number") && (
            <>
              <Field label="Minimum" value={row.minimum} onChange={(v) => update(index, { minimum: v })} placeholder="1" />
              <Field label="Maximum" value={row.maximum} onChange={(v) => update(index, { maximum: v })} placeholder="1000" />
            </>
          )}
          {(row.type === "string" || row.type === "integer" || row.type === "number") && (
            <Field label="Allowed options (comma-separated, optional)" value={row.options} onChange={(v) => update(index, { options: v })} placeholder={row.type === "string" ? "json, csv" : ""} />
          )}
          <Field label="Unit (optional)" value={row.unit} onChange={(v) => update(index, { unit: v })} placeholder="W, s, %" />
          <div style={{ gridColumn: "1 / -1", display: "grid", gap: 4 }}>
            <Field label="Help text (optional)" value={row.description} onChange={(v) => update(index, { description: v })} placeholder="What changing this value does" />
          </div>
          <div style={{ gridColumn: "1 / -1" }}>
            <button type="button" className="ae-btn ae-btn--secondary" onClick={() => setRows((current) => current.filter((_, i) => i !== index))}>
              Remove this setting
            </button>
          </div>
        </fieldset>
      ))}

      <div>
        <button type="button" className="ae-btn ae-btn--secondary" onClick={() => setRows((current) => [...current, emptyRow()])}>
          + Add setting
        </button>
      </div>
    </>
  );
}

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <label className="ae-field">
      <span className="ae-field__label">{label}</span>
      <input className="ae-input" value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

