"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
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
  return (
    <Suspense
      fallback={
        <div className="page">
          <section className="card" style={{ padding: 30 }}>
            Loading archived deployments...
          </section>
        </div>
      }
    >
      <ArchivedDeploymentsContent />
    </Suspense>
  );
}

function ArchivedDeploymentsContent() {
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

    return `/api/deployments?${params.toString()}`;
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
        `/api/deployments/${deploymentId}/restore`,
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
      <Link href="/deployments" style={{ color: "#075985", fontWeight: 600 }}>
        ← Back to active deployments
      </Link>

      <div style={{ marginTop: 24 }}>
        <h1 className="page-header__title">
          Archived deployments
        </h1>

        <p className="page-header__lead">
          {solutionId
            ? "Showing archived deployments for the selected solution."
            : "Archived deployments are hidden from operational monitoring but kept for audit, traceability, and historical review."}
        </p>

        {solutionId && (
          <div
            style={{
              marginTop: 12,
              color: "var(--ink-600)",
              fontFamily: "monospace",
              fontSize: 13,
            }}
          >
            Solution: {solutionId}
          </div>
        )}
      </div>

      {!loading && !error && (
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "minmax(220px, 0.35fr) minmax(0, 1fr)",
            gap: 16,
            marginTop: 26,
          }}
        >
          <div
            className="card"
            style={{
              padding: 20,
              background: "#f5f1ff",
              border: "1px solid #ded5ff",
            }}
          >
            <div style={{ color: "var(--ink-600)", fontSize: 13, fontWeight: 700 }}>
              Archived deployments
            </div>
            <div style={{ color: "#4d2ca3", fontSize: 32, fontWeight: 600, marginTop: 6 }}>
              {deployments.length}
            </div>
          </div>
          <div
            className="card"
            style={{
              padding: 20,
              display: "flex",
              alignItems: "center",
              color: "var(--ink-600)",
              border: "1px solid #e8e4f4",
            }}
          >
            Restore a deployment to return it to operational monitoring while
            keeping the same workflow ID and audit history.
          </div>
        </section>
      )}

      <div
        className="card"
        style={{
          marginTop: 22,
          overflow: "hidden",
          border: "1px solid #e8e4f4",
          boxShadow: "0 16px 40px rgba(44, 36, 86, 0.06)",
        }}
      >
        {loading && (
          <div style={{ padding: 24, color: "var(--ink-600)" }}>
            Loading archived deployments...
          </div>
        )}

        {error && <div style={{ padding: 24, color: "var(--danger-600)" }}>{error}</div>}

        {!loading && !error && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#faf9ff" }}>
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
                  <td colSpan={6} style={{ padding: 24, color: "var(--ink-600)" }}>
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
                    <div style={{ color: "var(--ink-600)", fontSize: 13, marginTop: 4 }}>
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
                          fontWeight: 600,
                          textDecoration: "none",
                        }}
                      >
                        View run details
                      </Link>

                      <button
                        onClick={() => restoreDeployment(deployment.id)}
                        disabled={restoringId === deployment.id}
                        style={{
                          border: "1px solid #6d4aff",
                          background: "#6d4aff",
                          color: "white",
                          padding: "8px 10px",
                          borderRadius: 10,
                          fontWeight: 600,
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
  return <td style={{ padding: 16, color: "var(--ink-900)" }}>{children}</td>;
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
      color: "var(--danger-600)",
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
