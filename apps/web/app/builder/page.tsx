"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useSearchParams } from "next/navigation";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { roleLabels, useAuth, type UserRole } from "../../components/auth-context";
import { apiErrorMessage } from "../../lib/solution-design";
import { NodeSettingsPanel, settingsDefinitionOf, settingsErrors, type SettingsValues } from "../../components/node-settings";
import { DesignAssistant, type AssistantSuggestion, type ProposedWorkflow } from "../../components/design-assistant";
import { builderNodeTypes, type ServiceNodeView } from "../../components/builder/flow-nodes";
import { SERVICE_DRAG_TYPE, ServicePalette, displayVersion, nodeLabelOf } from "../../components/builder/service-palette";
import { WORKFLOW_OUTPUT, WORKFLOW_START, serviceIcon, servicePorts, serviceStage, serviceText } from "../../lib/service-presentation";
import Link from "next/link";
import { Check, CircleCheck, CircleX, Info as InfoIcon, MapPin, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen, Play, SlidersHorizontal, Sparkles, TriangleAlert } from "lucide-react";

type Service = {
  id: string;
  name: string;
  provider: string;
  category: string;
  version: string;
  input_type: string;
  output_type: string;
  trust_badge: string;
  lifecycle_status?: "active" | "deprecated" | "archived" | string | null;
  owner_node?: string | null;
  description?: string | null;

  container_name?: string;
  image?: string;
  proto_uri?: string;
  node_type?: string;
  operation_name?: string;
  input_message_name?: string;
  output_message_name?: string;
  internal_host?: string;
  internal_port?: string;

  repository_url?: string | null;
  repository_branch?: string | null;
  manifest_path?: string | null;
  interface_type?: string | null;
  orchestration_mode?: string | null;
  adapter_type?: string | null;
  health_path?: string | null;
  contract_uri?: string | null;
  interface_contract?: Record<string, unknown> | null;
};

type RuntimePreflightCheck = {
  node_id: string;
  service_id: string;
  service_name: string;
  runtime_url: string | null;
  runtime_management_mode: string;
  responsible_party: string;
  status: "ready" | "unavailable" | "misconfigured" | "ineligible" | "unknown";
  blocking: boolean;
  message: string;
  recommended_action: string;
  http_status: number | null;
};

type RuntimePreflightResult = {
  status: "ready" | "blocked";
  checked_at: string;
  summary: {
    total_services: number;
    ready: number;
    blocked: number;
    unavailable: number;
    misconfigured: number;
    ineligible: number;
    unknown: number;
    message: string;
  };
  checks: RuntimePreflightCheck[];
};

type SavedSolution = {
  id: string;
  name: string;
};

const API_BASE_URL = "/api";

const initialNodes: Node[] = [
  {
    id: "input",
    position: { x: 120, y: 180 },
    data: { label: "Workflow Input", node_kind: "workflow_input" },
    type: "input",
  },
  {
    id: "output",
    position: { x: 760, y: 180 },
    data: { label: "Workflow Output", node_kind: "workflow_output" },
    type: "output",
  },
];

export default function BuilderPage() {
  return (
    <Suspense fallback={<div className="page"><div className="card" style={{ padding: 28 }}>Loading workflow studio...</div></div>}>
      <BuilderContent />
    </Suspense>
  );
}

function BuilderContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const solutionId = searchParams.get("solutionId");
  const catalogueServiceId = searchParams.get("serviceId");

  const [services, setServices] = useState<Service[]>([]);
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [rightTab, setRightTab] = useState<"assistant" | "inspector" | "run">("assistant");
  // Side panels can be folded away so the canvas gets the width; remembered per browser.
  const [paletteOpen, setPaletteOpen] = useState(true);
  const [sideOpen, setSideOpen] = useState(true);
  useEffect(() => {
    try {
      setPaletteOpen(localStorage.getItem("builder.paletteOpen") !== "0");
      setSideOpen(localStorage.getItem("builder.sideOpen") !== "0");
    } catch { /* storage unavailable: keep both open */ }
  }, []);
  function togglePalette(open: boolean) {
    setPaletteOpen(open);
    try { localStorage.setItem("builder.paletteOpen", open ? "1" : "0"); } catch { /* ignore */ }
  }
  function toggleSide(open: boolean) {
    setSideOpen(open);
    try { localStorage.setItem("builder.sideOpen", open ? "1" : "0"); } catch { /* ignore */ }
  }
  useEffect(() => {
    const timer = setTimeout(() => flowRef.current?.fitView({ padding: 0.15, maxZoom: 1.1, duration: 200 }), 220);
    return () => clearTimeout(timer);
  }, [paletteOpen, sideOpen]);
  function openSideTab(tab: "assistant" | "inspector" | "run") {
    setRightTab(tab);
    toggleSide(true);
  }
  const [aiUndo, setAiUndo] = useState<{ nodes: Node[]; edges: Edge[] } | null>(null);
  const [canvasFitKey, setCanvasFitKey] = useState(0);
  const flowRef = useRef<ReactFlowInstance | null>(null);

  function canvasAsProposal() {
    const serviceNodes = nodes.filter((node) => Boolean(node.data?.service));
    if (serviceNodes.length === 0) return null;
    const ids = new Set(serviceNodes.map((node) => node.id));
    return {
      steps: serviceNodes.map((node) => ({
        ref: node.id,
        service_id: (node.data.service as Service).id,
        why: "",
        settings: (node.data?.settings as SettingsValues | undefined) || {},
      })),
      connections: edges
        .filter((edge) => ids.has(edge.source) && ids.has(edge.target))
        .map((edge) => ({ from_ref: edge.source, to_ref: edge.target })),
    };
  }

  function applyAiWorkflow(workflow: ProposedWorkflow) {
    setAiUndo({ nodes, edges });
    const depth: Record<string, number> = {};
    const incoming = new Map<string, string[]>();
    workflow.connections.forEach((c) => incoming.set(c.to_ref, [...(incoming.get(c.to_ref) || []), c.from_ref]));
    const depthOf = (ref: string, seen = new Set<string>()): number => {
      if (depth[ref] !== undefined) return depth[ref];
      if (seen.has(ref)) return 0;
      seen.add(ref);
      const parents = incoming.get(ref) || [];
      depth[ref] = parents.length ? Math.max(...parents.map((p) => depthOf(p, seen))) + 1 : 0;
      return depth[ref];
    };
    workflow.steps.forEach((step) => depthOf(step.ref));
    const rows: Record<number, number> = {};
    const stamp = Date.now();
    const idFor = (ref: string) => `service-ai-${ref}-${stamp}`;
    const serviceNodes: Node[] = workflow.steps.map((step) => {
      const service = services.find((candidate) => candidate.id === step.service_id);
      const d = depth[step.ref] || 0;
      const row = (rows[d] = (rows[d] ?? -1) + 1);
      return {
        id: idFor(step.ref),
        position: { x: 340 + d * 260, y: 120 + row * 130 },
        data: {
          node_kind: "service",
          label: service ? serviceText(service).title : step.service_name,
          service: service || { id: step.service_id, name: step.service_name },
          settings: step.settings && Object.keys(step.settings).length ? step.settings : undefined,
        },
      };
    });
    const maxDepth = Math.max(0, ...Object.values(depth));
    const startRefs = workflow.steps.filter((s) => !(incoming.get(s.ref) || []).length).map((s) => s.ref);
    const endRefs = workflow.steps.filter((s) => !workflow.connections.some((c) => c.from_ref === s.ref)).map((s) => s.ref);
    setNodes([
      { ...initialNodes[0], position: { x: 80, y: 150 } },
      ...serviceNodes,
      { ...initialNodes[1], position: { x: 340 + (maxDepth + 1) * 260, y: 150 } },
    ]);
    setEdges([
      ...startRefs.map((ref) => ({ id: `e-input-${idFor(ref)}`, source: "input", target: idFor(ref) })),
      ...workflow.connections.map((c) => ({ id: `e-${idFor(c.from_ref)}-${idFor(c.to_ref)}`, source: idFor(c.from_ref), target: idFor(c.to_ref) })),
      ...endRefs.map((ref) => ({ id: `e-${idFor(ref)}-output`, source: idFor(ref), target: "output" })),
    ]);
    setSelectedService(null);
    setSelectedNodeId(null);
    setCanvasFitKey((key) => key + 1);
    invalidateWorkflowResults();
  }

  function undoAiWorkflow() {
    if (!aiUndo) return;
    setNodes(aiUndo.nodes);
    setEdges(aiUndo.edges);
    setAiUndo(null);
    invalidateWorkflowResults();
  }

  function catalogueEntry(service: Service) {
    return services.find((candidate) => candidate.id === service.id) || service;
  }

  function isStartServiceNode(nodeId: string) {
    const serviceNodeIds = new Set(nodes.filter((node) => Boolean(node.data?.service)).map((node) => node.id));
    return !edges.some((edge) => edge.target === nodeId && serviceNodeIds.has(edge.source));
  }

  function updateNodeSettings(nodeId: string, values: SettingsValues) {
    setNodes((current) =>
      current.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, settings: values } } : node
      )
    );
    invalidateWorkflowResults();
  }
  const [validationResults, setValidationResults] = useState<string[]>([]);
  const [runtimePreflight, setRuntimePreflight] = useState<RuntimePreflightResult | null>(null);
  const [workflowDesignStatus, setWorkflowDesignStatus] = useState<"valid" | "invalid" | null>(null);
  const [savingSolution, setSavingSolution] = useState(false);
  const [preparingDeployment, setPreparingDeployment] = useState(false);
  const [deploymentConfirmationReady, setDeploymentConfirmationReady] = useState(false);
  const [solutionNeedsRevalidation, setSolutionNeedsRevalidation] = useState(false);
  const [deploymentResult, setDeploymentResult] = useState<any>(null);
  const [submittingToOrchestrator, setSubmittingToOrchestrator] = useState(false);
  const [currentSolutionId, setCurrentSolutionId] = useState<string | null>(null);
  const [solutionName, setSolutionName] = useState("Untitled AI-EFFECT Solution");
  const [runInputMode, setRunInputMode] = useState<"prompt" | "json">("prompt");
  const [runInput, setRunInput] = useState("");
  const [runInputError, setRunInputError] = useState("");
  const [runOverrides, setRunOverrides] = useState<Record<string, SettingsValues>>({});
  const [solutionLoadError, setSolutionLoadError] = useState("");
  const roleMode: UserRole = user?.role || "solution_designer";
  const workflowRevisionRef = useRef(0);
  const solutionSavePromiseRef = useRef<Promise<SavedSolution> | null>(null);
  const saveDraftInFlightRef = useRef(false);
  const prepareInFlightRef = useRef(false);
  const confirmInFlightRef = useRef(false);
  const catalogueServiceHandledRef = useRef<string | null>(null);
  const preparedSolutionIdRef = useRef<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const invalidateWorkflowResults = useCallback(() => {
    workflowRevisionRef.current += 1;
    setWorkflowDesignStatus(null);
    setValidationResults([]);
    setRuntimePreflight(null);
    setDeploymentResult(null);
    setDeploymentConfirmationReady(false);
    preparedSolutionIdRef.current = null;
    setSolutionNeedsRevalidation(true);
  }, []);

  const canvasServices = useMemo(
    () =>
      nodes
        .map((node) => node.data?.service as Service | undefined)
        .filter(Boolean) as Service[],
    [nodes]
  );

  const servicesOnCanvas = useMemo(() => new Set(canvasServices.map((service) => service.id)), [canvasServices]);

  const readinessByNode = useMemo(() => {
    const map = new Map<string, "ready" | "blocked">();
    runtimePreflight?.checks.forEach((check) => map.set(check.node_id, check.status === "ready" ? "ready" : "blocked"));
    return map;
  }, [runtimePreflight]);

  // Nodes as drawn: start/end pills and service cards. The saved format is unchanged.
  const displayNodes = useMemo(
    () =>
      nodes.map((node) => {
        const kind = node.data?.node_kind;
        if (node.id === "input" || node.id === "output" || kind === "workflow_input" || kind === "workflow_output") {
          const end = node.id === "output" || kind === "workflow_output";
          return { ...node, type: "terminal", data: { ...node.data, kind: end ? "end" : "start" } };
        }
        const raw = node.data?.service as Service | undefined;
        if (!raw) return node;
        const service = catalogueEntry(raw);
        const ports = servicePorts({ ...service, input_type: service.input_type || "", output_type: service.output_type || "" });
        const view: ServiceNodeView = {
          title: serviceText(service).title,
          version: displayVersion(service.version),
          nodeLabel: nodeLabelOf(service.owner_node),
          icon: serviceIcon(service),
          stage: serviceStage(service, services),
          input: ports.input,
          output: ports.output,
          readiness: readinessByNode.get(node.id) || null,
          deprecated: getLifecycleStatus(service) === "deprecated",
          settingsCount: Object.keys((node.data?.settings as SettingsValues | undefined) || {}).length,
        };
        return { ...node, type: "service", data: { ...node.data, view } };
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [nodes, services, readinessByNode]
  );

  const displayEdges = useMemo(() => {
    const byId = new Map(nodes.map((node) => [node.id, node]));
    return edges.map((edge) => {
      const source = byId.get(edge.source)?.data?.service as Service | undefined;
      const label = source ? servicePorts(catalogueEntry(source)).output : undefined;
      return { ...edge, type: "smoothstep", animated: true, label, className: "flow-edge" };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [edges, nodes, services]);

  function serviceOfNode(nodeId: string) {
    const node = nodes.find((candidate) => candidate.id === nodeId);
    return node?.data?.service ? catalogueEntry(node.data.service as Service) : null;
  }

  /** A link is allowed only where the data fits: output type of one equals input type of the next. */
  function canConnect(sourceId: string, targetId: string) {
    if (sourceId === targetId) return false;
    const source = serviceOfNode(sourceId);
    const target = serviceOfNode(targetId);
    if (!source && !target) return false;
    if (!source) return sourceId === "input" && target!.input_type === WORKFLOW_START;
    if (!target) return targetId === "output" && source.output_type === WORKFLOW_OUTPUT;
    return source.output_type === target.input_type;
  }

  function alternativesFor(service: Service) {
    return services.filter(
      (candidate) =>
        candidate.id !== service.id &&
        candidate.input_type === service.input_type &&
        candidate.output_type === service.output_type &&
        getLifecycleStatus(candidate) === "active"
    );
  }

  function nextStepsFor(service: Service) {
    return services.filter(
      (candidate) => candidate.input_type === service.output_type && getLifecycleStatus(candidate) === "active"
    );
  }

  function replaceService(nodeId: string, replacement: Service) {
    setNodes((current) =>
      current.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, service: replacement, label: serviceText(replacement).title, settings: undefined } }
          : node
      )
    );
    if (selectedNodeId === nodeId) setSelectedService(replacement);
    invalidateWorkflowResults();
  }

  function removeNode(nodeId: string) {
    setNodes((current) => current.filter((node) => node.id !== nodeId));
    setEdges((current) => current.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    if (selectedNodeId === nodeId) {
      setSelectedNodeId(null);
      setSelectedService(null);
    }
    invalidateWorkflowResults();
  }

  function addServiceAfter(nodeId: string, service: Service) {
    const from = nodes.find((node) => node.id === nodeId);
    const newId = `service-${service.id}-${Date.now()}`;
    const position = from ? { x: from.position.x + 280, y: from.position.y } : { x: 400, y: 200 };
    setNodes((current) => [
      ...current.map((node) =>
        node.id === "output" && node.position.x < position.x + 260 ? { ...node, position: { ...node.position, x: position.x + 300 } } : node
      ),
      { id: newId, position, data: { node_kind: "service", label: serviceText(service).title, service } },
    ]);
    setEdges((current) => {
      const kept = current.filter((edge) => !(edge.source === nodeId && edge.target === "output"));
      const added: Edge[] = [{ id: `e-${nodeId}-${newId}`, source: nodeId, target: newId }];
      if (service.output_type === WORKFLOW_OUTPUT) added.push({ id: `e-${newId}-output`, source: newId, target: "output" });
      return [...kept, ...added];
    });
    invalidateWorkflowResults();
  }

  const workflowStatus = useMemo(() => {
    const serviceNodes = nodes.filter((node) => node.data?.service);
    if (!serviceNodes.length) return null;
    const outgoing = new Map<string, string[]>();
    const incoming = new Map<string, string[]>();
    edges.forEach((edge) => {
      outgoing.set(edge.source, [...(outgoing.get(edge.source) || []), edge.target]);
      incoming.set(edge.target, [...(incoming.get(edge.target) || []), edge.source]);
    });
    const fromStart = collectReachable(["input"], outgoing);
    const toEnd = collectReachable(["output"], incoming);
    const complete = serviceNodes.every((node) => fromStart.has(node.id) && toEnd.has(node.id));
    const where = Array.from(
      new Set(serviceNodes.map((node) => nodeLabelOf(catalogueEntry(node.data.service as Service).owner_node)).filter(Boolean))
    ) as string[];
    return { complete, where };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges, services]);

  // Next steps offered under Design with AI answers. All of them act on the canvas
  // directly (no AI request), using only what the catalogue says fits.
  function buildSuggestions(): AssistantSuggestion[] {
    const serviceNodes = nodes.filter((node) => node.data?.service);
    if (!serviceNodes.length) return [];
    const found: AssistantSuggestion[] = [];

    for (const node of serviceNodes) {
      const service = catalogueEntry(node.data.service as Service);
      const continues = edges.some((edge) => edge.source === node.id && edge.target !== "output");
      if (continues || service.output_type === WORKFLOW_OUTPUT) continue;
      const next = nextStepsFor(service).filter((candidate) => !servicesOnCanvas.has(candidate.id))[0];
      if (!next) continue;
      const title = serviceText(next).title;
      found.push({
        id: `add-${node.id}-${next.id}`,
        label: `Add ${title}`,
        act: () => {
          addServiceAfter(node.id, next);
          return `Added ${title} after ${serviceText(service).title} and connected it: it takes the ${servicePorts(service).output} as input.`;
        },
      });
      break;
    }

    for (const node of serviceNodes) {
      const service = catalogueEntry(node.data.service as Service);
      const alternative = alternativesFor(service)[0];
      if (!alternative) continue;
      const from = serviceText(service).title;
      const to = serviceText(alternative).title;
      const where = nodeLabelOf(alternative.owner_node);
      found.push({
        id: `swap-${node.id}-${alternative.id}`,
        label: `Use ${to}${where ? ` (${where})` : ""} instead`,
        act: () => {
          replaceService(node.id, alternative);
          return `Swapped in ${to}${where ? ` from the ${where}` : ""}. It takes and produces the same data as ${from}, so all connections are kept.`;
        },
      });
      break;
    }

    for (const node of serviceNodes) {
      const service = catalogueEntry(node.data.service as Service);
      const definition = settingsDefinitionOf(service);
      if (!definition) continue;
      const current = (node.data?.settings as SettingsValues | undefined) || {};
      const entry = Object.entries(definition.schema.properties).find(
        ([, prop]) => prop.type === "boolean" || Array.isArray((prop as { enum?: unknown[] }).enum)
      );
      if (!entry) continue;
      const [name, prop] = entry;
      const title = (prop.title || name).toLowerCase();
      const value = name in current ? current[name] : prop.default;
      let next: unknown;
      let label: string;
      if (prop.type === "boolean") {
        next = !value;
        label = `${next ? "Turn on" : "Turn off"} ${title}`;
      } else {
        const options = (prop as { enum?: unknown[] }).enum || [];
        next = options[(options.indexOf(value) + 1) % options.length];
        label = `Set ${title} to ${String(next)}`;
      }
      const stepTitle = serviceText(service).title;
      found.push({
        id: `set-${node.id}-${name}-${String(next)}`,
        label,
        act: () => {
          updateNodeSettings(node.id, { ...current, [name]: next });
          return `Set ${prop.title || name} to ${String(next)} on ${stepTitle}. You can change it any time under Details.`;
        },
      });
      break;
    }

    found.push({ id: "run", label: "Check and run it", act: () => { openSideTab("run"); return null; } });
    return found.slice(0, 3);
  }
  const suggestions = buildSuggestions();

  const canvasRef = useRef<HTMLElement | null>(null);
  const [nodeMenu, setNodeMenu] = useState<{ nodeId: string; x: number; y: number } | null>(null);
  useEffect(() => {
    if (!nodeMenu) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") setNodeMenu(null); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [nodeMenu]);

  // Open Details on the first step that has adjustable settings (follow-up from Design with AI).
  function showFirstAdjustableStep() {
    const node = nodes.find((n) => n.data?.service && settingsDefinitionOf(catalogueEntry(n.data.service as Service)));
    if (!node) {
      openSideTab("inspector");
      return;
    }
    setSelectedService(node.data.service as Service);
    setSelectedNodeId(node.id);
    openSideTab("inspector");
  }

  const deprecatedCanvasServices = useMemo(
    () => canvasServices.filter((service) => getLifecycleStatus(service) === "deprecated"),
    [canvasServices]
  );

  const deprecatedAvailableCount = useMemo(
    () => services.filter((service) => getLifecycleStatus(service) === "deprecated").length,
    [services]
  );


  useEffect(() => {
    fetch(`${API_BASE_URL}/services`)
      .then((res) => res.json())
      .then(setServices)
      .catch(() => setServices([]));
  }, []);

  useEffect(() => {
    async function loadSolution() {
      if (!solutionId) return;
      setSolutionLoadError("");
      try {
        const res = await fetch(`${API_BASE_URL}/solutions/${solutionId}`);
        const body = await res.json().catch(() => null);
        if (!res.ok) {
          throw new Error(apiErrorMessage(body, `Could not load this solution (HTTP ${res.status}).`));
        }
        setCurrentSolutionId(body.id);
        setSolutionName(body.name);
        setNodes(body.nodes || initialNodes);
        setEdges(body.edges || []);
      } catch (error) {
        setSolutionLoadError(error instanceof Error ? error.message : "Could not load this solution.");
      }
    }

    loadSolution();
  }, [solutionId, setNodes, setEdges]);

  useEffect(() => {
    if (!catalogueServiceId || solutionId || services.length === 0) return;
    if (catalogueServiceHandledRef.current === catalogueServiceId) return;

    const requestedService = services.find(
      (service) => service.id === catalogueServiceId
    );
    if (!requestedService) return;

    catalogueServiceHandledRef.current = catalogueServiceId;
    addServiceToCanvas(requestedService);
    setSelectedService(requestedService);
  }, [catalogueServiceId, services, solutionId]);

  function handleNodesChange(changes: NodeChange<Node>[]) {
    onNodesChange(changes);
    if (changes.some((change) => change.type !== "select" && change.type !== "dimensions")) {
      invalidateWorkflowResults();
    }
  }

  function handleEdgesChange(changes: EdgeChange<Edge>[]) {
    onEdgesChange(changes);
    if (changes.some((change) => change.type !== "select")) {
      invalidateWorkflowResults();
    }
  }

  function onConnect(connection: Connection) {
    setEdges((eds) => addEdge(connection, eds));
    invalidateWorkflowResults();
  }

  const onEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      setEdges((eds) =>
        eds.filter((edge) => !deletedEdges.some((deleted) => deleted.id === edge.id))
      );
      invalidateWorkflowResults();
    },
    [invalidateWorkflowResults, setEdges]
  );

  function addServiceToCanvas(service: Service, at?: { x: number; y: number }) {
    const nodeId = `service-${service.id}-${Date.now()}`;
    const lifecycleStatus = getLifecycleStatus(service);
    const interfaceType = getInterfaceType(service);
    const orchestrationMode = getOrchestrationMode(service);

    setNodes((existing) => [
      ...existing,
      {
        id: nodeId,
        position: at || {
          x: 360 + Math.random() * 120,
          y: 120 + Math.random() * 180,
        },
        data: {
          node_kind: "service",
          label: serviceText(service).title + (lifecycleStatus === "deprecated" ? " (deprecated)" : ""),
          service,
        },
      },
    ]);
    invalidateWorkflowResults();
  }

  function buildWorkflowPayload(solutionIdForPayload: string | null = currentSolutionId) {
    const serviceNodes = nodes.filter((node) => Boolean(node.data?.service));
    const workflowNodes = serviceNodes.map((node) => {
      const service = node.data.service as Service;

      return {
        node_id: node.id,
        service_id: service.id,
        container_name: service.container_name || service.id,
        image: service.image,
        proto_uri: service.proto_uri,
        node_type: service.node_type || "MLModel",
        operation_name: service.operation_name || service.name,
        input_message_name: service.input_message_name || "Request",
        output_message_name: service.output_message_name || "Response",
        internal_host: service.internal_host || service.container_name,
        internal_port: service.internal_port || "8080",
        settings: (node.data?.settings as SettingsValues | undefined) || undefined,
      };
    });
    const validNodeIds = new Set(serviceNodes.map((node) => node.id));
    const workflowEdges = edges
      .filter((edge) => validNodeIds.has(edge.source) && validNodeIds.has(edge.target))
      .map((edge) => ({ source: edge.source, target: edge.target }));

    return {
      name: solutionName || "Solution Studio Workflow",
      solution_id: solutionIdForPayload,
      nodes: workflowNodes,
      edges: workflowEdges,
    };
  }

  function buildRunInput(): Record<string, unknown> | undefined {
    const text = runInput.trim();
    if (!text) return undefined;
    if (runInputMode === "prompt") return { prompt: text };
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      throw new Error("Run input must be valid JSON.");
    }
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error("Run input must be a JSON object.");
    }
    return parsed as Record<string, unknown>;
  }

  async function runRuntimePreflight(payload: ReturnType<typeof buildWorkflowPayload>) {
    const response = await fetch(`${API_BASE_URL}/workflows/runtime-preflight`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Deployment readiness check failed with HTTP ${response.status}.`);
    }

    const result = (await response.json()) as RuntimePreflightResult;
    return result;
  }

  function evaluateWorkflowDesign() {
    const blockers: string[] = [];
    const notices: string[] = [];
    const serviceNodes = nodes.filter((node) => Boolean(node.data?.service));
    const serviceNodeIds = new Set(serviceNodes.map((node) => node.id));
    const inputNodeIds = nodes
      .filter((node) => node.type === "input" || node.id === "input")
      .map((node) => node.id);
    const outputNodeIds = nodes
      .filter((node) => node.type === "output" || node.id === "output")
      .map((node) => node.id);
    const nodeIds = new Set(nodes.map((node) => node.id));
    const adjacency = new Map<string, string[]>();
    const reverseAdjacency = new Map<string, string[]>();

    edges.forEach((edge) => {
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) return;
      adjacency.set(edge.source, [...(adjacency.get(edge.source) || []), edge.target]);
      reverseAdjacency.set(edge.target, [...(reverseAdjacency.get(edge.target) || []), edge.source]);
    });

    if (serviceNodes.length === 0) blockers.push("Blocked: Add at least one service.");
    if (inputNodeIds.length === 0) blockers.push("Blocked: Add a workflow input node.");
    if (outputNodeIds.length === 0) blockers.push("Blocked: Add a workflow output node.");

    const reachableFromInput = collectReachable(inputNodeIds, adjacency);
    const canReachOutput = collectReachable(outputNodeIds, reverseAdjacency);
    if (serviceNodes.length > 0 && !serviceNodes.some((node) => reachableFromInput.has(node.id))) {
      blockers.push("Blocked: Connect the workflow input into the service workflow.");
    }
    if (serviceNodes.length > 0 && !serviceNodes.some((node) => canReachOutput.has(node.id))) {
      blockers.push("Blocked: Connect the service workflow to the workflow output.");
    }

    serviceNodes
      .filter((node) => !reachableFromInput.has(node.id) || !canReachOutput.has(node.id))
      .forEach((node) => {
        const service = node.data.service as Service;
        blockers.push(`Blocked: ${service.name} is not on a complete path from workflow input to output.`);
      });

    edges.forEach((edge) => {
      if (!serviceNodeIds.has(edge.source) || !serviceNodeIds.has(edge.target)) return;
      const sourceService = nodes.find((node) => node.id === edge.source)?.data.service as Service;
      const targetService = nodes.find((node) => node.id === edge.target)?.data.service as Service;

      if (sourceService.output_type === targetService.input_type) {
        notices.push(`Passed: ${sourceService.name} to ${targetService.name} types are compatible.`);
      } else {
        blockers.push(
          `Blocked: ${sourceService.name} to ${targetService.name} is incompatible.\nOutput: ${sourceService.output_type}\nInput: ${targetService.input_type}`
        );
      }
    });

    serviceNodes.forEach((node) => {
      const service = node.data.service as Service;
      const definition = settingsDefinitionOf(catalogueEntry(service));
      settingsErrors(definition, node.data?.settings as SettingsValues | undefined).forEach((error) => {
        blockers.push(`Blocked: ${service.name} settings: ${error}`);
      });
      if (definition?.channel === "run_input" && !isStartServiceNode(node.id)) {
        blockers.push(`Blocked: ${service.name} reads its settings from the workflow input, so it must be a first step.`);
      }
      if (getLifecycleStatus(service) === "deprecated") {
        notices.push(`Warning: ${service.name} is deprecated. Prefer an active replacement for new designs.`);
      }
      if (getOrchestrationMode(service) === "sidecar") {
        notices.push(`Note: ${service.name} uses the AI-EFFECT Control Interface compatibility path.`);
      }
    });

    const valid = blockers.length === 0;
    const issueLabel = blockers.length === 1 ? "issue" : "issues";
    return {
      valid,
      results: [
        valid ? "Passed: Workflow design is valid." : `Blocked: Workflow design has ${blockers.length} ${issueLabel}.`,
        ...blockers,
        ...notices,
      ],
    };
  }

  function validateWorkflow() {
    const result = evaluateWorkflowDesign();
    setWorkflowDesignStatus(result.valid ? "valid" : "invalid");
    setValidationResults(result.results);
    setRuntimePreflight(null);
    setDeploymentResult(null);
    setDeploymentConfirmationReady(false);
    preparedSolutionIdRef.current = null;
    setSolutionNeedsRevalidation(false);
    return result;
  }

  async function prepareDeployment() {
    if (prepareInFlightRef.current) return;
    prepareInFlightRef.current = true;

    const design = validateWorkflow();
    if (!design.valid) {
      prepareInFlightRef.current = false;
      return;
    }

    const workflowRevision = workflowRevisionRef.current;
    setPreparingDeployment(true);
    try {
      let savedSolution: SavedSolution;
      try {
        savedSolution = await persistSolution();
      } catch {
        if (workflowRevision === workflowRevisionRef.current) {
          setRuntimePreflight(null);
          setDeploymentConfirmationReady(false);
          setDeploymentResult({
            status: "failed",
            error: "The solution could not be saved. Deployment preparation was stopped.",
          });
        }
        return;
      }

      if (workflowRevision !== workflowRevisionRef.current) return;

      const preflight = await runRuntimePreflight(buildWorkflowPayload(savedSolution.id));
      if (workflowRevision !== workflowRevisionRef.current) return;
      setRuntimePreflight(preflight);
      setDeploymentConfirmationReady(preflight.status === "ready");
      preparedSolutionIdRef.current = preflight.status === "ready" ? savedSolution.id : null;
      if (preflight.status === "blocked") {
        setDeploymentResult({ status: "blocked", error: preflight.summary.message });
      }
    } catch (error) {
      if (workflowRevision !== workflowRevisionRef.current) return;
      setRuntimePreflight(null);
      setDeploymentConfirmationReady(false);
      setDeploymentResult({
        status: "failed",
        error: error instanceof Error ? error.message : "Deployment readiness could not be checked.",
      });
    } finally {
      setPreparingDeployment(false);
      prepareInFlightRef.current = false;
    }
  }

  function persistSolution(): Promise<SavedSolution> {
    if (solutionSavePromiseRef.current) return solutionSavePromiseRef.current;

    const payload = {
      name: solutionName || "Untitled AI-EFFECT Solution",
      description: "Saved workflow design from Builder",
      nodes,
      edges,
      status: "draft",
    };

    const url = currentSolutionId
      ? `${API_BASE_URL}/solutions/${currentSolutionId}`
      : `${API_BASE_URL}/solutions`;

    const request = (async () => {
      const res = await fetch(url, {
        method: currentSolutionId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error(`Solution save failed with HTTP ${res.status}.`);

      const saved = (await res.json()) as SavedSolution;
      if (!saved.id) throw new Error("The saved solution response did not include an ID.");

      setCurrentSolutionId(saved.id);
      setSolutionName(saved.name || payload.name);
      return saved;
    })();

    let sharedRequest: Promise<SavedSolution>;
    sharedRequest = request.finally(() => {
      if (solutionSavePromiseRef.current === sharedRequest) {
        solutionSavePromiseRef.current = null;
      }
    });
    solutionSavePromiseRef.current = sharedRequest;
    return sharedRequest;
  }

  async function saveSolution() {
    if (saveDraftInFlightRef.current) return;
    saveDraftInFlightRef.current = true;
    setSavingSolution(true);

    try {
      await persistSolution();
      alert("Solution saved successfully.");
    } catch {
      alert("Failed to save solution.");
    } finally {
      setSavingSolution(false);
      saveDraftInFlightRef.current = false;
    }
  }

  async function confirmDeployment() {
    const preparedSolutionId = preparedSolutionIdRef.current;
    if (
      confirmInFlightRef.current ||
      !deploymentConfirmationReady ||
      runtimePreflight?.status !== "ready" ||
      !preparedSolutionId
    ) {
      return;
    }

    let input: Record<string, unknown> | undefined;
    try {
      input = buildRunInput();
      if (input && new TextEncoder().encode(JSON.stringify(input)).length > 65536) {
        throw new Error("Run input must be at most 64 KiB of JSON.");
      }
      const overrideErrors = nodes.flatMap((node) => {
        const service = node.data?.service as Service | undefined;
        if (!service || !runOverrides[node.id]) return [];
        return settingsErrors(settingsDefinitionOf(catalogueEntry(service)), runOverrides[node.id]).map(
          (error) => `${service.name}: ${error}`
        );
      });
      if (overrideErrors.length) throw new Error(`Settings for this run: ${overrideErrors.join(" ")}`);
      setRunInputError("");
    } catch (error) {
      setRunInputError(error instanceof Error ? error.message : "Invalid run input.");
      return;
    }

    confirmInFlightRef.current = true;
    setSubmittingToOrchestrator(true);
    setDeploymentResult(null);

    try {
      const basePayload = buildWorkflowPayload(preparedSolutionId);
      const workflowPayload = {
        ...basePayload,
        // Per-run overrides sit on top of the saved settings and are not saved.
        nodes: basePayload.nodes.map((node) =>
          runOverrides[node.node_id] && Object.keys(runOverrides[node.node_id]).length
            ? { ...node, settings: { ...(node.settings || {}), ...runOverrides[node.node_id] } }
            : node
        ),
        ...(input === undefined ? {} : { run_input: input }),
      };
      const res = await fetch(`${API_BASE_URL}/workflows/submit-to-orchestrator`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(workflowPayload),
      });

      if (!res.ok) {
        const errorBody = await res.json().catch(() => null);
        const backendPreflight = errorBody?.detail?.preflight as RuntimePreflightResult | undefined;
        if (backendPreflight) {
          setRuntimePreflight(backendPreflight);
          setDeploymentConfirmationReady(false);
          preparedSolutionIdRef.current = null;
          setDeploymentResult({
            status: "blocked",
            error: errorBody?.detail?.message || "Deployment readiness changed and is now blocked.",
          });
          return;
        }
        setDeploymentResult({
          status: "failed",
          error:
            errorBody?.detail?.message ||
            errorBody?.detail ||
            `Deployment submission failed with HTTP ${res.status}.`,
        });
        return;
      }

      const data = await res.json();
      setDeploymentResult(data);
      setDeploymentConfirmationReady(false);

      if (data.workflow_id) {
        try {
          await fetch(`${API_BASE_URL}/deployments`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              workflow_id: data.workflow_id,
              solution_id: preparedSolutionId,
              name: solutionName || "Solution Studio Workflow",
              status: data.status || "submitted",
            }),
          });
        } catch (deploymentError) {
          console.warn("Deployment submitted, but its local record could not be saved.", deploymentError);
        }
      }
    } catch {
      setDeploymentResult({
        status: "failed",
        error: "The deployment service could not be reached. Try again when the platform is available.",
      });
    } finally {
      setSubmittingToOrchestrator(false);
      confirmInFlightRef.current = false;
    }
  }

  return (
    <div className="builder-page">
      {solutionLoadError && (
        <section className="card" style={{ padding: 18, marginBottom: 18, borderColor: "#fda29b", color: "#b42318" }}>
          <strong>Unable to load solution design.</strong> {solutionLoadError}
        </section>
      )}
      <header className="builder-header">
        <div className="builder-header__title">
          <input
            className="builder-title-input"
            value={solutionName}
            onChange={(event) => setSolutionName(event.target.value)}
            placeholder="Untitled solution"
            aria-label="Solution name"
          />
          <span className="builder-header__meta">
            {canvasServices.length} {canvasServices.length === 1 ? "service" : "services"} · {edges.length} {edges.length === 1 ? "connection" : "connections"}
          </span>
        </div>
        <div className="page-header__actions">
          <button className="ae-btn ae-btn--secondary" onClick={saveSolution} disabled={savingSolution || preparingDeployment}>
            {savingSolution ? "Saving..." : "Save"}
          </button>
          <button className="ae-btn ae-btn--secondary" onClick={() => { validateWorkflow(); openSideTab("run"); }}>Check design</button>
          <button className="ae-btn ae-btn--primary" onClick={() => { openSideTab("run"); prepareDeployment(); }} disabled={preparingDeployment || savingSolution}>
            {preparingDeployment ? "Preparing..." : "Prepare and deploy"}
          </button>
        </div>
      </header>

      {(solutionNeedsRevalidation || deprecatedCanvasServices.length > 0) && (
        <div className="builder-notices">
          {solutionNeedsRevalidation && (
            <div className="ae-alert" role="status"><InfoIcon size={20} aria-hidden="true" /><div>The solution changed. Check the design again before deploying.</div></div>
          )}
          {deprecatedCanvasServices.length > 0 && (
            <div className="ae-alert ae-alert--warning"><TriangleAlert size={20} aria-hidden="true" /><div>
              <span className="ae-alert__title">Uses deprecated services:</span> {deprecatedCanvasServices.map((service) => serviceText(service).title).join(", ")}. Prefer active replacements for new work.
            </div></div>
          )}
        </div>
      )}

      <div className={"builder-workbench" + (paletteOpen ? "" : " is-palette-closed") + (sideOpen ? "" : " is-side-closed")}>
        <aside className={"builder-pane builder-palette" + (paletteOpen ? "" : " is-collapsed")} aria-label="Services">
          <div className="builder-rail">
            <button type="button" className="builder-icon-btn" onClick={() => togglePalette(true)} aria-label="Show services" title="Show services">
              <PanelLeftOpen size={18} aria-hidden="true" />
            </button>
            <span className="builder-rail__label">Services</span>
          </div>
          <div className="builder-pane__head">
            <h2 className="builder-pane__title">Services</h2>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span className="builder-pane__count">{services.length}</span>
              <button type="button" className="builder-icon-btn builder-collapse-btn" onClick={() => togglePalette(false)} aria-label="Hide services" title="Hide services">
                <PanelLeftClose size={18} aria-hidden="true" />
              </button>
            </span>
          </div>
          <ServicePalette services={services} inUse={servicesOnCanvas} onAdd={(service) => addServiceToCanvas(service)} />
        </aside>

        <main className="builder-canvas" aria-label="Workflow canvas" ref={canvasRef}>
          <ReactFlow
            key={canvasFitKey}
            onInit={(instance) => { flowRef.current = instance; }}
            fitViewOptions={{ padding: 0.15, maxZoom: 1.1 }}
            nodes={displayNodes}
            edges={displayEdges}
            nodeTypes={builderNodeTypes}
            isValidConnection={(connection) => canConnect(connection.source, connection.target)}
            onDragOver={(event) => {
              if (event.dataTransfer.types.includes(SERVICE_DRAG_TYPE)) {
                event.preventDefault();
                event.dataTransfer.dropEffect = "copy";
              }
            }}
            onDrop={(event) => {
              const service = services.find((candidate) => candidate.id === event.dataTransfer.getData(SERVICE_DRAG_TYPE));
              if (!service || !flowRef.current) return;
              event.preventDefault();
              addServiceToCanvas(service, flowRef.current.screenToFlowPosition({ x: event.clientX - 90, y: event.clientY - 30 }));
            }}
            onNodeContextMenu={(event, node) => {
              if (!node.data?.service || !canvasRef.current) return;
              event.preventDefault();
              const box = canvasRef.current.getBoundingClientRect();
              setNodeMenu({ nodeId: node.id, x: Math.min(event.clientX - box.left, box.width - 250), y: Math.min(event.clientY - box.top, box.height - 220) });
            }}
            onPaneClick={() => setNodeMenu(null)}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={onConnect}
            onEdgesDelete={onEdgesDelete}
            deleteKeyCode={["Backspace", "Delete"]}
            onNodeClick={(_, node) => {
              setNodeMenu(null);
              const service = node.data?.service as Service | undefined;
              setSelectedService(service || null);
              setSelectedNodeId(service ? node.id : null);
              if (service) setRightTab("inspector");
            }}
            fitView
          >
            <Background gap={20} size={1} />
            <Controls showInteractive={false} />
            {canvasServices.length > 0 && <MiniMap pannable zoomable position="bottom-right" nodeStrokeWidth={2} ariaLabel="Overview of the workflow" />}
          </ReactFlow>
          {canvasServices.length === 0 && (
            <div className="builder-canvas__empty">
              <span className="builder-canvas__empty-mark" aria-hidden="true" />
              <h3>Start your solution</h3>
              <p>Describe your experiment to Design with AI, or drag services from the list onto the canvas.</p>
            </div>
          )}
          {workflowStatus && (
            <div className="canvas-status" aria-live="polite">
              {workflowStatus.where.length > 0 && (
                <span className="canvas-status__where">
                  <MapPin size={13} aria-hidden="true" />
                  {workflowStatus.where.length === 1
                    ? `Runs on the ${workflowStatus.where[0]}`
                    : `Runs on ${workflowStatus.where.length} nodes: ${workflowStatus.where.join(", ")}`}
                </span>
              )}
              <span className={`canvas-status__state${workflowStatus.complete ? " is-complete" : ""}`}>
                {workflowStatus.complete ? <>Workflow complete <Check size={14} aria-hidden="true" /></> : "Connect every step from Start to Results"}
              </span>
            </div>
          )}
          {nodeMenu && (() => {
            const service = serviceOfNode(nodeMenu.nodeId);
            if (!service) return null;
            const alternatives = alternativesFor(service).slice(0, 5);
            return (
              <div className="node-menu" role="menu" style={{ left: nodeMenu.x, top: nodeMenu.y }}>
                <div className="node-menu__title">{serviceText(service).title}</div>
                <button type="button" role="menuitem" onClick={() => {
                  setSelectedService(service);
                  setSelectedNodeId(nodeMenu.nodeId);
                  openSideTab("inspector");
                  setNodeMenu(null);
                }}>Details and settings</button>
                <div className="node-menu__label">Replace with</div>
                {alternatives.map((alternative) => (
                  <button key={alternative.id} type="button" role="menuitem" onClick={() => { replaceService(nodeMenu.nodeId, alternative); setNodeMenu(null); }}>
                    {serviceText(alternative).title}
                    {nodeLabelOf(alternative.owner_node) && <small>{nodeLabelOf(alternative.owner_node)}</small>}
                  </button>
                ))}
                {alternatives.length === 0 && <div className="node-menu__note">No other service takes and produces the same data.</div>}
                <button type="button" role="menuitem" className="node-menu__danger" onClick={() => { removeNode(nodeMenu.nodeId); setNodeMenu(null); }}>Remove from workflow</button>
              </div>
            );
          })()}
        </main>

        <aside className={"builder-pane builder-side" + (sideOpen ? "" : " is-collapsed")} aria-label="Solution panel">
          <div className="builder-rail">
            <button type="button" className="builder-icon-btn" onClick={() => toggleSide(true)} aria-label="Show panel" title="Show panel">
              <PanelRightOpen size={18} aria-hidden="true" />
            </button>
            <button type="button" className="builder-icon-btn" onClick={() => openSideTab("assistant")} aria-label="Design with AI" title="Design with AI"><Sparkles size={18} aria-hidden="true" /></button>
            <button type="button" className="builder-icon-btn" onClick={() => openSideTab("inspector")} aria-label="Details" title="Details"><SlidersHorizontal size={18} aria-hidden="true" /></button>
            <button type="button" className="builder-icon-btn" onClick={() => openSideTab("run")} aria-label="Run" title="Run"><Play size={18} aria-hidden="true" /></button>
          </div>
          <div className="builder-side__head">
            <div className="ae-tabs builder-side__tabs" role="tablist">
              {([["assistant", "Design with AI"], ["inspector", "Details"], ["run", "Run"]] as const).map(([tab, label]) => (
                <button key={tab} className="ae-tab" role="tab" aria-selected={rightTab === tab} onClick={() => setRightTab(tab)}>{label}</button>
              ))}
            </div>
            <button type="button" className="builder-icon-btn builder-collapse-btn" onClick={() => toggleSide(false)} aria-label="Hide panel" title="Hide panel">
              <PanelRightClose size={18} aria-hidden="true" />
            </button>
          </div>

          <div className="builder-side__body">
            <div hidden={rightTab !== "assistant"}>
              <DesignAssistant getCurrent={canvasAsProposal} onApply={applyAiWorkflow} onUndo={undoAiWorkflow} canUndo={Boolean(aiUndo)} onRun={() => openSideTab("run")} onShowSettings={showFirstAdjustableStep} suggestions={suggestions} />
            </div>

            {rightTab === "inspector" && !selectedService && (
              <div className="empty-state builder-empty-state">
                <h3>No service selected</h3>
                <p>Select a service on the canvas to see what it does and adjust its settings.</p>
              </div>
            )}

            {rightTab === "inspector" && selectedService && (
              <div className="builder-details">
                <div>
                  <div className="service-page__meta">
                    <span className="ae-service__node">{selectedService.provider}</span>
                    {getLifecycleStatus(selectedService) === "deprecated" && <span className="ae-badge ae-badge--warning">Deprecated</span>}
                  </div>
                  <h3 className="builder-details__title">{serviceText(catalogueEntry(selectedService)).title}</h3>
                  <p className="builder-details__purpose">{serviceText(catalogueEntry(selectedService)).purpose}</p>
                </div>
                {selectedNodeId && nodes.some((node) => node.id === selectedNodeId) && (
                  <NodeSettingsPanel
                    definition={settingsDefinitionOf(catalogueEntry(selectedService))}
                    values={nodes.find((node) => node.id === selectedNodeId)?.data?.settings as SettingsValues | undefined}
                    onChange={(values) => updateNodeSettings(selectedNodeId, values)}
                    isStartNode={isStartServiceNode(selectedNodeId)}
                  />
                )}
                <dl className="kv">
                  <dt>Needs</dt><dd>{serviceText(catalogueEntry(selectedService)).needs}</dd>
                  <dt>Produces</dt><dd>{serviceText(catalogueEntry(selectedService)).produces}</dd>
                </dl>
                <details className="details">
                  <summary>Technical details</summary>
                  <div className="details__body">
                    <dl className="kv">
                      <dt>Operation</dt><dd className="ae-mono">{selectedService.operation_name || selectedService.name}</dd>
                      <dt>Interface</dt><dd>{formatValue(getInterfaceType(selectedService))} · {formatValue(getOrchestrationMode(selectedService))}</dd>
                      <dt>Input</dt><dd className="ae-mono">{selectedService.input_type}</dd>
                      <dt>Output</dt><dd className="ae-mono">{selectedService.output_type}</dd>
                      <dt>Version</dt><dd>{selectedService.version}</dd>
                    </dl>
                  </div>
                </details>
                <Link href={"/catalogue/" + selectedService.id} className="ae-btn ae-btn--ghost">Open catalogue page</Link>
              </div>
            )}

            {rightTab === "run" && (
              <div className="builder-run">
                <section className="builder-run__section">
                  <div className="builder-run__step-head">
                    <span className={"builder-run__step" + (workflowDesignStatus === "valid" ? " is-done" : "")}>1</span>
                    <h3 className="builder-run__title">Check the design</h3>
                    <span className={"ae-badge " + (workflowDesignStatus === "valid" ? "ae-badge--success" : workflowDesignStatus === "invalid" ? "ae-badge--danger" : "")}>
                      {workflowDesignStatus === "invalid" ? "Needs attention" : workflowDesignStatus === "valid" ? "Valid" : "Not checked"}
                    </span>
                  </div>
                  <p className="muted builder-run__hint">Finds missing connections, incompatible steps and invalid settings.</p>
                  {validationResults.length > 0 && (
                    <ul className="builder-checks">
                      {validationResults.filter((result) => !result.startsWith("Passed")).map((result, index) => {
                        const tone = result.startsWith("Blocked") ? "danger" : result.startsWith("Warning") ? "warning" : "info";
                        return <li key={index} className={"builder-check builder-check--" + tone}>{result.replace(/^(Blocked|Passed|Warning|Note):\s*/, "")}</li>;
                      })}
                    </ul>
                  )}
                  <button className="ae-btn ae-btn--secondary builder-run__action" onClick={() => validateWorkflow()}>Check design</button>
                </section>

                <section className="builder-run__section">
                  <div className="builder-run__step-head">
                    <span className={"builder-run__step" + (runtimePreflight?.status === "ready" ? " is-done" : "")}>2</span>
                    <h3 className="builder-run__title">Check the services</h3>
                    <span className={"ae-badge " + (runtimePreflight?.status === "ready" ? "ae-badge--success" : runtimePreflight?.status === "blocked" ? "ae-badge--danger" : "")}>
                      {runtimePreflight?.status === "ready" ? "All ready" : runtimePreflight?.status === "blocked" ? (runtimePreflight?.summary.blocked || 0) + " blocked" : "Not checked"}
                    </span>
                  </div>
                  <p className="muted builder-run__hint">Saves the solution and checks that every node service is reachable and allowed to run.</p>
                  {runtimePreflight?.status === "blocked" && (
                    <ul className="builder-checks">
                      {runtimePreflight.checks.filter((check) => check.blocking).map((check) => (
                        <li key={check.node_id} className="builder-check builder-check--danger">
                          <strong>{serviceText(catalogueEntry({ id: check.service_id, name: check.service_name } as Service)).title}:</strong> {check.message} {check.recommended_action}
                        </li>
                      ))}
                    </ul>
                  )}
                  <button className="ae-btn ae-btn--secondary builder-run__action" onClick={prepareDeployment} disabled={preparingDeployment || savingSolution}>
                    {preparingDeployment ? "Checking services..." : runtimePreflight ? "Check again" : "Check services"}
                  </button>
                </section>

                <section className="builder-run__section">
                  <div className="builder-run__step-head">
                    <span className="builder-run__step">3</span>
                    <h3 className="builder-run__title">Deploy</h3>
                  </div>
                  <div className="ae-field">
                    <label className="ae-field__label" htmlFor="run-input">Run input <span className="ae-field__unit">(optional)</span></label>
                    <select id="run-input-mode" className="ae-select" value={runInputMode} onChange={(event) => { setRunInputMode(event.target.value as "prompt" | "json"); setRunInputError(""); }} aria-label="Run input type">
                      <option value="prompt">Text prompt</option>
                      <option value="json">JSON object</option>
                    </select>
                    <textarea id="run-input" className="ae-textarea" value={runInput} onChange={(event) => { setRunInput(event.target.value); setRunInputError(""); }} rows={3} placeholder={runInputMode === "prompt" ? "Only needed if the first step expects a prompt" : '{"prompt": "...", "option": true}'} />
                    <span className="ae-field__help">Sent to the first step. Most workflows can leave this empty.</span>
                  </div>
                  {nodes.some((node) => node.data?.service && settingsDefinitionOf(catalogueEntry(node.data.service as Service))) && (
                    <details className="details">
                      <summary>
                        Settings for this run only{Object.values(runOverrides).some((values) => Object.keys(values).length) ? " · changed" : ""}
                      </summary>
                      <div className="details__body">
                        <p className="muted" style={{ margin: 0 }}>Try different values once without changing the saved solution.</p>
                        {nodes
                          .filter((node) => node.data?.service && settingsDefinitionOf(catalogueEntry(node.data.service as Service)))
                          .map((node) => {
                            const service = node.data.service as Service;
                            return (
                              <NodeSettingsPanel
                                key={node.id}
                                title={serviceText(catalogueEntry(service)).title}
                                mode="run"
                                idPrefix={"run-" + node.id}
                                definition={settingsDefinitionOf(catalogueEntry(service))}
                                values={runOverrides[node.id]}
                                onChange={(values) => setRunOverrides((current) => ({ ...current, [node.id]: values }))}
                                isStartNode={isStartServiceNode(node.id)}
                              />
                            );
                          })}
                      </div>
                    </details>
                  )}
                  {runInputError && <p role="alert" className="ae-field__error">{runInputError}</p>}
                  <button className="ae-btn ae-btn--primary builder-run__action" onClick={confirmDeployment} disabled={!deploymentConfirmationReady || submittingToOrchestrator}>
                    <Play size={16} aria-hidden="true" />{submittingToOrchestrator ? "Deploying..." : "Deploy now"}
                  </button>
                  {!deploymentConfirmationReady && !deploymentResult && (
                    <p className="muted builder-run__hint">Available once the design is valid and every service is ready.</p>
                  )}
                </section>

                {deploymentResult && (
                  <div className={"ae-alert " + (deploymentResult.status === "failed" || deploymentResult.status === "blocked" ? "ae-alert--danger" : "ae-alert--success")}>
                    {deploymentResult.status === "failed" || deploymentResult.status === "blocked" ? <CircleX size={20} aria-hidden="true" /> : <CircleCheck size={20} aria-hidden="true" />}
                    <div>
                      {deploymentResult.workflow_id ? (
                        <>
                          <span className="ae-alert__title">Deployed.</span>{" "}
                          <Link href={"/deployments/" + deploymentResult.workflow_id}>Follow the run</Link>
                          <div className="ae-mono">{deploymentResult.workflow_id}</div>
                        </>
                      ) : (
                        <><span className="ae-alert__title">{deploymentResult.status === "blocked" ? "Not ready to deploy." : "Deployment failed."}</span> {deploymentResult.error}</>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </aside>
      </div>

      <RuntimeReadinessPanel
        preflight={runtimePreflight}
        onPrepare={prepareDeployment}
        preparing={preparingDeployment}
        roleMode={roleMode}
        confirmationReady={deploymentConfirmationReady}
        onConfirm={confirmDeployment}
        confirming={submittingToOrchestrator}
        runInputError={runInputError}
      />
    </div>
  );
}

function RuntimeReadinessPanel({
  preflight,
  onPrepare,
  preparing,
  roleMode,
  confirmationReady,
  onConfirm,
  confirming,
  runInputError,
}: {
  preflight: RuntimePreflightResult | null;
  onPrepare: () => void;
  preparing: boolean;
  roleMode: UserRole;
  confirmationReady: boolean;
  onConfirm: () => void;
  confirming: boolean;
  runInputError: string;
}) {
  const blockedChecks = preflight?.checks.filter((check) => check.blocking) || [];

  return (
    <section
      id="runtime-readiness"
      className={`card runtime-readiness-panel runtime-readiness-panel--${preflight?.status || "unchecked"}`}
    >
      <div className="runtime-readiness-heading">
        <div>
          <span>Prepare deployment</span>
          <h2>Deployment readiness</h2>
          <p>Confirms that every service is eligible, correctly configured, and operationally ready before deployment.</p>
        </div>
        <button onClick={onPrepare} disabled={preparing} style={secondaryButton}>
          {preparing ? "Preparing deployment..." : "Check readiness again"}
        </button>
      </div>

      <div className="runtime-role-note">Signed in as: <strong>{roleLabels[roleMode]}</strong></div>

      {!preflight && (
        <div className="runtime-readiness-summary runtime-readiness-summary--neutral">
          <strong>Deployment has not been prepared yet.</strong>
          <p>Validate the design, then select Prepare &amp; deploy.</p>
        </div>
      )}

      {preflight?.status === "ready" && (
        <div className="runtime-readiness-summary runtime-readiness-summary--ready">
          <strong>Ready to confirm</strong>
          <p>{preflight.summary.message}</p>
        </div>
      )}

      {preflight?.status === "blocked" && (
        <>
          <div className="runtime-readiness-summary runtime-readiness-summary--blocked">
            <strong>Provider action required</strong>
            <p>{preflight.summary.message}</p>
          </div>

          <div className="runtime-readiness-grid">
            {blockedChecks.map((check) => (
              <article className="runtime-readiness-card" key={`${check.node_id}-${check.service_id}`}>
                <span>{formatValue(check.status)}</span>
                <h3>{check.service_name}</h3>
                <dl>
                  <div><dt>Status</dt><dd>{formatValue(check.status)}</dd></div>
                  <div><dt>Managed by</dt><dd>{runtimeOwnerLabel(check)}</dd></div>
                  <div><dt>Reason</dt><dd>{check.message}</dd></div>
                  <div><dt>Recommended action</dt><dd>{check.recommended_action}</dd></div>
                </dl>
                <p className="runtime-readiness-card-copy">{runtimeOwnershipGuidance(check.runtime_management_mode)}</p>
                {check.service_id && (
                  <a className="runtime-action-button" href={`/catalogue/${check.service_id}`}>Open service details</a>
                )}
              </article>
            ))}
          </div>
        </>
      )}

      {preflight?.status === "ready" && confirmationReady && (
        <div className="runtime-readiness-actions">
          <h3>Confirm deployment</h3>
          <p>Readiness has passed. Confirm to submit the deployment through the platform execution layer.</p>
          {runInputError && <p role="alert" style={{ color: "#b42318" }}>{runInputError}</p>}
          <button onClick={onConfirm} disabled={confirming} style={primaryButton}>
            {confirming ? "Submitting deployment..." : "Confirm deployment"}
          </button>
        </div>
      )}
    </section>
  );
}

function ServiceBadges({ service }: { service: Service }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
      <span className="badge">{service.trust_badge}</span>
      <span style={interfaceBadgeStyle(getInterfaceType(service))}>
        {formatValue(getInterfaceType(service))}
      </span>
      <span style={orchestrationBadgeStyle(getOrchestrationMode(service))}>
        {formatValue(getOrchestrationMode(service))}
      </span>
      {service.adapter_type && (
        <span style={metadataBadgeStyle}>adapter: {service.adapter_type}</span>
      )}
    </div>
  );
}

function getLifecycleStatus(service: Service) {
  return service.lifecycle_status || "active";
}

function getInterfaceType(service: Service) {
  return service.interface_type || "control";
}

function getOrchestrationMode(service: Service) {
  return service.orchestration_mode || "native";
}

function formatValue(value?: string | null) {
  if (!value) return "Not specified";
  return value.replaceAll("_", " ");
}

function collectReachable(startIds: string[], adjacency: Map<string, string[]>) {
  const visited = new Set<string>();
  const queue = [...startIds];

  while (queue.length > 0) {
    const current = queue.shift();
    if (!current || visited.has(current)) continue;
    visited.add(current);
    (adjacency.get(current) || []).forEach((next) => {
      if (!visited.has(next)) queue.push(next);
    });
  }

  return visited;
}

function runtimeOwnerLabel(check: RuntimePreflightCheck) {
  return `${check.responsible_party} (${formatValue(check.runtime_management_mode)})`;
}

function runtimeOwnershipGuidance(mode: string) {
  if (mode === "platform_managed") {
    return "Platform-managed runtime: platform preparation will be supported in a later controlled implementation.";
  }
  if (mode === "manual" || mode === "tef_managed") {
    return "Manual or TEF runtime: operator action or scheduling is required.";
  }
  return "Runtime preparation is controlled by the service provider.";
}

function lifecycleBadgeStyle(status: string): CSSProperties {
  if (status === "deprecated") {
    return {
      background: "#fef3c7",
      color: "#92400e",
      border: "1px solid #fde68a",
      padding: "5px 8px",
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 900,
      textTransform: "uppercase",
      letterSpacing: 0.4,
      whiteSpace: "nowrap",
    };
  }

  if (status === "archived") {
    return {
      background: "#f1f5f9",
      color: "#475569",
      border: "1px solid #cbd5e1",
      padding: "5px 8px",
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 900,
      textTransform: "uppercase",
      letterSpacing: 0.4,
      whiteSpace: "nowrap",
    };
  }

  return {
    background: "#dcfce7",
    color: "#166534",
    border: "1px solid #bbf7d0",
    padding: "5px 8px",
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 900,
    textTransform: "uppercase",
    letterSpacing: 0.4,
    whiteSpace: "nowrap",
  };
}

const metadataBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  border: "1px solid #cbd5e1",
  borderRadius: 999,
  padding: "5px 8px",
  fontSize: 12,
  fontWeight: 900,
  textTransform: "uppercase",
  letterSpacing: 0.35,
  whiteSpace: "nowrap",
  background: "#ffffff",
  color: "#334155",
};

function interfaceBadgeStyle(value?: string | null): CSSProperties {
  const normalized = value || "control";

  if (normalized === "grpc") {
    return {
      ...metadataBadgeStyle,
      background: "#eef2ff",
      color: "#3730a3",
      borderColor: "#c7d2fe",
    };
  }

  if (normalized === "http") {
    return {
      ...metadataBadgeStyle,
      background: "#ecfeff",
      color: "#0e7490",
      borderColor: "#a5f3fc",
    };
  }

  if (normalized === "container_job") {
    return {
      ...metadataBadgeStyle,
      background: "#f5f3ff",
      color: "#6d28d9",
      borderColor: "#ddd6fe",
    };
  }

  if (normalized === "legacy_sidecar") {
    return {
      ...metadataBadgeStyle,
      background: "#fff7ed",
      color: "#c2410c",
      borderColor: "#fed7aa",
    };
  }

  return {
    ...metadataBadgeStyle,
    background: "#f0fdf4",
    color: "#047857",
    borderColor: "#bbf7d0",
  };
}

function orchestrationBadgeStyle(value?: string | null): CSSProperties {
  const normalized = value || "native";

  if (normalized === "sidecar") {
    return {
      ...metadataBadgeStyle,
      background: "#fffbeb",
      color: "#92400e",
      borderColor: "#fde68a",
    };
  }

  if (normalized === "external") {
    return {
      ...metadataBadgeStyle,
      background: "#f8fafc",
      color: "#475569",
      borderColor: "#cbd5e1",
    };
  }

  if (normalized === "manual_review") {
    return {
      ...metadataBadgeStyle,
      background: "#fef2f2",
      color: "#b91c1c",
      borderColor: "#fecaca",
    };
  }

  return {
    ...metadataBadgeStyle,
    background: "#eff6ff",
    color: "#1d4ed8",
    borderColor: "#bfdbfe",
  };
}

function validationResultBackground(result: string) {
  if (result.startsWith("Passed:")) return "#ecfdf3";
  if (result.startsWith("Warning:")) return "#fffbeb";
  if (result.startsWith("Note:")) return "#eff6ff";
  return "#fef3f2";
}

function validationResultColor(result: string) {
  if (result.startsWith("Passed:")) return "#067647";
  if (result.startsWith("Warning:")) return "#92400e";
  if (result.startsWith("Note:")) return "#1d4ed8";
  return "#b42318";
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "#f8fafc", padding: 12, borderRadius: 12 }}>
      <div style={{ color: "#667085", fontSize: 13 }}>{label}</div>
      <strong style={{ wordBreak: "break-word" }}>{value}</strong>
    </div>
  );
}

const primaryButton: CSSProperties = {
  background: "linear-gradient(135deg, #5b2cf2, #4320ca)",
  color: "white",
  padding: "10px 14px",
  borderRadius: 10,
  border: "none",
  fontWeight: 800,
  cursor: "pointer",
};

const secondaryButton: CSSProperties = {
  background: "white",
  color: "#5635ce",
  padding: "10px 14px",
  borderRadius: 10,
  border: "1px solid #d1c8f3",
  fontWeight: 800,
  cursor: "pointer",
};
