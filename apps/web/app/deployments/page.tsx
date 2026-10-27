"use client";

import { deploymentResultsUrl } from "../../lib/experiment-journey";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [archivedCount, setArchivedCount] = useState(0);

  async function loadDeployments() {
    const [res, archivedRes] = await Promise.all([
      fetch("/api/deployments"),
      fetch("/api/deployments?archived_only=true"),
    ]);

    if (!res.ok) {
      throw new Error("Failed to load deployments.");
    }

    const data = await res.json();
    setDeployments(Array.isArray(data) ? data : []);

    if (archivedRes.ok) {
      const archivedData = await archivedRes.json();
      setArchivedCount(Array.isArray(archivedData) ? archivedData.length : 0);
    }
  }

  async function syncStatuses() {
    setSyncing(true);
    setSyncSummary(null);
    setError("");

    try {
      const syncRes = await fetch(
        "/api/deployments/sync-statuses",
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
        `/api/deployments/${deploymentId}/archive`,
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

  const statusCounts = useMemo(() => {
    const normalized = deployments.map((deployment) =>
      deployment.status.toLowerCase()
    );

    return {
      running: normalized.filter((status) => status === "running").length,
      completed: normalized.filter((status) => status === "completed").length,
      failed: normalized.filter((status) => status === "failed").length,
    };
  }, [deployments]);

  const filteredDeployments = useMemo(() => {
    const query = search.trim().toLowerCase();

    return deployments.filter((deployment) => {
      const matchesStatus =
        statusFilter === "all" ||
        deployment.status.toLowerCase() === statusFilter;
      const matchesSearch =
        !query ||
        deployment.name.toLowerCase().includes(query) ||
        deployment.workflow_id.toLowerCase().includes(query) ||
        deployment.solution_id?.toLowerCase().includes(query);

      return matchesStatus && Boolean(matchesSearch);
    });
  }, [deployments, search, statusFilter]);

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
          <p style={{ color: "#526173", fontSize: 17, maxWidth: 760 }}>
            Track submitted workflows, execution states, and orchestrator
            results.
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
              border: "1px solid #d7ceff",
              background: syncing ? "#f8f7fc" : "#6d4aff",
              color: syncing ? "#6941c6" : "white",
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

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
          gap: 14,
          marginTop: 26,
        }}
      >
        <MetricCard label="Total deployments" value={deployments.length} />
        <MetricCard label="Running" value={statusCounts.running} tone="blue" />
        <MetricCard
          label="Completed"
          value={statusCounts.completed}
          tone="good"
        />
        <MetricCard label="Failed" value={statusCounts.failed} tone="bad" />
        <MetricCard label="Archived" value={archivedCount} tone="muted" />
      </section>

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

      <section
        className="card"
        style={{
          marginTop: 22,
          padding: 16,
          display: "flex",
          gap: 12,
          alignItems: "center",
          border: "1px solid #e8e4f4",
        }}
      >
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search deployments by name, workflow or solution..."
          style={{ flex: 1, minWidth: 240 }}
        />
        <select
          value={statusFilter}
          onChange={(event) => setStatusFilter(event.target.value)}
          style={{ minWidth: 170 }}
        >
          <option value="all">All statuses</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </section>

      <div
        className="card"
        style={{
          marginTop: 18,
          overflow: "hidden",
          border: "1px solid #e8e4f4",
          boxShadow: "0 16px 40px rgba(44, 36, 86, 0.06)",
        }}
      >
        {loading && (
          <div style={{ padding: 24, color: "#667085" }}>
            Loading deployments...
          </div>
        )}

        {error && <div style={{ padding: 24, color: "#b42318" }}>{error}</div>}

        {!loading && !error && (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#faf9ff" }}>
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
              {filteredDeployments.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: 24, color: "#667085" }}>
                    No deployments match the current view. Submit a workflow
                    from the Builder or check archived deployments.
                  </td>
                </tr>
              )}

              {filteredDeployments.map((deployment) => (
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
                        href={deploymentResultsUrl(deployment.workflow_id)}
                        style={{
                          color: "white",
                          background: "#6d4aff",
                          fontWeight: 800,
                          textDecoration: "none",
                          padding: "8px 11px",
                          borderRadius: 9,
                          fontSize: 13,
                        }}
                      >
                        View results
                      </Link>

                      <button
                        onClick={() => archiveDeployment(deployment.id)}
                        disabled={archivingId === deployment.id}
                        style={{
                          border: "1px solid #fecdca",
                          background: "white",
                          color: "#b42318",
                          fontWeight: 800,
                          cursor:
                            archivingId === deployment.id
                              ? "not-allowed"
                              : "pointer",
                          padding: "8px 11px",
                          borderRadius: 9,
                          fontSize: 13,
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

function MetricCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number | string;
  tone?: "neutral" | "blue" | "good" | "bad" | "muted";
}) {
  const tones = {
    neutral: { background: "#ffffff", color: "#17152b", accent: "#6d4aff" },
    blue: { background: "#eef5ff", color: "#2457a6", accent: "#4f7cff" },
    good: { background: "#effbf4", color: "#027a48", accent: "#12b76a" },
    bad: { background: "#fff2f1", color: "#b42318", accent: "#f04438" },
    muted: { background: "#f7f7fb", color: "#475467", accent: "#98a2b3" },
  };
  const selected = tones[tone];

  return (
    <div
      className="card"
      style={{
        padding: 17,
        background: selected.background,
        border: "1px solid #e8e4f4",
        boxShadow: "0 10px 26px rgba(44, 36, 86, 0.05)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
        <span style={{ color: "#667085", fontSize: 13, fontWeight: 700 }}>
          {label}
        </span>
        <span
          style={{
            width: 9,
            height: 9,
            borderRadius: 99,
            background: selected.accent,
            marginTop: 4,
          }}
        />
      </div>
      <div
        style={{
          color: selected.color,
          fontSize: typeof value === "number" ? 29 : 20,
          fontWeight: 900,
          marginTop: 8,
        }}
      >
        {value}
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
