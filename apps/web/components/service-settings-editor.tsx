"use client";

import { useState } from "react";
import { useAuth } from "./auth-context";
import type { SettingProperty, SettingsDefinition } from "./node-settings";

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

function toRows(definition: SettingsDefinition | null): Row[] {
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

function toDefinition(channel: SettingsDefinition["channel"], rows: Row[]): SettingsDefinition {
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

const emptyRow = (): Row => ({
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

  const update = (index: number, patch: Partial<Row>) =>
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));

  return (
    <section className="card service-detail-section" aria-label="Adjustable settings">
      <p className="service-detail-eyebrow">Configuration</p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h2 style={{ margin: 0 }}>Adjustable settings</h2>
        {canEdit && !editing && (
          <button type="button" style={secondaryButton} onClick={startEditing}>
            {definition ? "Edit settings" : "Declare settings"}
          </button>
        )}
      </div>

      {!editing && (
        definition ? (
          <ul className="service-detail-limitations">
            {Object.entries(definition.schema.properties).map(([name, p]) => (
              <li key={name}>
                <strong>{p.title || name}</strong> <code>{name}</code>: {describe(p)}
                {p.description ? `. ${p.description}` : ""}
              </li>
            ))}
          </ul>
        ) : (
          <p className="service-detail-lead">
            Fixed settings: this service runs with the values chosen by its provider.
            {canEdit && " If the service reads values from its request, declare them so designers can adjust them."}
          </p>
        )
      )}

      {editing && (
        <div style={{ display: "grid", gap: 14 }}>
          <p style={{ color: "#667085", margin: 0, lineHeight: 1.6 }}>
            Declare only settings your service already reads. <strong>Name</strong> must match the key in your code exactly
            (for example <code>request.parameters.get(&quot;num_records&quot;)</code> means the name is <code>num_records</code>).
          </p>
          <label style={{ display: "grid", gap: 4, maxWidth: 520 }}>
            <span style={{ fontWeight: 600 }}>Where the service reads them</span>
            <select value={channel} onChange={(e) => setChannel(e.target.value as SettingsDefinition["channel"])} style={{ padding: 8 }}>
              <option value="parameters">From the request&apos;s &quot;parameters&quot; field (any step)</option>
              <option value="run_input">From its input JSON (first steps only)</option>
            </select>
          </label>

          {rows.map((row, index) => (
            <fieldset key={index} style={{ border: "1px solid #eaecf0", borderRadius: 12, padding: 12, display: "grid", gap: 8, gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))" }}>
              <legend style={{ fontWeight: 600, padding: "0 6px" }}>Setting {index + 1}</legend>
              <Field label="Name (key in code)" value={row.name} onChange={(v) => update(index, { name: v })} placeholder="num_records" />
              <Field label="Label shown to designers" value={row.title} onChange={(v) => update(index, { title: v })} placeholder="Records to generate" />
              <label style={{ display: "grid", gap: 4 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>Type</span>
                <select value={row.type} onChange={(e) => update(index, { type: e.target.value as Row["type"] })} style={{ padding: 8 }}>
                  {Object.entries(TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>
              <Field label="Default" value={row.defaultText} onChange={(v) => update(index, { defaultText: v })} placeholder={row.type === "boolean" ? "true / false" : "10"} />
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
                <button type="button" style={secondaryButton} onClick={() => setRows((current) => current.filter((_, i) => i !== index))}>
                  Remove this setting
                </button>
              </div>
            </fieldset>
          ))}

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button type="button" style={secondaryButton} onClick={() => setRows((current) => [...current, emptyRow()])}>
              + Add setting
            </button>
            <button type="button" style={primaryButton} disabled={saving} onClick={() => save(false)}>
              {saving ? "Saving..." : "Save settings"}
            </button>
            <button type="button" style={secondaryButton} disabled={saving} onClick={() => setEditing(false)}>
              Cancel
            </button>
            {definition && (
              <button type="button" disabled={saving} onClick={() => save(true)} style={{ ...secondaryButton, color: "#b42318" }}>
                Remove all settings
              </button>
            )}
          </div>
        </div>
      )}

      {error && <p role="alert" style={{ color: "#b42318" }}>{error}</p>}
      {saved && <p role="status" style={{ color: "#067647" }}>{saved}</p>}
    </section>
  );
}

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <label style={{ display: "grid", gap: 4 }}>
      <span style={{ fontSize: 13, fontWeight: 600 }}>{label}</span>
      <input value={value} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} style={{ padding: 8, boxSizing: "border-box", width: "100%" }} />
    </label>
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
