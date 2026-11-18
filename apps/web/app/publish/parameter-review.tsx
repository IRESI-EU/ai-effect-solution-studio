"use client";

import { useEffect, useState, type CSSProperties } from "react";

type Definition = { type: "integer" | "number" | "boolean" | "string"; title: string; description: string; required?: boolean; default?: unknown; minimum?: number; maximum?: number; enum?: unknown[]; unit?: string };
type Candidate = { name: string; source_pointer: string; classification: string; supported: boolean; reason?: string; definition?: Definition };
type Discovery = { revision: string; operation_name: string; source_reference: string; source_sha256: string; candidates: Candidate[] };
type Contract = { id: string; contract_version: string; status: string; operation_identity: string; definition: { execution_parameters?: { properties: Record<string, Definition> } } };
type State = { operation_name: string; service_status: string; interface_type: string; discovery?: Discovery; reviews: Record<string, { evidence_reference: string; mappings?: Record<string, { algorithm_mapping: string; transport_path: string }> }> };
type Row = Candidate & { selected: boolean; definition: Definition; defaultText: string; minimumText: string; maximumText: string; enumText: string; mapping: string };

function editable(candidate: Candidate): Row {
  const definition = candidate.definition || { type: "integer", title: candidate.name, description: "" };
  return { ...candidate, definition, selected: false, mapping: "",
    defaultText: "default" in definition ? JSON.stringify(definition.default) : "",
    minimumText: definition.minimum == null ? "" : String(definition.minimum),
    maximumText: definition.maximum == null ? "" : String(definition.maximum),
    enumText: definition.enum ? JSON.stringify(definition.enum) : "" };
}

async function request(path: string, body?: unknown) {
  const response = await fetch(path, body === undefined ? { cache: "no-store" } : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data;
}

export function ParameterReview({ serviceId }: { serviceId: string }) {
  const [state, setState] = useState<State | null>(null);
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [rows, setRows] = useState<Row[]>([]);
  const [document, setDocument] = useState("");
  const [source, setSource] = useState("");
  const [operationId, setOperationId] = useState("");
  const [identity, setIdentity] = useState("");
  const [version, setVersion] = useState("");
  const [evidence, setEvidence] = useState("");
  const [confirmations, setConfirmations] = useState([false, false, false]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const base = `/api/services/${encodeURIComponent(serviceId)}`;

  async function load() {
    const [next, list] = await Promise.all([request(`${base}/parameter-onboarding`), request(`${base}/operation-contracts`)]);
    setState(next); setContracts(list); setRows((next.discovery?.candidates || []).map(editable));
  }
  useEffect(() => {
    let current = true;
    setState(null); setError(""); setNotice(""); setBusy(true);
    Promise.all([request(`${base}/parameter-onboarding`), request(`${base}/operation-contracts`)]).then(([next, list]) => {
      if (current) { setState(next); setContracts(list); setRows((next.discovery?.candidates || []).map(editable)); }
    }).catch(reason => { if (current) setError(reason.message); }).finally(() => { if (current) setBusy(false); });
    return () => { current = false; };
  }, [base]);

  function edit(index: number, change: Partial<Row>) {
    setRows(current => current.map((row, i) => i === index ? { ...row, ...change } : row));
    setConfirmations([false, false, false]); setNotice("");
  }
  async function discover() {
    setBusy(true); setError(""); setNotice("");
    try {
      const discovery = await request(`${base}/parameter-onboarding/discover`, {
        document: JSON.parse(document), source_reference: source, operation_id: operationId || null,
      }) as Discovery;
      setState(current => current ? { ...current, discovery } : current);
      setRows(discovery.candidates.map(editable)); setConfirmations([false, false, false]);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Discovery failed; existing definitions are unchanged."); }
    finally { setBusy(false); }
  }
  async function save() {
    if (!state?.discovery) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const parameters = rows.filter(row => row.selected).map(row => {
        const definition: Definition = { type: row.definition.type, title: row.definition.title, description: row.definition.description, required: row.definition.required };
        if (row.definition.unit) definition.unit = row.definition.unit;
        if (row.defaultText.trim()) definition.default = JSON.parse(row.defaultText);
        if (row.enumText.trim()) definition.enum = JSON.parse(row.enumText);
        if (row.minimumText.trim()) { definition.minimum = Number(row.minimumText); if (!Number.isFinite(definition.minimum)) throw new Error(`${row.name}: minimum must be a number`); }
        if (row.maximumText.trim()) { definition.maximum = Number(row.maximumText); if (!Number.isFinite(definition.maximum)) throw new Error(`${row.name}: maximum must be a number`); }
        return { name: row.name, source_pointer: row.source_pointer, definition, algorithm_mapping: row.mapping };
      });
      await request(`${base}/parameter-onboarding/review`, { discovery_revision: state.discovery.revision,
        operation_identity: identity, contract_version: version, parameters,
        runtime_support_confirmed: confirmations[0], normal_configuration_tested: confirmations[1],
        invalid_configuration_tested: confirmations[2], evidence_reference: evidence });
      await load(); setConfirmations([false, false, false]);
      setNotice("Reviewed settings saved as a draft. Publish this version after service approval to make it available in Builder.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Review could not be saved; your edits are retained."); }
    finally { setBusy(false); }
  }
  async function activate(contractId: string) {
    setBusy(true); setError(""); setNotice("");
    try {
      await request(`/api/operation-contracts/${encodeURIComponent(contractId)}/activate`, {});
      await load(); setNotice("Settings published. They are available in the existing Builder instance controls. Saved designs retain their version pins.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Publication failed."); }
    finally { setBusy(false); }
  }

  return <section aria-label="Provider parameter review" style={{ borderTop: "1px solid #ddd8f4", marginTop: 20, paddingTop: 20 }}>
    <h2>Adjustable service settings</h2>
    <p>Review the settings for <strong>{state?.operation_name || serviceId}</strong>. Discovery suggests candidates; the provider confirms meaning, limits and actual runtime support.</p>
    {error && <p role="alert" style={{ color: "#991b1b", overflowWrap: "anywhere" }}>{error}</p>}
    {notice && <p role="status">{notice}</p>}
    <fieldset disabled={busy || !state} style={{ border: 0, padding: 0 }}>
      <details open={!state?.discovery}>
        <summary>Supply an interface description</summary>
        <p>Use a JSON Schema for this operation’s settings, or an OpenAPI JSON document with a request body. Complex constraints, protobuf and prose need a supported description from the provider. No repository code is executed.</p>
        <label style={label}>Interface description file<input type="file" accept=".json,application/json" onChange={async event => {
          const file = event.target.files?.[0]; if (!file) return;
          if (file.size > 256000) { setError("Choose a JSON description under 256 KB."); return; }
          setDocument(await file.text()); setSource(file.name); setError("");
        }} /></label>
        <label style={label}>JSON description<textarea value={document} onChange={event => setDocument(event.target.value)} rows={7} style={input} /></label>
        <label style={label}>Source reference and revision<input value={source} onChange={event => setSource(event.target.value)} style={input} /></label>
        <label style={label}>OpenAPI operationId (when different from the registered name)<input value={operationId} onChange={event => setOperationId(event.target.value)} style={input} /></label>
        <button type="button" onClick={discover} disabled={!document.trim() || !source.trim()}>Discover candidate settings</button>
      </details>
      {state?.discovery && <>
        <p>Source: {state.discovery.source_reference}</p>
        <div style={{ overflowX: "auto" }}><table style={{ width: "100%", textAlign: "left" }}>
          <thead><tr><th>Expose</th><th>Candidate / source</th><th>Classification</th></tr></thead>
          <tbody>{rows.map((row, index) => <tr key={row.source_pointer}>
            <td><input type="checkbox" aria-label={`Expose ${row.name}`} checked={row.selected} disabled={!row.supported} onChange={event => edit(index, { selected: event.target.checked })} /></td>
            <td style={{ overflowWrap: "anywhere" }}><strong>{row.name}</strong><br /><small>{row.source_pointer}</small></td>
            <td>{row.classification.replaceAll("_", " ")}{row.reason && <p>{row.reason}</p>}</td>
          </tr>)}</tbody>
        </table></div>
        {rows.filter(row => row.selected).map(row => {
          const index = rows.indexOf(row);
          const update = (change: Partial<Definition>) => edit(index, { definition: { ...row.definition, ...change } });
          return <fieldset key={row.name} style={{ border: "1px solid #ddd8f4", margin: "16px 0", borderRadius: 10 }}>
            <legend>{row.name}</legend>
            <label style={label}>Label<input value={row.definition.title} onChange={event => update({ title: event.target.value })} style={input} /></label>
            <label style={label}>Meaning<textarea value={row.definition.description} onChange={event => update({ description: event.target.value })} style={input} /></label>
            <label style={label}>Type<select value={row.definition.type} onChange={event => update({ type: event.target.value as Definition["type"] })} style={input}>{["integer", "number", "boolean", "string"].map(type => <option key={type}>{type}</option>)}</select></label>
            <label style={label}>Units (optional)<input value={row.definition.unit || ""} onChange={event => update({ unit: event.target.value })} style={input} /></label>
            <label><input type="checkbox" checked={row.definition.required === true} onChange={event => update({ required: event.target.checked })} /> Required</label>
            <label style={label}>Default as JSON (blank means no default)<input value={row.defaultText} onChange={event => edit(index, { defaultText: event.target.value })} style={input} /></label>
            <label style={label}>Minimum (optional)<input type="number" value={row.minimumText} onChange={event => edit(index, { minimumText: event.target.value })} style={input} /></label>
            <label style={label}>Maximum (optional)<input type="number" value={row.maximumText} onChange={event => edit(index, { maximumText: event.target.value })} style={input} /></label>
            <label style={label}>Allowed values as a JSON array (optional; required for strings)<input value={row.enumText} onChange={event => edit(index, { enumText: event.target.value })} style={input} /></label>
            <p>Delivered as <code>configuration.parameters.{row.name}</code>.</p>
            <label style={label}>How the runtime passes this value to the algorithm<input value={row.mapping} onChange={event => edit(index, { mapping: event.target.value })} style={input} /></label>
          </fieldset>;
        })}
        <label style={label}>Canonical operation URI or URN<input value={identity} onChange={event => { setIdentity(event.target.value); setConfirmations([false, false, false]); }} style={input} /></label>
        <label style={label}>New contract version<input placeholder="Semantic version, for example 1.0.0" value={version} onChange={event => { setVersion(event.target.value); setConfirmations([false, false, false]); }} style={input} /></label>
        <label style={label}>Provider runtime test evidence reference<input value={evidence} onChange={event => { setEvidence(event.target.value); setConfirmations([false, false, false]); }} style={input} /></label>
        {["I confirm this runtime accepts the configuration envelope and consumes each selected value in the algorithm.", "I have tested a normal configuration using this runtime and these definitions.", "I have tested that this runtime rejects an invalid configuration."].map((text, index) => <label key={text} style={{ display: "block", margin: "10px 0" }}><input type="checkbox" checked={confirmations[index]} onChange={event => setConfirmations(current => current.map((value, i) => i === index ? event.target.checked : value))} /> {text}</label>)}
        {state.interface_type !== "control" && <p role="alert">This interface needs a verified configuration adapter. Discovery can be reviewed, but this connector cannot publish its settings yet.</p>}
        <button type="button" onClick={save} disabled={state.interface_type !== "control" || !rows.some(row => row.selected) || !confirmations.every(Boolean) || !identity.trim() || !version.trim() || !evidence.trim()}>Save reviewed settings as draft</button>
      </>}
      {contracts.filter(contract => state?.reviews[contract.id]).map(contract => <article key={contract.id} style={{ borderTop: "1px solid #ddd", marginTop: 16 }}>
        <h3>Version {contract.contract_version} · {contract.status}</h3>
        <p>{Object.values(contract.definition.execution_parameters?.properties || {}).map(spec => spec.title).join(", ")}</p>
        <p>Provider evidence: {state?.reviews[contract.id].evidence_reference}</p>
        <details><summary>Review saved definitions and runtime mappings</summary>
          {Object.entries(contract.definition.execution_parameters?.properties || {}).map(([name, spec]) => <div key={name}>
            <h4>{spec.title}{spec.unit ? ` (${spec.unit})` : ""}</h4>
            <p>{spec.description}</p>
            <p>{name} · {spec.type} · {spec.required ? "Required" : "Optional"} · Default: {Object.hasOwn(spec, "default") ? JSON.stringify(spec.default) : "None declared"}</p>
            <p>Minimum: {spec.minimum ?? "Not declared"} · Maximum: {spec.maximum ?? "Not declared"}{spec.enum ? ` · Choices: ${JSON.stringify(spec.enum)}` : ""}</p>
            <p>{state?.reviews[contract.id].mappings?.[name]?.transport_path} → {state?.reviews[contract.id].mappings?.[name]?.algorithm_mapping}</p>
          </div>)}
        </details>
        {contract.status === "draft" && <>
          <p>Publication requires administrator approval of the service. It publishes this saved version.</p>
          <button type="button" disabled={!["approved", "validated"].includes(state?.service_status || "")} onClick={() => activate(contract.id)}>Publish version {contract.contract_version}</button>
        </>}
      </article>)}
    </fieldset>
    {busy && <p role="status">Updating settings…</p>}
  </section>;
}

const label: CSSProperties = { display: "grid", gap: 5, margin: "12px 0", fontWeight: 600 };
const input: CSSProperties = { width: "100%", padding: 9, borderRadius: 8, border: "1px solid #cbd5e1" };
