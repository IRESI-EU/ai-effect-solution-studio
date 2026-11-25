"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { countServiceConnections, countServiceNodes } from "../../../lib/solution-design";

type Deployment = {
  id: string;
  workflow_id: string;
  solution_id?: string | null;
  name: string;
  status: string;
  is_archived?: boolean;
  created_at: string;
  updated_at: string;
};

type SolutionWorkspace = {
  id: string;
  name: string;
  description?: string | null;
  nodes: Node[];
  edges: Edge[];
  status: string;
  created_at: string;
  updated_at: string;
  deployments: Deployment[];
};

type SyncSummary = {
  total: number;
  updated: number;
  unchanged: number;
  failed: number;
};

export default function SolutionDetailsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [solutionId, setSolutionId] = useState("");
  const [solution, setSolution] = useState<SolutionWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [archivingId, setArchivingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [syncSummary, setSyncSummary] = useState<SyncSummary | null>(null);

  async function loadSolution(id: string) {
    const res = await fetch(`/api/solutions/${id}/workspace`);

    if (!res.ok) {
      throw new Error("Failed to load solution workspace.");
    }

    const data = await res.json();
    setSolution(data);
  }

  async function refreshWorkspace() {
    if (!solutionId) {
      return;
    }

    setRefreshing(true);
    setSyncSummary(null);
    setError("");

    try {
      const syncRes = await fetch(
        "/api/deployments/sync-statuses",
        {
          method: "POST",
        }
      );

      if (syncRes.ok) {
        const summary = await syncRes.json();
        setSyncSummary(summary);
      }

      await loadSolution(solutionId);
    } catch {
      setError("Could not refresh this solution workspace.");
    } finally {
      setRefreshing(false);
    }
  }

  async function archiveDeployment(deploymentId: string) {
    const confirmed = window.confirm(
      "Archive this deployment? It will be hidden from this solution workspace and the active deployments page, but kept for audit history."
    );

    if (!confirmed || !solutionId) {
      return;
    }

    setArchivingId(deploymentId);
    setError("");

    try {
      const res = await fetch(
        `/api/deployments/${deploymentId}/archive`,
        {
          method: "PUT",
        }
      );

      if (!res.ok) {
        throw new Error("Failed to archive deployment.");
      }

      await loadSolution(solutionId);
    } catch {
      setError("Could not archive deployment.");
    } finally {
      setArchivingId(null);
    }
  }

  useEffect(() => {
    async function init() {
      try {
        const { id } = await params;
        setSolutionId(id);
        await loadSolution(id);
      } catch {
        setError("Could not load this solution workspace.");
      } finally {
        setLoading(false);
      }
    }

    init();
  }, [params]);

  const sortedDeployments = useMemo(() => {
    return [...(solution?.deployments || [])].sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }, [solution]);

  const latestDeployment = sortedDeployments[0];

  const completedCount = sortedDeployments.filter(
    (deployment) => deployment.status === "completed"
  ).length;

  const failedCount = sortedDeployments.filter(
    (deployment) => deployment.status === "failed"
  ).length;

  const runningCount = sortedDeployments.filter(
    (deployment) => deployment.status === "running"
  ).length;

  const successRate =
    sortedDeployments.length > 0
      ? Math.round((completedCount / sortedDeployments.length) * 100)
      : 0;

  return (
    <div className="page">
      <Link href="/solutions" style={{ color: "#075985", fontWeight: 800 }}>
        ← Back to saved solutions
      </Link>

      {loading && (
        <section className="card" style={{ padding: 30, marginTop: 20 }}>
          Loading solution workspace...
        </section>
      )}

      {error && (
        <section className="card" style={{ padding: 30, marginTop: 20 }}>
          <p style={{ color: "#b42318", fontWeight: 800 }}>{error}</p>
        </section>
      )}

      {solution && (
        <>
          <section
            className="card"
            style={{
              padding: 30,
              marginTop: 20,
              background: "linear-gradient(135deg, #ffffff 0%, #f7f4ff 100%)",
              border: "1px solid #ded7f5",
              boxShadow: "0 18px 46px rgba(48, 35, 104, 0.08)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 24,
                alignItems: "flex-start",
              }}
            >
              <div>
                <span className="badge">Solution Workspace</span>

                <h1 style={{ fontSize: 40, margin: "16px 0 10px" }}>
                  {solution.name}
                </h1>

                <span
                  className="badge"
                  style={solutionStatusBadgeStyle(solution.status)}
                >
                  {solution.status}
                </span>

                <p style={{ color: "#526173", fontSize: 17, maxWidth: 850 }}>
                  {solution.description || "No description provided."}
                </p>
              </div>

              <div style={{ display: "flex", gap: 12 }}>
                <button
                  onClick={refreshWorkspace}
                  disabled={refreshing}
                  style={{
                    border: "1px solid #d7ceff",
                    background: refreshing ? "#f8fafc" : "white",
                    color: "#6941c6",
                    padding: "12px 16px",
                    borderRadius: 12,
                    fontWeight: 800,
                    cursor: refreshing ? "not-allowed" : "pointer",
                    whiteSpace: "nowrap",
                  }}
                >
                  {refreshing ? "Refreshing..." : "Refresh status"}
                </button>

                {solution.status !== "archived" ? (
                  <Link
                    href={`/builder?solutionId=${solution.id}`}
                    style={{
                      background: "#6d4aff",
                      color: "white",
                      padding: "12px 16px",
                      borderRadius: 12,
                      fontWeight: 800,
                      textDecoration: "none",
                      whiteSpace: "nowrap",
                    }}
                  >
                    Open Builder
                  </Link>
                ) : (
                  <span
                    style={{
                      background: "#f2f4f7",
                      color: "#667085",
                      padding: "12px 16px",
                      borderRadius: 12,
                      fontWeight: 800,
                      whiteSpace: "nowrap",
                    }}
                  >
                    Archived read-only
                  </span>
                )}
              </div>
            </div>

            {syncSummary && (
              <div
                style={{
                  marginTop: 18,
                  padding: 14,
                  borderRadius: 14,
                  background: "#f8fafc",
                  color: "#344054",
                }}
              >
                Status refresh complete:{" "}
                <strong>{syncSummary.updated}</strong> updated,{" "}
                <strong>{syncSummary.unchanged}</strong> unchanged,{" "}
                <strong>{syncSummary.failed}</strong> failed to sync.
              </div>
            )}

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(6, 1fr)",
                gap: 16,
                marginTop: 24,
              }}
            >
              <Info label="Solution status" value={solution.status} />
              <Info
                label="Services"
                value={String(countServiceNodes(solution.nodes))}
              />
              <Info label="Service connections" value={String(countServiceConnections(solution.nodes, solution.edges))} />
              <Info
                label="Deployments"
                value={String(sortedDeployments.length)}
              />
              <Info label="Success rate" value={`${successRate}%`} />
              <Info label="Last updated" value={formatDate(solution.updated_at)} />
            </div>
          </section>

          <section
            className="card"
            style={{
              padding: 30,
              marginTop: 20,
              display: "grid",
              gridTemplateColumns: "1.2fr 1fr",
              gap: 20,
            }}
          >
            <div>
              <h2 style={{ marginTop: 0 }}>Latest run</h2>

              {!latestDeployment && (
                <div
                  style={{
                    padding: 18,
                    borderRadius: 14,
                    background: "#f8fafc",
                    color: "#667085",
                  }}
                >
                  This solution has not been deployed yet.
                </div>
              )}

              {latestDeployment && (
                <div
                  style={{
                    padding: 18,
                    borderRadius: 16,
                    background: statusBackground(latestDeployment.status),
                    border: "1px solid #d6dee9",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 14,
                      alignItems: "flex-start",
                    }}
                  >
                    <div>
                      <span
                        className="badge"
                        style={statusBadgeStyle(latestDeployment.status)}
                      >
                        {latestDeployment.status}
                      </span>

                      <div
                        style={{
                          marginTop: 12,
                          fontFamily: "monospace",
                          fontWeight: 800,
                          color: "#0f172a",
                        }}
                      >
                        {latestDeployment.workflow_id}
                      </div>

                      <div style={{ color: "#526173", marginTop: 8 }}>
                        Created {formatDate(latestDeployment.created_at)}
                      </div>
                    </div>

                    <Link
                      href={`/deployments/${latestDeployment.workflow_id}`}
                      style={{
                        color: "#075985",
                        fontWeight: 800,
                        whiteSpace: "nowrap",
                      }}
                    >
                      Open latest →
                    </Link>
                  </div>
                </div>
              )}
            </div>

            <div>
              <h2 style={{ marginTop: 0 }}>Run health</h2>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: 12,
                }}
              >
                <HealthCard label="Completed" value={completedCount} tone="good" />
                <HealthCard label="Failed" value={failedCount} tone="bad" />
                <HealthCard label="Running" value={runningCount} tone="neutral" />
              </div>

              <div
                style={{
                  marginTop: 14,
                  padding: 14,
                  borderRadius: 14,
                  background: "#f8fafc",
                  color: "#526173",
                  lineHeight: 1.6,
                }}
              >
                Deployment records are linked to this solution and synchronized
                with the orchestrator status. Archived deployments are hidden
                from this active history but retained for audit.
              </div>
            </div>
          </section>

          <section
            className="card"
            style={{
              padding: 30,
              marginTop: 20,
              border: "1px solid #e8e4f4",
              boxShadow: "0 14px 34px rgba(44, 36, 86, 0.05)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 16,
              }}
            >
              <h2 style={{ margin: 0 }}>Workflow diagram</h2>

              <span style={{ color: "#667085", fontSize: 14 }}>
                Read-only preview
              </span>
            </div>

            <div
              style={{
                height: 340,
                border: "1px solid #e4e9f2",
                borderRadius: 16,
                overflow: "hidden",
                background: "#f8fafc",
              }}
            >
              <ReactFlow
                nodes={solution.nodes}
                edges={solution.edges}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
                fitView
              >
                <Background />
                <Controls />
                <MiniMap />
              </ReactFlow>
            </div>
          </section>

          <section
            className="card"
            style={{
              padding: 30,
              marginTop: 20,
              border: "1px solid #e8e4f4",
              boxShadow: "0 14px 34px rgba(44, 36, 86, 0.05)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 16,
                alignItems: "center",
                marginBottom: 16,
              }}
            >
              <div>
                <h2 style={{ margin: 0 }}>Deployment history</h2>
                <p style={{ color: "#667085", marginBottom: 0 }}>
                  Active orchestrator runs created from this saved solution.
                  Archive old debug runs without deleting audit history.
                </p>
              </div>

              <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
  <Link
    href={`/deployments/archived?solutionId=${solution.id}`}
    style={{
      color: "#475467",
      fontWeight: 800,
      whiteSpace: "nowrap",
      textDecoration: "none",
    }}
  >
    View archived deployments →
  </Link>

  {latestDeployment && (
    <Link
      href={`/deployments/${latestDeployment.workflow_id}`}
      style={{
        color: "#075985",
        fontWeight: 800,
        whiteSpace: "nowrap",
        textDecoration: "none",
      }}
    >
      Open latest deployment →
    </Link>
  )}
</div>

            </div>

            {sortedDeployments.length === 0 && (
              <div
                style={{
                  padding: 18,
                  borderRadius: 14,
                  background: "#f8fafc",
                  color: "#667085",
                }}
              >
                No active deployments linked to this solution. Open it in
                Builder and submit it to the orchestrator, or check archived
                deployments.
              </div>
            )}

            {sortedDeployments.length > 0 && (
              <div
                style={{
                  border: "1px solid #e4e9f2",
                  borderRadius: 16,
                  overflow: "hidden",
                }}
              >
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead style={{ background: "#f8fafc" }}>
                    <tr>
                      <Th>Workflow ID</Th>
                      <Th>Status</Th>
                      <Th>Created</Th>
                      <Th>Updated</Th>
                      <Th>Actions</Th>
                    </tr>
                  </thead>

                  <tbody>
                    {sortedDeployments.map((deployment) => (
                      <tr
                        key={deployment.id}
                        style={{ borderTop: "1px solid #e4e9f2" }}
                      >
                        <Td>
                          <span style={{ fontFamily: "monospace" }}>
                            {deployment.workflow_id}
                          </span>
                        </Td>

                        <Td>
                          <span
                            className="badge"
                            style={statusBadgeStyle(deployment.status)}
                          >
                            {deployment.status}
                          </span>
                        </Td>

                        <Td>{formatDate(deployment.created_at)}</Td>
                        <Td>{formatDate(deployment.updated_at)}</Td>

                        <Td>
                          <div
                            style={{
                              display: "flex",
                              gap: 12,
                              flexWrap: "wrap",
                              alignItems: "center",
                            }}
                          >
                            <Link
                              href={`/deployments/${deployment.workflow_id}`}
                              style={{
                                color: "#075985",
                                fontWeight: 800,
                                textDecoration: "none",
                              }}
                            >
                              View →
                            </Link>

                            <button
                              onClick={() => archiveDeployment(deployment.id)}
                              disabled={
                                archivingId === deployment.id ||
                                solution.status === "archived"
                              }
                              style={{
                                border: "none",
                                background: "transparent",
                                color:
                                  solution.status === "archived"
                                    ? "#98a2b3"
                                    : "#b42318",
                                fontWeight: 800,
                                cursor:
                                  archivingId === deployment.id ||
                                  solution.status === "archived"
                                    ? "not-allowed"
                                    : "pointer",
                                padding: 0,
                              }}
                            >
                              {archivingId === deployment.id
                                ? "Archiving..."
                                : "Archive"}
                            </button>
                          </div>
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        background: "rgba(255, 255, 255, 0.88)",
        padding: 16,
        borderRadius: 14,
        border: "1px solid #e8e4f4",
      }}
    >
      <div style={{ color: "#667085", fontSize: 13 }}>{label}</div>
      <strong>{value}</strong>
    </div>
  );
}

function HealthCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "good" | "bad" | "neutral";
}) {
  const background =
    tone === "good" ? "#ecfdf3" : tone === "bad" ? "#fef3f2" : "#f8fafc";

  const color =
    tone === "good" ? "#027a48" : tone === "bad" ? "#b42318" : "#344054";

  return (
    <div
      style={{
        background,
        color,
        padding: 16,
        borderRadius: 14,
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 26, fontWeight: 900 }}>{value}</div>
      <div style={{ fontSize: 13, marginTop: 4 }}>{label}</div>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ textAlign: "left", padding: 16 }}>{children}</th>;
}

function Td({ children }: { children: React.ReactNode }) {
  return <td style={{ padding: 16, color: "#344054" }}>{children}</td>;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function statusBackground(status: string) {
  if (status === "completed") {
    return "#ecfdf3";
  }

  if (status === "failed") {
    return "#fef3f2";
  }

  return "#f8fafc";
}

function statusBadgeStyle(status: string) {
  if (status === "completed") {
    return {
      background: "#dcfae6",
      color: "#027a48",
    };
  }

  if (status === "failed") {
    return {
      background: "#fee4e2",
      color: "#b42318",
    };
  }

  if (status === "running") {
    return {
      background: "#e0f2fe",
      color: "#075985",
    };
  }

  return {};
}

function solutionStatusBadgeStyle(status: string) {
  const normalized = status.toLowerCase();

  if (normalized === "archived") {
    return { background: "#f2f4f7", color: "#475467" };
  }

  if (normalized === "submitted" || normalized === "running") {
    return { background: "#eaf2ff", color: "#2457a6" };
  }

  return { background: "#eee8ff", color: "#6941c6" };
}
