"use client";

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

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 20,
          alignItems: "flex-start",
        }}
      >
        <div>
          <h1 className="page-header__title">Runs</h1>
          <p className="page-header__lead">
            Every workflow you deployed, its status and its results.
          </p>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Link
            href="/deployments/archived"
            style={{
              border: "1px solid #d0d5dd",
              color: "var(--ink-900)",
              background: "white",
              borderRadius: 8,
              padding: "12px 16px",
              fontWeight: 600,
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
              background: syncing ? "var(--surface-sunken)" : "#6d4aff",
              color: syncing ? "var(--brand-600)" : "white",
              borderRadius: 8,
              padding: "12px 16px",
              fontWeight: 600,
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
            background: "var(--surface-sunken)",
            color: "var(--ink-900)",
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
          <div style={{ padding: 24, color: "var(--ink-600)" }}>
            Loading deployments...
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
                <Th>Updated</Th>
                <Th>Actions</Th>
              </tr>
            </thead>

            <tbody>
              {filteredDeployments.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: 24, color: "var(--ink-600)" }}>
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
                          color: "white",
                          background: "#6d4aff",
                          fontWeight: 600,
                          textDecoration: "none",
                          padding: "8px 11px",
                          borderRadius: 9,
                          fontSize: 13,
                        }}
                      >
                        View run details
                      </Link>

                      <button
                        onClick={() => archiveDeployment(deployment.id)}
                        disabled={archivingId === deployment.id}
                        style={{
                          border: "1px solid #fecdca",
                          background: "white",
                          color: "var(--danger-600)",
                          fontWeight: 600,
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
    blue: { background: "#eef5ff", color: "var(--brand-600)", accent: "#4f7cff" },
    good: { background: "#effbf4", color: "var(--success-600)", accent: "#12b76a" },
    bad: { background: "#fff2f1", color: "var(--danger-600)", accent: "#f04438" },
    muted: { background: "#f7f7fb", color: "var(--ink-600)", accent: "var(--ink-400)" },
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
        <span style={{ color: "var(--ink-600)", fontSize: 13, fontWeight: 700 }}>
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
          fontWeight: 600,
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
  return <td style={{ padding: 16, color: "var(--ink-900)" }}>{children}</td>;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

function statusBadgeStyle(status: string) {
  if (status === "completed") {
    return {
      background: "var(--mint-100)",
      color: "var(--success-600)",
    };
  }

  if (status === "failed") {
    return {
      background: "var(--danger-100)",
      color: "var(--danger-600)",
    };
  }

  if (status === "running") {
    return {
      background: "var(--brand-50)",
      color: "var(--brand-600)",
    };
  }

  return {};
}
