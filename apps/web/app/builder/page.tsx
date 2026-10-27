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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { roleLabels, useAuth, type UserRole } from "../../components/auth-context";
import { apiErrorMessage } from "../../lib/solution-design";

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
  const [designMetadata, setDesignMetadata] = useState<Record<string, unknown> | null>(null);
  const [runInputMode, setRunInputMode] = useState<"prompt" | "json">("prompt");
  const [runInput, setRunInput] = useState("");
  const [runInputError, setRunInputError] = useState("");
  const [solutionLoadError, setSolutionLoadError] = useState("");
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
        setDesignMetadata(body.design_metadata || null);
        if (body.design_metadata?.run_input != null) {
          setRunInputMode("json");
          setRunInput(JSON.stringify(body.design_metadata.run_input, null, 2));
        }
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

  function addServiceToCanvas(service: Service) {
    const nodeId = `service-${service.id}-${Date.now()}`;
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
      {solutionLoadError && (
        <section className="card" style={{ padding: 18, marginBottom: 18, borderColor: "#fda29b", color: "#b42318" }}>
          <strong>Unable to load solution design.</strong> {solutionLoadError}
        </section>
      )}
      <div className="builder-page-header">
        <div>
          <span className="badge">AI Vendor Studio</span>
          <h1 style={{ fontSize: 42, margin: "14px 0 8px", letterSpacing: "-0.04em" }}>Build a solution</h1>
          <p style={{ color: "#626a83", fontSize: 16, maxWidth: 850, margin: 0, lineHeight: 1.65 }}>
            Compose AI-EFFECT services visually. Add services from the catalogue, connect them into a
            workflow, and prepare the solution for deployment.
          </p>
        </div>
        <div className="builder-top-actions">
          <button onClick={saveSolution} style={secondaryButton} disabled={savingSolution || preparingDeployment}>
            {savingSolution ? "Saving draft..." : "Save draft"}
          </button>
          <button onClick={validateWorkflow} style={secondaryButton}>Validate design</button>
          <button
            onClick={prepareDeployment}
            style={{ ...primaryButton, opacity: preparingDeployment ? 0.7 : 1 }}
            disabled={preparingDeployment || savingSolution}
          >
            {preparingDeployment ? "Preparing deployment..." : "Prepare & deploy"}
          </button>
        </div>
      </div>

      <div className="builder-name-row">
        <div><span>Solution name</span><input value={solutionName} onChange={(event) => setSolutionName(event.target.value)} placeholder="Solution name" /></div>
        <div className="builder-health-summary"><span>{nodes.length}</span> {nodes.length === 1 ? "node" : "nodes"} <span>{edges.length}</span> {edges.length === 1 ? "connection" : "connections"} <span>{validationResults.length}</span> {validationResults.length === 1 ? "check" : "checks"}</div>
      </div>

      {solutionNeedsRevalidation && (
        <div className="builder-stale-message" role="status">
          The solution changed and must be validated again before deployment.
        </div>
      )}

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
        <aside className="card builder-palette-card builder-service-palette">
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
          </div>
        </aside>

        <main className="card builder-canvas-card">
          <div
            className="builder-canvas-header"
          >
            <div><span>Visual workflow</span><strong>Workflow canvas</strong></div>
            <div className="builder-canvas-legend"><i /> Service <i /> Connection</div>
          </div>

          <div className="builder-canvas-area">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={handleNodesChange}
              onEdgesChange={handleEdgesChange}
              onConnect={onConnect}
              onEdgesDelete={onEdgesDelete}
              deleteKeyCode={["Backspace", "Delete"]}
              onNodeClick={(_, node) => {
                const service = node.data?.service as Service | undefined;
                setSelectedService(service || null);
              }}
              fitView
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
        </main>

        <aside className="card builder-details-card">
          <div className="builder-panel-heading"><div><span>Inspector</span><h2>Service details</h2></div></div>

          {!selectedService && (
            <p style={{ color: "#667085", lineHeight: 1.6 }}>
              Select a service on the canvas to inspect its provider, interface, lifecycle, and
              trust status.
            </p>
          )}

          {selectedService && (
            <div style={{ display: "grid", gap: 12 }}>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                <span className="badge">{selectedService.trust_badge}</span>
                <span style={lifecycleBadgeStyle(getLifecycleStatus(selectedService))}>
                  {getLifecycleStatus(selectedService)}
                </span>
              </div>

              <ServiceBadges service={selectedService} />

              <h3 style={{ marginBottom: 0 }}>{selectedService.name}</h3>

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
            </div>
          )}

          <div style={{ marginTop: 30 }}>
            <h3>Validation Results</h3>

            {validationResults.length === 0 && (
              <p style={{ color: "#667085" }}>Run workflow validation.</p>
            )}

            <div style={{ display: "grid", gap: 10 }}>
              {validationResults.map((result, index) => (
                <div
                  key={index}
                  style={{
                    padding: 10,
                    borderRadius: 10,
                    background: validationResultBackground(result),
                    color: validationResultColor(result),
                    whiteSpace: "pre-line",
                  }}
                >
                  {result}
                </div>
              ))}
            </div>

            <div className="runtime-preflight-compact">
              <div className="runtime-preflight-statuses">
                <div>
                  <span>Workflow design</span>
                  <strong className={workflowDesignStatus === "invalid" ? "is-blocked" : workflowDesignStatus === "valid" ? "is-ready" : "is-neutral"}>
                    {workflowDesignStatus === "invalid" ? "Needs attention" : workflowDesignStatus === "valid" ? "Valid" : "Not checked"}
                  </strong>
                </div>
                <div>
                  <span>Deployment readiness</span>
                  <strong className={runtimePreflight?.status === "ready" ? "is-ready" : runtimePreflight?.status === "blocked" ? "is-blocked" : "is-neutral"}>
                    {runtimePreflight?.status === "ready" ? "Ready" : runtimePreflight?.status === "blocked" ? "Blocked" : "Not checked"}
                  </strong>
                </div>
              </div>

              <div className="runtime-preflight-counts">
                <span><strong>{runtimePreflight?.summary.ready || 0}</strong> ready</span>
                <span><strong>{runtimePreflight?.summary.blocked || 0}</strong> blocked</span>
              </div>

              {runtimePreflight?.status === "blocked" && (
                <p>
                  {workflowDesignStatus === "valid"
                    ? "The design is valid, but one or more services require provider or operator action."
                    : "Resolve the design blockers before preparing deployment."}
                </p>
              )}

              <a href="#runtime-readiness">View deployment readiness</a>
            </div>
          </div>

          <div style={{ marginTop: 30 }}>
            <h3>Deployment</h3>

            <label htmlFor="run-input-mode" style={{ display: "block", marginBottom: 8, fontWeight: 600 }}>Run input (optional)</label>
            <select id="run-input-mode" value={runInputMode} onChange={(event) => { setRunInputMode(event.target.value as "prompt" | "json"); setRunInputError(""); }} style={{ width: "100%", padding: 10, marginBottom: 10 }}>
              <option value="prompt">Prompt</option>
              <option value="json">JSON object</option>
            </select>
            <textarea aria-label="Run input" value={runInput} onChange={(event) => { setRunInput(event.target.value); setRunInputError(""); }} rows={5} placeholder={runInputMode === "prompt" ? "Describe what this workflow should do..." : '{"prompt":"...", "option":true}'} style={{ width: "100%", padding: 10, boxSizing: "border-box" }} />
            <p style={{ color: "#667085", fontSize: 13, marginTop: 5 }}>Sent as JSON to the first service when you confirm deployment. Leave empty to use the service default.</p>
            {runInputError && <p role="alert" style={{ color: "#b42318" }}>{runInputError}</p>}

            {!deploymentResult && (
              <p style={{ color: "#667085" }}>
                Validate the design, prepare the deployment, then confirm when all services are ready.
              </p>
            )}

            {deploymentResult && (
              <div
                style={{
                  padding: 12,
                  borderRadius: 12,
                  background:
                    deploymentResult.status === "failed" || deploymentResult.status === "blocked" ? "#fef3f2" : "#ecfdf3",
                  color: deploymentResult.status === "failed" || deploymentResult.status === "blocked" ? "#b42318" : "#067647",
                  whiteSpace: "pre-line",
                }}
              >
                {deploymentResult.workflow_id
                  ? `Deployment submitted\nID: ${deploymentResult.workflow_id}\nStatus: ${deploymentResult.status}`
                  : `${deploymentResult.status === "blocked" ? "Deployment blocked" : "Deployment failed"}\n${deploymentResult.error}`}
              </div>
            )}
          </div>

          <div className="builder-workflow-health">
            <span>Workflow health</span>
            <div><strong>{canvasServices.length}</strong><small>{canvasServices.length === 1 ? "Service" : "Services"}</small></div>
            <div><strong>{edges.length}</strong><small>Connections</small></div>
            <div><strong>{deprecatedCanvasServices.length}</strong><small>Deprecated</small></div>
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
