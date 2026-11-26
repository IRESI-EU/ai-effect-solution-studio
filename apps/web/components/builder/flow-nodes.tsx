"use client";

import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { MapPin } from "lucide-react";
import type { ServiceIcon as ServiceIconKind, ServiceStage } from "../../lib/service-presentation";
import { ServiceIcon } from "./service-icon";

/** Display data the Builder attaches to a service node before rendering. */
export type ServiceNodeView = {
  title: string;
  version: string | null;
  nodeLabel: string | null;
  icon: ServiceIconKind;
  stage: ServiceStage;
  input: string | null;
  output: string;
  readiness: "ready" | "blocked" | null;
  deprecated: boolean;
  settingsCount: number;
};

export type ServiceFlowNode = Node<{ view: ServiceNodeView } & Record<string, unknown>, "service">;
export type TerminalFlowNode = Node<{ kind: "start" | "end" } & Record<string, unknown>, "terminal">;

export function ServiceNode({ data, selected }: NodeProps<ServiceFlowNode>) {
  const view = data.view;
  return (
    <div className={`flow-card flow-card--${view.stage}${selected ? " is-selected" : ""}`}>
      <div className="flow-card__head">
        <span className={`flow-card__icon flow-card__icon--${view.stage}`}><ServiceIcon kind={view.icon} size={16} /></span>
        <span className="flow-card__title" title={view.title}>{view.title}</span>
        {view.readiness && (
          <span className={`flow-card__status flow-card__status--${view.readiness}`}>
            <span aria-hidden="true" />{view.readiness === "ready" ? "Ready" : "Unavailable"}
          </span>
        )}
      </div>
      <div className="flow-card__meta">
        {view.version && <span className="flow-card__version">v{view.version.replace(/^v/i, "")}</span>}
        {view.nodeLabel && <span className="flow-card__node"><MapPin size={10} aria-hidden="true" />{view.nodeLabel}</span>}
        {view.deprecated && <span className="flow-card__deprecated">Deprecated</span>}
        {view.settingsCount > 0 && <span className="flow-card__settings">{view.settingsCount} setting{view.settingsCount === 1 ? "" : "s"}</span>}
      </div>
      <div className="flow-card__ports">
        <div className="flow-card__port flow-card__port--in">
          {view.input && (
            <>
              <Handle type="target" position={Position.Left} />
              <span>{view.input}</span>
            </>
          )}
          {!view.input && <Handle type="target" position={Position.Left} />}
        </div>
        <div className="flow-card__port flow-card__port--out">
          <span>{view.output}</span>
          <Handle type="source" position={Position.Right} />
        </div>
      </div>
    </div>
  );
}

export function TerminalNode({ data }: NodeProps<TerminalFlowNode>) {
  const start = data.kind === "start";
  return (
    <div className={`flow-terminal${start ? " flow-terminal--start" : " flow-terminal--end"}`}>
      {!start && <Handle type="target" position={Position.Left} />}
      <span>{start ? "Start" : "Results"}</span>
      {start && <Handle type="source" position={Position.Right} />}
    </div>
  );
}

export const builderNodeTypes = { service: ServiceNode, terminal: TerminalNode };
