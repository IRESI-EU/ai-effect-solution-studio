"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Position,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { roleLabels, useAuth, type UserRole } from "../../components/auth-context";
import { apiErrorMessage } from "../../lib/solution-design";
import { deploymentResultsUrl, executionLabel, isDutchExperiment } from "../../lib/experiment-journey";
import { designReturnUrl } from "../design-ai/session";
import InstanceParameters, { type InstanceConfiguration } from "../../components/instance-parameters";
import { copyInstance } from "../../lib/copy-instance";
import CapabilityBindings from "../../components/capability-bindings";
import ReviewDialog from "../../components/review-dialog";
import { designFingerprint, nextReviewAction, offlineReview, workflowReview, reviewInput } from "../../lib/builder-review";
import { bindingSignature, savedBindingSignatures, stepPurpose } from "../../lib/connection-review";
import BuilderViewport from "../../components/builder-viewport";
import { MIN_ZOOM, MAX_ZOOM } from "../../lib/builder-viewport";

type Service = {
  id: string;
  name: string;
  provider: string;
  category: string;
  version: string;
  description?: string;
  input_type: string;
  output_type: string;
  trust_badge: string;
  lifecycle_status?: "active" | "deprecated" | "archived" | string | null;

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
  updated_at: string;
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
  const [selectedInstanceId, setSelectedInstanceId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [savedFingerprint, setSavedFingerprint] = useState<string | null>(null);
  const settingsRef = useRef<HTMLElement | null>(null);
  const revealSettings = useCallback(() => {
    if (document.querySelector("dialog[open]")) return;
    settingsRef.current?.querySelector<HTMLElement>(".inspector-step-name")?.focus({preventScroll:true});
    settingsRef.current?.scrollIntoView({block:"start"});
  }, []);
  const [validationDetailsOpen, setValidationDetailsOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [stepDetailsOpen, setStepDetailsOpen] = useState(false);
  const [deploymentOptionsOpen, setDeploymentOptionsOpen] = useState(false);
  const [readinessDetailsOpen, setReadinessDetailsOpen] = useState(false);
  const [profileConfig, setProfileConfig] = useState<{provider_mode?: string; provider_name?: string} | null>(null);
  const [validatingDesign, setValidatingDesign] = useState(false);
  const [savedBindings, setSavedBindings] = useState<Record<string, string>>({});
  const [checkedBindings, setCheckedBindings] = useState<Record<string, string>>({});
  const savedUpdatedAtRef = useRef<string | null>(null);
  const [validationResults, setValidationResults] = useState<string[]>([]);
  const [runtimePreflight, setRuntimePreflight] = useState<RuntimePreflightResult | null>(null);
  const [workflowDesignStatus, setWorkflowDesignStatus] = useState<"valid" | "invalid" | null>(null);
  const [savingSolution, setSavingSolution] = useState(false);
  const [preparingDeployment, setPreparingDeployment] = useState(false);
  const [deploymentConfirmationReady, setDeploymentConfirmationReady] = useState(false);
  const [solutionNeedsRevalidation, setSolutionNeedsRevalidation] = useState(false);
  const [deploymentResult, setDeploymentResult] = useState<any>(null);
  const [submittingToOrchestrator, setSubmittingToOrchestrator] = useState(false);
  const [loadedSolutionScope, setLoadedSolutionScope] = useState<string | null>(null);
  const [currentSolutionId, setCurrentSolutionId] = useState<string | null>(null);
  const [solutionName, setSolutionName] = useState("Untitled AI-EFFECT Solution");
  const [designMetadata, setDesignMetadata] = useState<Record<string, unknown> | null>(null);
  const [runInputMode, setRunInputMode] = useState<"prompt" | "json">("prompt");
  const [runInput, setRunInput] = useState("");
  const [runInputError, setRunInputError] = useState("");
  const [solutionLoadError, setSolutionLoadError] = useState("");
  const [solutionSaveError, setSolutionSaveError] = useState("");
  const [serviceSearch, setServiceSearch] = useState("");
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
  const guidedDutch = isDutchExperiment(nodes, designMetadata);
  const displayedNodes = useMemo(() => guidedDutch ? nodes.map(node => {
    const operation = (node.data?.service as Service | undefined)?.operation_name;
    const order = node.type === "input" ? 0 : node.type === "output" ? 3 : operation === "ConfigureAndSynthesize" ? 1 : 2;
    return {...node, width:245, height:64, measured:{width:245,height:64}, position:{x:0,y:order*125}, sourcePosition:Position.Bottom,targetPosition:Position.Top,
      style:{...node.style,width:245,height:64,boxSizing:"border-box" as const}};
  }) : nodes, [nodes, guidedDutch]);

  const invalidateWorkflowResults = useCallback(() => {
    workflowRevisionRef.current += 1;
    setCheckedBindings({});
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

  const review = workflowReview(nodes, edges);
  const dirty = savedFingerprint !== designFingerprint(solutionName, nodes, edges, designMetadata ? reviewInput(runInputMode, runInput) : undefined);
  const offline = offlineReview(profileConfig, process.env.NEXT_PUBLIC_ENVIRONMENT_LABEL);
  const loaded = !!user && (!solutionId || loadedSolutionScope === JSON.stringify([user.id, solutionId]));
  const reviewAction = nextReviewAction({steps: canvasServices.length, dirty, design: workflowDesignStatus, offline,
    readiness: runtimePreflight?.status, confirmationReady: deploymentConfirmationReady, submitted: !!deploymentResult?.workflow_id});
  const actionLabels = {add: "Add services", save: "Save draft", validate: "Validate design", review: "Validate again", prepare: "Prepare & deploy", confirm: "Confirm deployment", results: "View this run’s results"};
  const busy = savingSolution || validatingDesign || preparingDeployment || submittingToOrchestrator;
  async function takeNextAction() {
    if (busy || !loaded) return;
    if (reviewAction === "add") { setPaletteOpen(true); return; }
    if (reviewAction === "save") { await saveSolution(); return; }
    if (reviewAction === "prepare") { await prepareDeployment(); return; }
    if (reviewAction === "confirm") { await confirmDeployment(); return; }
    if (reviewAction === "validate" || reviewAction === "review") {
      setValidatingDesign(true);
      try { await validateWorkflow(); } finally { setValidatingDesign(false); }
    }
  }
  useEffect(() => {
    let active = true;
    fetch(`${API_BASE_URL}/design-ai/config`).then(r => r.ok ? r.json() : null).then(value => { if (active) setProfileConfig(value); }).catch(() => {});
    return () => { active = false; };
  }, []);
  useEffect(() => { setStepDetailsOpen(false); }, [selectedInstanceId, solutionId]);
  useEffect(() => { if (selectedInstanceId) revealSettings(); }, [selectedInstanceId, revealSettings]);

  const deprecatedCanvasServices = useMemo(
    () => canvasServices.filter((service) => getLifecycleStatus(service) === "deprecated"),
    [canvasServices]
  );

  const deprecatedAvailableCount = useMemo(
    () => services.filter((service) => getLifecycleStatus(service) === "deprecated").length,
    [services]
  );

  const filteredServices = useMemo(() => {
    const query = serviceSearch.trim().toLowerCase();
    if (!query) return services;
    return services.filter((service) =>
      [service.name, service.provider, service.category, getInterfaceType(service)]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [services, serviceSearch]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/services`)
      .then((res) => res.json())
      .then(setServices)
      .catch(() => setServices([]));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function loadSolution() {
      if (!solutionId || !user?.id) return;
      setSolutionLoadError("");
      try {
        const res = await fetch(`${API_BASE_URL}/solutions/${solutionId}`, { signal: controller.signal });
        const body = await res.json().catch(() => null);
        if (!res.ok) {
          throw new Error(apiErrorMessage(body, `Could not load this solution (HTTP ${res.status}).`));
        }
        if (controller.signal.aborted) return;
        invalidateWorkflowResults();
        setSolutionNeedsRevalidation(false);
        setLoadedSolutionScope(JSON.stringify([user.id, solutionId]));
        setCurrentSolutionId(body.id);
        savedUpdatedAtRef.current = body.updated_at;
        setSelectedEdgeId(null);
        setSavedBindings(savedBindingSignatures(body.nodes || [], body.edges || []));
        setSavedFingerprint(designFingerprint(body.name, body.nodes || initialNodes, body.edges || [], body.design_metadata ? body.design_metadata.run_input ?? null : undefined));
        setCheckedBindings({});
        setSelectedInstanceId(null);
        setSelectedService(null);
        setSolutionName(body.name);
        setNodes(body.nodes || initialNodes);
        setEdges(body.edges || []);
        setDesignMetadata(body.design_metadata || null);
        if (body.design_metadata?.run_input != null) {
          setRunInputMode("json");
          setRunInput(JSON.stringify(body.design_metadata.run_input, null, 2));
        } else { setRunInputMode("prompt"); setRunInput(""); }
      } catch (error) {
        if (controller.signal.aborted) return;
        setSolutionLoadError(error instanceof Error ? error.message : "Could not load this solution.");
      }
    }

    void loadSolution();
    return () => controller.abort();
  }, [solutionId, user?.id, setNodes, setEdges, invalidateWorkflowResults]);

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

  function addServiceToCanvas(service: Service) {
    const nodeId = `service-${service.id}-${crypto.randomUUID()}`;
    setSelectedInstanceId(nodeId);
    setSelectedService(service);
    const lifecycleStatus = getLifecycleStatus(service);
    const interfaceType = getInterfaceType(service);
    const orchestrationMode = getOrchestrationMode(service);

    setNodes((existing) => [
      ...existing,
      {
        id: nodeId,
        position: {
          x: 360 + Math.random() * 120,
          y: 120 + Math.random() * 180,
        },
        data: {
          node_kind: "service",
          label:
            lifecycleStatus === "deprecated"
              ? `${service.name} (deprecated)`
              : `${service.name} [${formatValue(interfaceType)} / ${formatValue(
                  orchestrationMode
                )}]`,
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
        ...("configuration" in node.data ? { configuration: node.data.configuration } : {}),
        ...("operation_contract" in node.data ? { operation_contract: node.data.operation_contract } : {}),
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
      };
    });
    const validNodeIds = new Set(serviceNodes.map((node) => node.id));
    const workflowEdges = edges
      .filter((edge) => validNodeIds.has(edge.source) && validNodeIds.has(edge.target))
      .map((edge) => ({ source: edge.source, target: edge.target,
        ...(edge.data && "binding" in edge.data ? { binding: edge.data.binding } : {}) }));

    return {
      name: solutionName || "Solution Studio Workflow",
      solution_id: solutionIdForPayload,
      expected_updated_at: savedUpdatedAtRef.current,
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
      throw new Error(apiErrorMessage(await response.json().catch(() => null), `Deployment readiness check failed with HTTP ${response.status}.`));
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

      if (edge.data?.binding) {
        notices.push(`Connection: ${sourceService.name} to ${targetService.name} will be checked against pinned operation contracts.`);
      } else if (sourceService.output_type !== targetService.input_type) {
        blockers.push(`Blocked: ${sourceService.name} to ${targetService.name} has different catalogue interface labels. Choose a verified data connection or review the services with their owner.`);
      } else {
        notices.push(`Unverified: ${sourceService.name} to ${targetService.name} has no explicit semantic binding.`);
      }
    });

    serviceNodes.forEach((node) => {
      const service = node.data.service as Service;
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

  async function validateWorkflow() {
    const revision = workflowRevisionRef.current;
    const result = evaluateWorkflowDesign();
    const checked: Record<string, string> = {};
    if (result.valid) {
      try {
        const response = await fetch(`${API_BASE_URL}/workflows/compile`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...buildWorkflowPayload(), ...(buildRunInput() ? { run_input: buildRunInput() } : {}) }),
        });
        const body = await response.json();
        if (!response.ok) throw new Error(apiErrorMessage(body, "Connection validation failed."));
        const report = body.solution_studio_metadata.capability_bindings;
        for (const edge of edges) {
          const selectedBinding = edge.data?.binding as {source_slot: string; target_slot: string} | undefined;
          if (selectedBinding && report.status === "verified" && report.bindings?.some((binding: {source: string; target: string; source_slot: string; target_slot: string}) =>
            binding.source === edge.source && binding.target === edge.target && binding.source_slot === selectedBinding.source_slot
              && binding.target_slot === selectedBinding.target_slot)) checked[edge.id] = bindingSignature(nodes, edge);
        }
        result.results.push(`${report.status === "verified" ? "Passed" : "Notice"}: ${report.message}`);
      } catch (error) {
        result.valid = false;
        result.results = result.results.filter(message => message !== "Passed: Workflow design is valid.");
        result.results.unshift(`Blocked: ${error instanceof Error ? error.message : "Connection validation failed."}`);
      }
    }
    if (revision !== workflowRevisionRef.current) return { valid: false, results: ["Design changed during validation. Validate again."] };
    setCheckedBindings(result.valid ? checked : {});
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
    if (offline || prepareInFlightRef.current) return;
    prepareInFlightRef.current = true;

    const design = await validateWorkflow();
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
      } catch (error) {
        if (workflowRevision === workflowRevisionRef.current) {
          setRuntimePreflight(null);
          setDeploymentConfirmationReady(false);
          setDeploymentResult({
            status: "failed",
            error: error instanceof Error ? error.message : "The solution could not be saved. Deployment preparation was stopped.",
          });
        }
        return;
      }

      if (workflowRevision !== workflowRevisionRef.current) return;

      const preflight = await runRuntimePreflight({ ...buildWorkflowPayload(savedSolution.id), ...(buildRunInput() ? { run_input: buildRunInput() } : {}) });
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
      ...(currentSolutionId ? { expected_updated_at: savedUpdatedAtRef.current } : {}),
      name: solutionName || "Untitled AI-EFFECT Solution",
      description: "Saved workflow design from Builder",
      nodes,
      edges,
      status: "draft",
      design_metadata: designMetadata ? { ...designMetadata, run_input: buildRunInput() ?? null } : null,
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

      if (!res.ok) throw new Error(apiErrorMessage(await res.json().catch(() => null), `Solution save failed with HTTP ${res.status}.`));

      const saved = (await res.json()) as SavedSolution;
      if (!saved.id) throw new Error("The saved solution response did not include an ID.");

      setSavedBindings(savedBindingSignatures(payload.nodes, payload.edges));
      setSavedFingerprint(designFingerprint(saved.name || payload.name, payload.nodes, payload.edges, payload.design_metadata ? payload.design_metadata.run_input : undefined));
      setCurrentSolutionId(saved.id);
      savedUpdatedAtRef.current = saved.updated_at;
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
    setSolutionSaveError("");

    try {
      await persistSolution();
      alert("Solution saved successfully.");
    } catch (error) {
      setSolutionSaveError(error instanceof Error ? error.message : "Failed to save solution.");
    } finally {
      setSavingSolution(false);
      saveDraftInFlightRef.current = false;
    }
  }

  async function confirmDeployment() {
    const preparedSolutionId = preparedSolutionIdRef.current;
    if (
      offline || confirmInFlightRef.current ||
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
      setRunInputError("");
    } catch (error) {
      setRunInputError(error instanceof Error ? error.message : "Invalid run input.");
      return;
    }

    confirmInFlightRef.current = true;
    setSubmittingToOrchestrator(true);
    setDeploymentResult(null);

    try {
      const workflowPayload = { ...buildWorkflowPayload(preparedSolutionId), ...(input === undefined ? {} : { run_input: input }) };
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
    <div className="page builder-page">
      <div className="builder-page-header">
        <div><h1>Build a solution</h1><p>Review the workflow, then select a step to change its settings.</p></div>
        <div className="builder-review-links">
          <Link href={designReturnUrl(designMetadata)}>Return to Design with AI</Link>
          {!guidedDutch && <button type="button" disabled={!loaded} onClick={() => setPaletteOpen(true)}>Add services</button>}
        </div>
      </div>
      {offline && <section className="builder-offline-notice" role="status"><strong>OFFLINE TEST FIXTURE</strong>
        <span>Design review only. Execution is unavailable in this profile. Saving or validating does not execute this workflow.</span></section>}
      {solutionLoadError && <p role="alert">Unable to load solution design. {solutionLoadError}</p>}
      <section className="card builder-overview" aria-label="Workflow overview">
        <label className="builder-solution-name">Solution name<input aria-label="Solution name" value={solutionName}
          onChange={event => { setSolutionName(event.target.value); invalidateWorkflowResults(); }} /></label>
        <p className="builder-workflow-purpose">{loaded ? review.purpose : "Loading workflow…"}</p>
        <ol className="builder-step-list" aria-label="Processing steps">
          {review.steps.map((node, index) => <li key={node.id}><button type="button" aria-pressed={selectedInstanceId === node.id}
            onClick={() => { setSelectedEdgeId(null); setSelectedInstanceId(node.id); setSelectedService(node.data.service as Service); }}>
            <span>{index + 1}</span>{(node.data.service as Service).name}</button></li>)}
        </ol>
      <div className="builder-connections-card">
          <CapabilityBindings nodes={nodes} edges={edges} saved={savedBindings} checked={checkedBindings} selectedEdgeId={selectedEdgeId} onBind={(edgeId, source, target, sourceSlot, targetSlot) => {
            const edge = edges.find(e => e.id === edgeId);
            if (!edge) return;
            const nextNodes = nodes.map(node => {
              const contract = node.id === edge.source ? source : node.id === edge.target ? target : null;
              return contract ? { ...node, data: { ...node.data, operation_contract: {
                contract_id: contract.id, contract_version: contract.contract_version,
              } } } : node;
            });
            const nextEdges = edges.map(value => value.id === edgeId ? { ...value, data: { ...value.data,
              binding: { source_slot: sourceSlot, target_slot: targetSlot } } } : value);
            if (bindingSignature(nodes, edge) === bindingSignature(nextNodes, nextEdges.find(value => value.id === edgeId)!)) return;
            setNodes(nextNodes);
            setEdges(nextEdges);
            invalidateWorkflowResults();
          }} />
      </div>
      <section className="builder-review-actions" aria-label="Review status and next action" id="runtime-readiness">
        <dl className="builder-review-statuses">
          <div><dt>Design saved</dt><dd>{!loaded ? "Loading" : dirty ? "Unsaved changes" : "Saved"}</dd></div>
          <div><dt>Design compatibility</dt><dd>{workflowDesignStatus === "valid" ? "Checked successfully" : workflowDesignStatus === "invalid" ? "Needs attention" : "Not checked"}</dd></div>
          <div><dt>Runtime readiness</dt><dd>{runtimePreflight?.status === "ready" ? "Checked — ready" : runtimePreflight?.status === "blocked" ? "Checked — blocked" : "Not checked"}</dd></div>
          <div><dt>Execution</dt><dd>{deploymentResult?.workflow_id ? executionLabel(deploymentResult.status) : submittingToOrchestrator ? "Submitting…" : "No execution result in this view"}</dd></div>
        </dl>
        <div className="builder-next-action">
          <p>{!loaded ? "Wait for the workflow to load." : dirty ? "Next: Save your design changes." : workflowDesignStatus !== "valid" ? "Next: Validate the design and its connections." : offline ? "Design review complete. You can review the settings or return to Design with AI. Runtime readiness is unchecked; execution is unavailable." : deploymentConfirmationReady ? "Readiness has passed. Only Confirm deployment submits an execution." : "Next: Prepare & deploy checks readiness before explicit confirmation."}</p>
          {reviewAction === "results" && deploymentResult?.workflow_id ? <Link className="btn btn-primary" href={deploymentResultsUrl(deploymentResult.workflow_id)}>{actionLabels.results}</Link> :
            <button type="button" onClick={takeNextAction} disabled={!loaded || busy} style={reviewAction === "review" ? secondaryButton : primaryButton}>
              {busy ? savingSolution ? "Saving draft…" : validatingDesign ? "Validating design…" : submittingToOrchestrator ? "Submitting deployment…" : "Preparing deployment…" : actionLabels[reviewAction]}</button>}
        </div>
        {solutionNeedsRevalidation && <p className="builder-stale-message">The design changed. Validate again after saving.</p>}
        {solutionSaveError && <p role="alert">Could not save this solution. {solutionSaveError}</p>}
        {runInputError && <p role="alert">{runInputError}</p>}
        {validationResults.filter(result => /^(Blocked|Warning)/.test(result)).map((result, index) => <p key={index} role="alert">{result}</p>)}
        {deploymentResult && !deploymentResult.workflow_id && <p role="alert">{deploymentResult.status === "blocked" ? "Deployment blocked" : "Deployment failed"}: {String(deploymentResult.error)}</p>}
        {runtimePreflight?.checks.filter(check => check.blocking).map(check => <p key={check.node_id} role="alert"><strong>{check.service_name}:</strong> {check.recommended_action}</p>)}
        <div className="builder-review-secondary">
          {validationResults.length > 0 && <button type="button" onClick={() => setValidationDetailsOpen(true)}>Design check details</button>}
          <button type="button" onClick={() => setDeploymentOptionsOpen(true)}>Deployment options</button>
          {runtimePreflight && <button type="button" onClick={() => setReadinessDetailsOpen(true)}>Readiness details</button>}
        </div>
      </section>
      </section>
      <ReviewDialog open={validationDetailsOpen} onClose={() => setValidationDetailsOpen(false)} title="Design check details">
        {validationResults.map((result,index) => <p key={index}>{result}</p>)}
      </ReviewDialog>
      <ReviewDialog open={paletteOpen} onClose={() => setPaletteOpen(false)} title="Available services">
        <aside className={`card builder-palette-card builder-service-palette ${guidedDutch ? "guided-service-review" : ""}`}>
          {guidedDutch ? <><h2>Experiment services</h2><p>The generated grid is passed to the benchmark.</p>{canvasServices.map(service => <details key={service.id}><summary>{service.operation_name === "ConfigureAndSynthesize" ? "Generate sample grid." : "Benchmark grid."}</summary><p>{service.name}</p><code>{service.id}</code><br /><code>{service.operation_name}</code></details>)}</> : <>
          <div className="builder-panel-heading"><div><span>Service palette</span><h2>Available services</h2></div><strong>{filteredServices.length}</strong></div>
          <p style={{ color: "#697087", fontSize: 12, lineHeight: 1.55 }}>
            Click a service to add it to the workflow canvas. Archived services are hidden.
          </p>

          <label className="builder-search-control">
            <input value={serviceSearch} onChange={(event) => setServiceSearch(event.target.value)} placeholder="Search services..." aria-label="Search services" />
          </label>

          {deprecatedAvailableCount > 0 && (
            <div
              style={{
                marginTop: 12,
                padding: 12,
                borderRadius: 12,
                background: "#fef3c7",
                color: "#92400e",
                fontSize: 13,
                lineHeight: 1.5,
                fontWeight: 600,
              }}
            >
              {deprecatedAvailableCount} deprecated service
              {deprecatedAvailableCount === 1 ? "" : "s"} available. Use only for compatibility.
            </div>
          )}

          <div className="builder-service-list-scroll">
            {filteredServices.map((service) => {
              const lifecycleStatus = getLifecycleStatus(service);
              const isDeprecated = lifecycleStatus === "deprecated";

              return (
                <button
                  className="builder-service-card"
                  key={service.id}
                  onClick={() => addServiceToCanvas(service)}
                  style={{
                    textAlign: "left",
                    padding: 14,
                    borderRadius: 14,
                    border: isDeprecated ? "1px solid #f59e0b" : "1px solid #d6dee9",
                    background: isDeprecated ? "#fffbeb" : "white",
                    cursor: "pointer",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 8,
                      alignItems: "flex-start",
                    }}
                  >
                    <strong>{service.name}</strong>
                    <span style={lifecycleBadgeStyle(lifecycleStatus)}>{lifecycleStatus}</span>
                  </div>

                  <div style={{ color: "#667085", fontSize: 13, marginTop: 6 }}>
                    {service.provider}
                  </div>

                  <ServiceBadges service={service} />

                  {isDeprecated && (
                    <div
                      style={{
                        marginTop: 10,
                        color: "#92400e",
                        fontSize: 12,
                        fontWeight: 700,
                        lineHeight: 1.4,
                      }}
                    >
                      Deprecated. Prefer an active replacement for new workflows.
                    </div>
                  )}
                </button>
              );
            })}
            {filteredServices.length === 0 && <div className="builder-empty-palette">No services match your search.</div>}
          </div></>}
        </aside>
      </ReviewDialog>
      <ReviewDialog open={deploymentOptionsOpen} onClose={() => setDeploymentOptionsOpen(false)} title="Deployment options">
        <p>{offline ? "Execution is unavailable in this offline profile." : "These inputs are sent only after the required readiness check and explicit deployment confirmation."}</p>
        {guidedDutch ? <p>Saved experiment settings: seed <strong>{String((designMetadata?.run_input as Record<string, unknown>)?.seed)}</strong>. Review settings in Design with AI before preparing a run.</p> : <>
          <label htmlFor="run-input-mode">Run input (optional)</label>
          <select id="run-input-mode" value={runInputMode} onChange={event => { setRunInputMode(event.target.value as "prompt" | "json"); setRunInputError(""); invalidateWorkflowResults(); }}><option value="prompt">Prompt</option><option value="json">JSON object</option></select>
          <textarea aria-label="Run input" value={runInput} onChange={event => { setRunInput(event.target.value); setRunInputError(""); invalidateWorkflowResults(); }} rows={5} />
          <p>Leave empty to use the service default. Required input errors are shown next to the review action.</p>
        </>}
        {runInputError && <p role="alert">{runInputError}</p>}
      </ReviewDialog>
      <ReviewDialog open={readinessDetailsOpen} onClose={() => setReadinessDetailsOpen(false)} title="Readiness details">
        <RuntimeReadinessDetails preflight={runtimePreflight} roleMode={roleMode} />
      </ReviewDialog>
      {deprecatedCanvasServices.length > 0 && (
        <div
          className="card"
          style={{
            marginTop: 20,
            padding: 18,
            border: "1px solid #fde68a",
            background: "#fffbeb",
          }}
        >
          <strong style={{ color: "#92400e" }}>This solution uses deprecated services</strong>
          <p style={{ color: "#92400e", margin: "8px 0 0", lineHeight: 1.6 }}>
            Deprecated services remain runnable for compatibility, but new workflows should move to
            active replacements where available.
          </p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
            {deprecatedCanvasServices.map((service) => (
              <span key={service.id} style={lifecycleBadgeStyle("deprecated")}>
                {service.name}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="builder-workbench" style={{ marginTop: deprecatedCanvasServices.length > 0 ? 32 : 24 }}>
        <main className="card builder-canvas-card">
          <div
            className="builder-canvas-header"
          >
            <div><span>Visual workflow</span><strong>Workflow canvas</strong></div>
            <div className="builder-canvas-legend"><i /> Service <i /> Connection</div>
          </div>

          <div className="builder-canvas-area">
            {user && (!solutionId || loadedSolutionScope === JSON.stringify([user.id, solutionId])) ? <ReactFlow
              key={JSON.stringify([user.id, solutionId || currentSolutionId, guidedDutch])}
              nodes={displayedNodes}
              nodesDraggable={!guidedDutch}
              nodesConnectable={!guidedDutch}
              edgesReconnectable={!guidedDutch}
              edges={edges}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              onConnect={onConnect}
              onEdgesDelete={onEdgesDelete}
              deleteKeyCode={guidedDutch ? null : ["Backspace", "Delete"]}
              onNodeClick={(_, node) => {
                const service = node.data?.service as Service | undefined;
                setSelectedEdgeId(null);
                setSelectedService(service || null);
                setSelectedInstanceId(service ? node.id : null);
              }}
              onEdgeClick={(_, edge) => { setSelectedEdgeId(edge.id); setSelectedService(null); setSelectedInstanceId(null); }}
              onPaneClick={() => { setSelectedEdgeId(null); setSelectedService(null); setSelectedInstanceId(null); }}
              minZoom={MIN_ZOOM}
              maxZoom={MAX_ZOOM}
              ariaLabelConfig={{ "controls.fitView.ariaLabel": "Fit workflow" }}
            >
              <Background />
              <BuilderViewport userId={user.id} solutionId={solutionId || currentSolutionId} />
              <Controls showInteractive={!guidedDutch} fitViewOptions={{ padding: 0.12, minZoom: MIN_ZOOM, maxZoom: 1 }} />
              <MiniMap pannable zoomable />
            </ReactFlow> : <p role="status" style={{ padding: 20 }}>{solutionLoadError || "Loading workflow canvas..."}</p>}
          </div>
        </main>

        <aside ref={settingsRef} className="card builder-details-card">
          <div className="builder-panel-heading"><div><span>Inspector</span><h2>{selectedEdgeId ? "Connection review" : "Step settings"}</h2></div></div>

          {!selectedService && (
            <p style={{ color: "#667085", lineHeight: 1.6 }}>
              Select a step to find its settings, or a connection to review its data flow.
            </p>
          )}


          {selectedService && (
            <div style={{ display: "grid", gap: 12 }}>
              <h3 tabIndex={-1} className="inspector-step-name">{String(nodes.find(n => n.id === selectedInstanceId)?.data.label || selectedService.name)}</h3>
              <p className="inspector-purpose">{stepPurpose(selectedService)}</p>
              {selectedService.description && <details className="builder-description"><summary>About this step</summary><p>{selectedService.description}</p></details>}
              {!guidedDutch && selectedInstanceId && nodes.some(node => node.id === selectedInstanceId) && <InstanceParameters
                key={selectedInstanceId} instanceId={selectedInstanceId} serviceId={selectedService.id} onReady={revealSettings}
                configuration={nodes.find(node => node.id === selectedInstanceId)?.data.configuration as InstanceConfiguration | undefined}
                onChange={configuration => {
                  setNodes(existing => existing.map(node => {
                    if (node.id !== selectedInstanceId) return node;
                    const data = { ...node.data };
                    if (configuration === undefined) delete data.configuration; else data.configuration = configuration;
                    return { ...node, data };
                  }));
                  invalidateWorkflowResults();
                }}
                onCopy={() => {
                  const original = nodes.find(node => node.id === selectedInstanceId);
                  if (!original) return;
                  const copied = copyInstance(original, edges, `service-${crypto.randomUUID()}`);
                  setNodes(existing => [...existing, copied.node]);
                  setEdges(existing => [...existing, ...copied.edges]);
                  setSelectedInstanceId(copied.node.id);
                  invalidateWorkflowResults();
                }}
              />}

              {getLifecycleStatus(selectedService) === "deprecated" && (
                <div
                  style={{
                    padding: 12,
                    borderRadius: 12,
                    background: "#fef3c7",
                    color: "#92400e",
                    fontSize: 13,
                    lineHeight: 1.5,
                    fontWeight: 600,
                  }}
                >
                  This selected service is deprecated.
                </div>
              )}

              {getOrchestrationMode(selectedService) === "sidecar" && (
                <div
                  style={{
                    padding: 12,
                    borderRadius: 12,
                    background: "#fffbeb",
                    color: "#92400e",
                    fontSize: 13,
                    lineHeight: 1.5,
                    fontWeight: 600,
                  }}
                >
                  This service uses sidecar orchestration. It will run through the AI-EFFECT Control
                  Interface compatibility path.
                </div>
              )}

              <button type="button" onClick={() => setStepDetailsOpen(true)}>Technical details for this step</button>
              <ReviewDialog open={stepDetailsOpen} onClose={() => setStepDetailsOpen(false)} title="Step technical details">
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <span className="badge">{selectedService.trust_badge}</span>
                <span style={lifecycleBadgeStyle(getLifecycleStatus(selectedService))}>
                  {getLifecycleStatus(selectedService)}
                </span>
              </div>

              <ServiceBadges service={selectedService} />

              <Info label="Instance" value={selectedInstanceId || "Not selected"} />
              <Info label="Operation contract pin" value={JSON.stringify(nodes.find(n => n.id === selectedInstanceId)?.data.operation_contract || "Not selected")} />
              <Info label="Provider" value={selectedService.provider} />
              <Info label="Category" value={selectedService.category} />
              <Info label="Version" value={`v${selectedService.version}`} />
              <Info label="Interface" value={formatValue(getInterfaceType(selectedService))} />
              <Info
                label="Orchestration"
                value={formatValue(getOrchestrationMode(selectedService))}
              />
              <Info label="Adapter" value={selectedService.adapter_type || "none"} />
              <Info label="Contract URI" value={selectedService.contract_uri || "Not declared"} />
              <Info label="Proto URI" value={selectedService.proto_uri || "Not declared"} />
              <Info label="Input" value={selectedService.input_type} />
              <Info label="Output" value={selectedService.output_type} />
              {selectedService.description && <p>{selectedService.description}</p>}
              </ReviewDialog>
            </div>
          )}

        </aside>
      </div>

    </div>
  );
}

function RuntimeReadinessDetails({ preflight, roleMode }: { preflight: RuntimePreflightResult | null; roleMode: UserRole }) {
  return <section><p>Signed in as {roleLabels[roleMode]}. {preflight ? preflight.summary.message : "Runtime readiness has not been checked."}</p>
    {preflight?.checks.map(check => <article key={check.node_id}><h3>{check.service_name}</h3><dl>
      <dt>Status</dt><dd>{check.status}</dd><dt>Reason</dt><dd>{check.message}</dd><dt>Recommended action</dt><dd>{check.recommended_action}</dd>
      <dt>Managed by</dt><dd>{runtimeOwnerLabel(check)}</dd><dt>Runtime</dt><dd>{check.runtime_url || "Unknown"}</dd></dl>
      <p>{runtimeOwnershipGuidance(check.runtime_management_mode)}</p><Link href={`/catalogue/${check.service_id}`}>Open service details</Link></article>)}
  </section>;
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
