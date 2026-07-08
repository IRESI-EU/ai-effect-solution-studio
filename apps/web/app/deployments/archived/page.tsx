"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

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

export default function ArchivedDeploymentsPage() {
  const searchParams = useSearchParams();
  const solutionId = searchParams.get("solutionId");

  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const archivedUrl = useMemo(() => {
    const params = new URLSearchParams();
    params.set("archived_only", "true");

    if (solutionId) {
      params.set("solution_id", solutionId);
    }

    return `http://localhost:18080/deployments?${params.toString()}`;
  }, [solutionId]);

  async function loadArchivedDeployments() {
    const res = await fetch(archivedUrl);

    if (!res.ok) {
      throw new Error("Failed to load archived deployments.");
    }

    const data = await res.json();
    setDeployments(Array.isArray(data) ? data : []);
  }

  async function restoreDeployment(deploymentId: string) {
    setRestoringId(deploymentId);
    setError("");

    try {
      const res = await fetch(
        `http://localhost:18080/deployments/${deploymentId}/restore`,
        {
          method: "PUT",
        }
      );

      if (!res.ok) {
        throw new Error("Failed to restore deployment.");
      }

      await loadArchivedDeployments();
    } catch {
      setError("Could not restore deployment.");
    } finally {
      setRestoringId(null);
    }
  }

  useEffect(() => {
    async function init() {
      try {
        await loadArchivedDeployments();
      } catch {
        setError("Could not load archived deployments from the backend.");
      } finally {
        setLoading(false);
      }
    }

    init();
  }, [archivedUrl]);

  return (
    <div className="page">
      <Link href="/deployments" style={{ color: "#075985", fontWeight: 800 }}>
        ← Back to active deployments
      </Link>

      <div style={{ marginTop: 24 }}>
        <span className="badge">Deployment Lifecycle</span>

        <h1 style={{ fontSize: 40, marginBottom: 8 }}>
          Archived deployments
        </h1>

        <p style={{ color: "#526173", fontSize: 17, maxWidth: 950 }}>
          {solutionId
            ? "Showing archived deployments for the selected solution."
            : "Archived deployments are hidden from operational monitoring but kept for audit, traceability, and historical review."}
        </p>

        {solutionId && (
          <div
            style={{
              marginTop: 12,
              color: "#667085",
              fontFamily: "monospace",
              fontSize: 13,
            }}
          >
            Solution: {solutionId}
          </div>
        )}
      </div>

      <div className="card" style={{ marginTop: 28, overflow: "hidden" }}>
        {loading && (
          <div style={{ padding: 24, color: "#667085" }}>
            Loading archived deployments...
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
                <Th>Archived / Updated</Th>
                <Th>Actions</Th>
              </tr>
            </thead>

            <tbody>
              {deployments.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: 24, color: "#667085" }}>
                    No archived deployments found.
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
                        onClick={() => restoreDeployment(deployment.id)}
                        disabled={restoringId === deployment.id}
                        style={{
                          border: "1px solid #bae6fd",
                          background: "white",
                          color: "#075985",
                          padding: "8px 10px",
                          borderRadius: 10,
                          fontWeight: 800,
                          cursor:
                            restoringId === deployment.id
                              ? "not-allowed"
                              : "pointer",
                        }}
                      >
                        {restoringId === deployment.id
                          ? "Restoring..."
                          : "Restore"}
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