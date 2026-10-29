"use client";

import { useEffect, useState } from "react";

export type InstanceConfiguration = { contract_id: string; contract_version: string; parameters: Record<string, unknown> };
type Parameter = { type: "integer" | "number" | "boolean" | "string"; title: string; description: string; default?: unknown; minimum?: number; maximum?: number; enum?: unknown[] };
type Contract = { id: string; contract_version: string; definition: { execution_parameters?: { properties: Record<string, Parameter> } } };

export default function InstanceParameters({ instanceId, serviceId, configuration, onChange, onCopy, onReady }: {
  instanceId: string; serviceId: string; configuration?: InstanceConfiguration;
  onChange: (value: InstanceConfiguration | undefined) => void; onCopy: () => void; onReady?: () => void;
}) {
  const [contract, setContract] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setContract(null); setError(""); setLoading(true);
    fetch(`/api/services/${serviceId}/operation-contract-resolution`).then(async response => {
      if (!response.ok) throw new Error("Parameter definitions are unavailable. Reload to try again.");
      const result = await response.json();
      if (active) setContract(result.contract);
    }).catch(reason => { if (active) setError(reason.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [serviceId]);
  useEffect(() => { if (!loading) onReady?.(); }, [loading, onReady]);
  const properties = contract?.definition.execution_parameters?.properties;
  const incompatible = configuration && contract && (configuration.contract_id !== contract.id || configuration.contract_version !== contract.contract_version);
  function update(name: string, value: unknown) {
    if (!contract) return;
    onChange({ contract_id: contract.id, contract_version: contract.contract_version,
      parameters: { ...(configuration?.parameters || {}), [name]: value } });
  }
  return <section aria-label="Instance settings" style={{ borderTop: "1px solid #ddd", paddingTop: 14 }}>
    <h3>Instance settings</h3>
    {error && <p role="alert">{error}</p>}
    {incompatible && <p role="alert">The saved contract changed. Review the current settings and select Use current defaults before saving.</p>}
    {loading ? <p>Loading settings…</p> : error ? null : properties ? <>
      <p>Edit settings, then save and validate the design. Defaults apply to omitted values.</p>
      {!configuration || incompatible ? <button type="button" onClick={() => onChange({ contract_id: contract!.id, contract_version: contract!.contract_version, parameters: {} })}>Use current defaults</button> : <>
        {Object.entries(properties).map(([name, spec]) => {
          const value = configuration.parameters[name] ?? spec.default ?? "";
          return <div key={name} style={{ display: "grid", gap: 5, margin: "12px 0" }}>
            <label htmlFor={`setting-${instanceId}-${name}`}><strong>{spec.title}</strong></label>
            {spec.enum ? <select id={`setting-${instanceId}-${name}`} aria-label={spec.title} value={JSON.stringify(value)} onChange={event => update(name, JSON.parse(event.target.value))}>
              {value === "" && <option value={'""'}>Choose a value</option>}
              {spec.enum.map(option => <option key={JSON.stringify(option)} value={JSON.stringify(option)}>{String(option)}</option>)}
            </select> : spec.type === "boolean" ? <input id={`setting-${instanceId}-${name}`} aria-label={spec.title} type="checkbox" checked={value === true} onChange={event => update(name, event.target.checked)} /> :
              <input id={`setting-${instanceId}-${name}`} aria-label={spec.title} type="number" min={spec.minimum} max={spec.maximum} step={spec.type === "integer" ? 1 : "any"} value={String(value)} onChange={event => update(name, event.target.value === "" ? null : Number(event.target.value))} />}
            <details className="instance-setting-help"><summary>Setting help</summary><small>{spec.description}{spec.default != null ? ` Default: ${String(spec.default)}.` : ""}</small></details>
          </div>;
        })}
      </>}
    </> : <p>No editable execution parameters are published for this operation.</p>}
    <details className="instance-extra-actions"><summary>More step actions</summary>
    <button type="button" onClick={onCopy}>Copy instance with incoming connections</button>
    <p><small>The copy has independent settings. Connect its outputs on the canvas.</small></p>
    </details>
  </section>;
}
