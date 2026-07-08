"use client";

import { useCallback, useEffect, useMemo, useState, type CSSProperties } from "react";
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
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

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
};

const API_BASE_URL = "http://localhost:18080";

const initialNodes: Node[] = [
  {
    id: "input",
    position: { x: 120, y: 180 },
    data: { label: "Workflow Input" },
    type: "input",
  },
  {
    id: "output",
    position: { x: 760, y: 180 },
    data: { label: "Workflow Output" },
    type: "output",
  },
];

export default function BuilderPage() {
  const searchParams = useSearchParams();
  const solutionId = searchParams.get("solutionId");

  const [services, setServices] = useState<Service[]>([]);
  const [selectedService, setSelectedService] = useState<Service | null>(null);
  const [validationResults, setValidationResults] = useState<string[]>([]);
  const [deploymentResult, setDeploymentResult] = useState<any>(null);
  const [submittingToOrchestrator, setSubmittingToOrchestrator] = useState(false);
  const [currentSolutionId, setCurrentSolutionId] = useState<string | null>(null);
  const [solutionName, setSolutionName] = useState("Untitled AI-EFFECT Solution");

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

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

  useEffect(() => {
    fetch(`${API_BASE_URL}/services`)
      .then((res) => res.json())
      .then(setServices)
      .catch(() => setServices([]));
  }, []);

  useEffect(() => {
    async function loadSolution() {
      if (!solutionId) return;

      const res = await fetch(`${API_BASE_URL}/solutions/${solutionId}`);
      if (!res.ok) return;

      const solution = await res.json();

      setCurrentSolutionId(solution.id);
      setSolutionName(solution.name);
      setNodes(solution.nodes || initialNodes);
      setEdges(solution.edges || []);
    }

    loadSolution();
  }, [solutionId, setNodes, setEdges]);

  function onConnect(connection: Connection) {
    setEdges((eds) => addEdge(connection, eds));
  }

  const onEdgesDelete = useCallback(
    (deletedEdges: any[]) => {
      setEdges((eds) =>
        eds.filter((edge) => !deletedEdges.some((deleted) => deleted.id === edge.id))
      );
    },
    [setEdges]
  );

  function addServiceToCanvas(service: Service) {
    const nodeId = `service-${service.id}-${Date.now()}`;
    const lifecycleStatus = getLifecycleStatus(service);

    setNodes((existing) => [
      ...existing,
      {
        id: nodeId,
        position: {
          x: 360 + Math.random() * 120,
          y: 120 + Math.random() * 180,
        },
        data: {
          label:
            lifecycleStatus === "deprecated"
              ? `${service.name} (deprecated)`
              : service.name,
          service,
        },
      },
    ]);
  }

  function validateWorkflow() {
    const results: string[] = [];

    const deprecatedServices = nodes
      .map((node) => node.data?.service as Service | undefined)
      .filter((service): service is Service => Boolean(service))
      .filter((service) => getLifecycleStatus(service) === "deprecated");

    deprecatedServices.forEach((service) => {
      results.push(
        `⚠ ${service.name} is deprecated. Existing workflows may still use it, but prefer an active replacement for new designs.`
      );
    });

    edges.forEach((edge) => {
      const sourceNode = nodes.find((n) => n.id === edge.source);
      const targetNode = nodes.find((n) => n.id === edge.target);

      const sourceService = sourceNode?.data?.service as Service | undefined;
      const targetService = targetNode?.data?.service as Service | undefined;

      if (!sourceService || !targetService) return;

      if (sourceService.output_type === targetService.input_type) {
        results.push(`✓ ${sourceService.name} → ${targetService.name}`);
      } else {
        results.push(
          `❌ ${sourceService.name} → ${targetService.name}
Output: ${sourceService.output_type}
Input: ${targetService.input_type}`
        );
      }
    });

    if (results.length === 0) {
      results.push("No workflow connections found.");
    }

    setValidationResults(results);
  }

  async function saveSolution() {
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

    const res = await fetch(url, {
      method: currentSolutionId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      alert("Failed to save solution.");
      return;
    }

    const saved = await res.json();
    setCurrentSolutionId(saved.id);
    setSolutionName(saved.name);
    alert("Solution saved successfully.");
  }

  async function submitToOrchestrator() {
    setSubmittingToOrchestrator(true);
    setDeploymentResult(null);

    const serviceNodes = nodes.filter((node) => node.id.startsWith("service-"));

    if (serviceNodes.length === 0) {
      alert("Add at least one service before submitting.");
      setSubmittingToOrchestrator(false);
      return;
    }

    const workflowNodes = serviceNodes.map((node) => {
      const service = node.data.service as Service;

      return {
        node_id: node.id,
        service_id: service.id,
        name: service.name,
        container_name: service.container_name,
        image: service.image,
        proto_uri: service.proto_uri,
        node_type: service.node_type || "MLModel",
        operation_name: service.operation_name,
        input_message_name: service.input_message_name || "Request",
        output_message_name: service.output_message_name || "Response",
        internal_host: service.internal_host || service.container_name,
        internal_port: service.internal_port || "8080",
      };
    });

    const validNodeIds = new Set(serviceNodes.map((node) => node.id));

    const workflowEdges = edges
      .filter((edge) => validNodeIds.has(edge.source) && validNodeIds.has(edge.target))
      .map((edge) => ({
        source: edge.source,
        target: edge.target,
      }));

    const res = await fetch(`${API_BASE_URL}/workflows/submit-to-orchestrator`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: solutionName || "Solution Studio Workflow",
        solution_id: currentSolutionId,
        nodes: workflowNodes,
        edges: workflowEdges,
      }),
    });

    if (!res.ok) {
      const error = await res.text();
      setDeploymentResult({ status: "failed", error });
      setSubmittingToOrchestrator(false);
      return;
    }

    const data = await res.json();
    setDeploymentResult(data);

    if (data.workflow_id) {
      await fetch(`${API_BASE_URL}/deployments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          workflow_id: data.workflow_id,
          solution_id: currentSolutionId,
          name: solutionName || "Solution Studio Workflow",
          status: data.status || "submitted",
        }),
      });
    }

    setSubmittingToOrchestrator(false);
  }

  return (
    <div className="page">
      <span className="badge">AI Vendor Studio</span>
      <h1 style={{ fontSize: 40, marginBottom: 8 }}>Build a solution</h1>

      <p style={{ color: "#526173", fontSize: 17, maxWidth: 900 }}>
        Compose AI-EFFECT services visually. Add services from the catalogue, connect them into a
        workflow, and prepare the solution for orchestrator deployment.
      </p>

      <input
        value={solutionName}
        onChange={(event) => setSolutionName(event.target.value)}
        placeholder="Solution name"
        style={{
          marginTop: 16,
          width: "100%",
          maxWidth: 520,
          padding: "12px 14px",
          borderRadius: 12,
          border: "1px solid #d6dee9",
          fontWeight: 700,
        }}
      />

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

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "320px 1fr 320px",
          gap: 18,
          height: "680px",
          marginTop: deprecatedCanvasServices.length > 0 ? 36 : 28,
        }}
      >
        <aside className="card" style={{ padding: 18, overflow: "auto" }}>
          <h2 style={{ marginTop: 0 }}>Available services</h2>
          <p style={{ color: "#667085", fontSize: 14 }}>
            Click a service to add it to the workflow canvas. Archived services are hidden.
          </p>

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

          <div style={{ display: "grid", gap: 12, marginTop: 18 }}>
            {services.map((service) => {
              const lifecycleStatus = getLifecycleStatus(service);
              const isDeprecated = lifecycleStatus === "deprecated";

              return (
                <button
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
                    <span style={lifecycleBadgeStyle(lifecycleStatus)}>
                      {lifecycleStatus}
                    </span>
                  </div>

                  <div style={{ color: "#667085", fontSize: 13, marginTop: 6 }}>
                    {service.provider}
                  </div>

                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
                    <span className="badge">{service.trust_badge}</span>
                  </div>

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
          </div>
        </aside>

        <main className="card" style={{ overflow: "hidden" }}>
          <div
            style={{
              height: 56,
              borderBottom: "1px solid #e4e9f2",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0 18px",
            }}
          >
            <strong>Workflow canvas</strong>

            <div style={{ display: "flex", gap: 10 }}>
              <button onClick={validateWorkflow} style={primaryButton}>
                Validate workflow
              </button>

              <button
                onClick={submitToOrchestrator}
                style={{
                  ...primaryButton,
                  opacity: submittingToOrchestrator ? 0.7 : 1,
                }}
                disabled={submittingToOrchestrator}
              >
                {submittingToOrchestrator ? "Submitting..." : "Submit to WP3"}
              </button>

              <button onClick={saveSolution} style={secondaryButton}>
                Save draft
              </button>
            </div>
          </div>

          <div style={{ height: "624px" }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
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

        <aside className="card" style={{ padding: 18, overflow: "auto" }}>
          <h2 style={{ marginTop: 0 }}>Node details</h2>

          {!selectedService && (
            <p style={{ color: "#667085", lineHeight: 1.6 }}>
              Select a service node on the canvas to inspect its provider, interface, lifecycle, and
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
                  This selected node uses a deprecated service.
                </div>
              )}

              <Info label="Provider" value={selectedService.provider} />
              <Info label="Category" value={selectedService.category} />
              <Info label="Version" value={`v${selectedService.version}`} />
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
          </div>

          <div style={{ marginTop: 30 }}>
            <h3>Deployment Result</h3>

            {!deploymentResult && (
              <p style={{ color: "#667085" }}>
                Submit a validated workflow to the WP3 orchestrator.
              </p>
            )}

            {deploymentResult && (
              <div
                style={{
                  padding: 12,
                  borderRadius: 12,
                  background:
                    deploymentResult.status === "failed" ? "#fef3f2" : "#ecfdf3",
                  color: deploymentResult.status === "failed" ? "#b42318" : "#067647",
                  whiteSpace: "pre-line",
                }}
              >
                {deploymentResult.workflow_id
                  ? `Workflow submitted\nID: ${deploymentResult.workflow_id}\nStatus: ${deploymentResult.status}`
                  : `Submission failed\n${deploymentResult.error}`}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function getLifecycleStatus(service: Service) {
  return service.lifecycle_status || "active";
}

function lifecycleBadgeStyle(status: string): CSSProperties {
  if (status === "deprecated") {
    return {
      background: "#fef3c7",
      color: "#92400e",
      border: "1px solid #fde68a",
      padding: "5px 8px",
      borderRadius: 999,
      fontSize: 10,
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
      fontSize: 10,
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
    fontSize: 10,
    fontWeight: 900,
    textTransform: "uppercase",
    letterSpacing: 0.4,
    whiteSpace: "nowrap",
  };
}

function validationResultBackground(result: string) {
  if (result.startsWith("✓")) return "#ecfdf3";
  if (result.startsWith("⚠")) return "#fffbeb";
  return "#fef3f2";
}

function validationResultColor(result: string) {
  if (result.startsWith("✓")) return "#067647";
  if (result.startsWith("⚠")) return "#92400e";
  return "#b42318";
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "#f8fafc", padding: 12, borderRadius: 12 }}>
      <div style={{ color: "#667085", fontSize: 13 }}>{label}</div>
      <strong>{value}</strong>
    </div>
  );
}

const primaryButton: CSSProperties = {
  background: "#075985",
  color: "white",
  padding: "10px 14px",
  borderRadius: 10,
  border: "none",
  fontWeight: 800,
  cursor: "pointer",
};

const secondaryButton: CSSProperties = {
  background: "white",
  color: "#075985",
  padding: "10px 14px",
  borderRadius: 10,
  border: "1px solid #bae6fd",
  fontWeight: 800,
  cursor: "pointer",
};