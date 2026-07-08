"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type Deployment = {
  id: string;
  workflow_id: string;
  solution_id?: string | null;
  status: string;
  name: string;
  is_archived?: boolean;
  created_at: string;
  updated_at: string;
};

type SyncSummary = {
  total: number;
  updated: number;
  unchanged: number;
  failed: number;
};

export default function DeploymentsPage() {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [archivingId, setArchivingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [syncSummary, setSyncSummary] = useState<SyncSummary | null>(null);

  async function loadDeployments() {
    const res = await fetch("http://localhost:18080/deployments");

    if (!res.ok) {
      throw new Error("Failed to load deployments.");
    }

    const data = await res.json();
    setDeployments(Array.isArray(data) ? data : []);
  }

  async function syncStatuses() {
    setSyncing(true);
    setSyncSummary(null);
    setError("");

    try {
      const syncRes = await fetch(
        "http://localhost:18080/deployments/sync-statuses",
        {
          method: "POST",
        }
      );

      if (!syncRes.ok) {
        throw new Error("Failed to sync deployment statuses.");
      }

      const summary = await syncRes.json();
      setSyncSummary(summary);

      await loadDeployments();
    } catch {
      setError("Could not sync deployment statuses from the orchestrator.");
    } finally {
      setSyncing(false);
    }
  }

  async function archiveDeployment(deploymentId: string) {
    const confirmed = window.confirm(
      "Archive this deployment? It will be hidden from the active deployments page but kept for audit history."
    );

    if (!confirmed) {
      return;
    }

    setArchivingId(deploymentId);
    setError("");

    try {
      const res = await fetch(
        `http://localhost:18080/deployments/${deploymentId}/archive`,
        {
          method: "PUT",
        }
      );

      if (!res.ok) {
        throw new Error("Failed to archive deployment.");
      }

      await loadDeployments();
    } catch {
      setError("Could not archive deployment.");
    } finally {
      setArchivingId(null);
    }
  }

  useEffect(() => {
    async function init() {
      try {
        await syncStatuses();
      } catch {
        try {
          await loadDeployments();
        } catch {
          setError("Could not load deployments from the backend.");
        }
      } finally {
        setLoading(false);
      }
    }

    init();
  }, []);

  return (
    <div className="page">
      <span className="badge">Execution Monitoring</span>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 20,
          alignItems: "flex-start",
        }}
      >
        <div>
          <h1 style={{ fontSize: 40, marginBottom: 8 }}>Deployments</h1>
          <p style={{ color: "#526173", fontSize: 17, maxWidth: 900 }}>
            Track active workflows submitted from Solution Studio to the
            orchestrator. Archive old test runs without deleting audit history.
          </p>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link
            href="/deployments/archived"
            style={{
              border: "1px solid #d0d5dd",
              color: "#344054",
              background: "white",
              borderRadius: 12,
              padding: "12px 16px",
              fontWeight: 800,
              textDecoration: "none",
              whiteSpace: "nowrap",
            }}
          >
            Archived
          </Link>

          <button
            onClick={syncStatuses}
            disabled={syncing}
            style={{
              border: "1px solid #bae6fd",
              background: syncing ? "#f8fafc" : "white",
              color: "#075985",
              borderRadius: 12,
              padding: "12px 16px",
              fontWeight: 800,
              cursor: syncing ? "not-allowed" : "pointer",
              whiteSpace: "nowrap",
            }}
          >
            {syncing ? "Refreshing..." : "Refresh statuses"}
          </button>
        </div>
      </div>

      {syncSummary && (
        <div
          className="card"
          style={{
            marginTop: 20,
            padding: 18,
            background: "#f8fafc",
            color: "#344054",
          }}
        >
          Status sync complete: <strong>{syncSummary.updated}</strong> updated,{" "}
          <strong>{syncSummary.unchanged}</strong> unchanged,{" "}
          <strong>{syncSummary.failed}</strong> failed to sync.
        </div>
      )}

      <div className="card" style={{ marginTop: 28, overflow: "hidden" }}>
        {loading && (
          <div style={{ padding: 24, color: "#667085" }}>
            Loading deployments...
          </div>
        )}

        {error && <div style={{ padding: 24, color: "#b42318" }}>{error}</div>}

        {!loading && !error && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#f8fafc" }}>
              <tr>
                <Th>Name</Th>
                <Th>Workflow ID</Th>
                <Th>Status</Th>
                <Th>Created</Th>
                <Th>Updated</Th>
                <Th>Actions</Th>
              </tr>
            </thead>

            <tbody>
              {deployments.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: 24, color: "#667085" }}>
                    No active deployments. Submit a workflow from the Builder or
                    check archived deployments.
                  </td>
                </tr>
              )}

              {deployments.map((deployment) => (
                <tr
                  key={deployment.id}
                  style={{ borderTop: "1px solid #e4e9f2" }}
                >
                  <Td>
                    <strong>{deployment.name}</strong>
                    <div style={{ color: "#667085", fontSize: 13, marginTop: 4 }}>
                      {deployment.solution_id
                        ? `Solution: ${deployment.solution_id}`
                        : "No linked solution"}
                    </div>
                  </Td>

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
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
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
                        disabled={archivingId === deployment.id}
                        style={{
                          border: "none",
                          background: "transparent",
                          color: "#b42318",
                          fontWeight: 800,
                          cursor:
                            archivingId === deployment.id
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
        )}
      </div>
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