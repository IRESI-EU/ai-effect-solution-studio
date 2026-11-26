"use client";

import { ChevronRight, GripVertical, MapPin, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { serviceIcon, serviceStage, serviceText, type ServiceStage } from "../../lib/service-presentation";
import { nodeLabels, type NodeCode } from "../auth-context";
import { ServiceIcon } from "./service-icon";

export const SERVICE_DRAG_TYPE = "application/x-ai-effect-service";

export type PaletteService = {
  id: string;
  name: string;
  provider: string;
  category: string;
  version: string;
  description?: string | null;
  input_type: string;
  output_type: string;
  operation_name?: string;
  owner_node?: string | null;
  lifecycle_status?: string | null;
  interface_contract?: Record<string, unknown> | null;
};

const GROUPS: { stage: ServiceStage; title: string; hint: string }[] = [
  { stage: "start", title: "Start with", hint: "Data and configuration" },
  { stage: "middle", title: "Process and model", hint: "Prepare, simulate and train" },
  { stage: "finish", title: "Finish with", hint: "Results, drawings and reports" },
];

export function nodeLabelOf(code?: string | null) {
  return code && code in nodeLabels ? nodeLabels[code as NodeCode] : null;
}

export function displayVersion(version?: string | null) {
  const v = (version || "").trim();
  return v && v.toLowerCase() !== "latest" ? v : null;
}

export function ServicePalette<S extends PaletteService>({
  services,
  inUse,
  onAdd,
}: {
  services: S[];
  inUse: Set<string>;
  onAdd: (service: S) => void;
}) {
  const [query, setQuery] = useState("");
  const [showOther, setShowOther] = useState(false);

  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const visible = services.filter((service) => {
      if (!q) return true;
      const text = serviceText(service);
      return [text.title, text.purpose, service.provider, service.category, nodeLabelOf(service.owner_node) || ""]
        .join(" ").toLowerCase().includes(q);
    });
    const byStage: Record<ServiceStage, S[]> = { start: [], middle: [], finish: [], other: [] };
    visible.forEach((service) => byStage[serviceStage(service, services)].push(service));
    (Object.keys(byStage) as ServiceStage[]).forEach((stage) =>
      byStage[stage].sort((a, b) => serviceText(a).title.localeCompare(serviceText(b).title)),
    );
    return { byStage, count: visible.length };
  }, [services, query]);

  function card(service: S) {
    const text = serviceText(service);
    const used = inUse.has(service.id);
    const deprecated = service.lifecycle_status === "deprecated";
    const version = displayVersion(service.version);
    const node = nodeLabelOf(service.owner_node);
    const stage = serviceStage(service, services);
    return (
      <button
        type="button"
        key={service.id}
        className={`palette-card${used ? " is-in-use" : ""}`}
        draggable
        onDragStart={(event) => {
          event.dataTransfer.setData(SERVICE_DRAG_TYPE, service.id);
          event.dataTransfer.effectAllowed = "copy";
        }}
        onClick={() => onAdd(service)}
        title={`Drag onto the canvas, or click to add ${text.title}`}
      >
        <span className={`palette-card__icon flow-card__icon--${stage}`}><ServiceIcon kind={serviceIcon(service)} /></span>
        <span className="palette-card__body">
          <span className="palette-card__top">
            <span className="palette-card__title">{text.title}</span>
            {used && <span className="palette-card__inuse">In use</span>}
          </span>
          {version && <span className="palette-card__version">v{version.replace(/^v/i, "")}</span>}
          <span className="palette-card__purpose">{text.purpose}</span>
          <span className="palette-card__tags">
            {node && <span className="palette-card__node"><MapPin size={11} aria-hidden="true" />{node}</span>}
            {deprecated && <span className="ae-badge ae-badge--warning">Deprecated</span>}
          </span>
        </span>
        <GripVertical className="palette-card__grip" size={16} aria-hidden="true" />
      </button>
    );
  }

  return (
    <>
      <label className="catalogue-search builder-palette__search">
        <Search size={16} aria-hidden="true" />
        <input className="ae-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search services" aria-label="Search services" />
      </label>
      <div className="builder-palette__list">
        {GROUPS.map(({ stage, title, hint }) =>
          grouped.byStage[stage].length ? (
            <section key={stage} className="palette-group" aria-label={title}>
              <h3 className="palette-group__title">{title} <span>{hint}</span></h3>
              {grouped.byStage[stage].map(card)}
            </section>
          ) : null,
        )}
        {grouped.byStage.other.length > 0 && (
          <section className="palette-group">
            <button type="button" className="palette-group__toggle" aria-expanded={showOther} onClick={() => setShowOther((open) => !open)}>
              <ChevronRight size={14} aria-hidden="true" style={{ transform: showOther ? "rotate(90deg)" : undefined }} />
              Other services ({grouped.byStage.other.length})
            </button>
            {showOther && (
              <>
                <p className="palette-group__note">These cannot be connected to other catalogue services yet.</p>
                {grouped.byStage.other.map(card)}
              </>
            )}
          </section>
        )}
        {grouped.count === 0 && <p className="builder-empty muted">No services match your search.</p>}
      </div>
    </>
  );
}
