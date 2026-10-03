import Link from "next/link";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";
export const revalidate = 0;

type SolutionSummary = {
  id: string;
  name: string;
  description?: string | null;
  status: string;
  services_count: number;
  connections_count: number;
  deployments_count: number;
  completed_deployments_count: number;
  failed_deployments_count: number;
  running_deployments_count: number;
  latest_workflow_id?: string | null;
  latest_deployment_status?: string | null;
  latest_deployment_created_at?: string | null;
  created_at: string;
  updated_at: string;
};

type SolutionsResult = {
  solutions: SolutionSummary[];
  archivedCount: number;
  error?: string;
};

function getApiBaseUrls() {
  if (process.env.INTERNAL_API_URL) {
    return [process.env.INTERNAL_API_URL];
  }

  return ["http://api:8080"];
}

async function getSolutions(): Promise<SolutionsResult> {
  const urls = getApiBaseUrls();

  for (const baseUrl of urls) {
    try {
      const res = await fetch(`${baseUrl}/solutions/summary`, {
        cache: "no-store",
      });

      if (!res.ok) {
        continue;
      }

      const data = await res.json();
      let archivedCount = 0;

      try {
        const archivedRes = await fetch(
          `${baseUrl}/solutions/summary?archived_only=true`,
          { cache: "no-store" }
        );

        if (archivedRes.ok) {
          const archivedData = await archivedRes.json();
          archivedCount = Array.isArray(archivedData) ? archivedData.length : 0;
        }
      } catch {
        archivedCount = 0;
      }

      return {
        solutions: Array.isArray(data) ? data : [],
        archivedCount,
      };
    } catch {
      continue;
    }
  }

  return {
    solutions: [],
    archivedCount: 0,
    error:
      "Could not load saved solutions. The web app could not reach the Solution Studio API.",
  };
}

export default async function SolutionsPage() {
  const { solutions, archivedCount, error } = await getSolutions();
  const draftCount = solutions.filter(
    (solution) => solution.status.toLowerCase() === "draft"
  ).length;
  const submittedCount = solutions.filter((solution) => {
    const status = solution.status.toLowerCase();
    return (
      status === "submitted" ||
      status === "running" ||
      solution.running_deployments_count > 0
    );
  }).length;

  return (
    <div className="page">
      <span className="badge">Solution Workspace</span>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 20,
          alignItems: "flex-start",
        }}
      >
        <div>
          <h1 style={{ fontSize: 40, marginBottom: 8 }}>Saved solutions</h1>
          <p style={{ color: "#526173", fontSize: 17, maxWidth: 760 }}>
            Manage draft and submitted AI-EFFECT workflows composed from
            trusted marketplace services.
          </p>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
  <Link
    href="/solutions/archived"
    style={{
      border: "1px solid #d0d5dd",
      color: "#344054",
      background: "white",
      padding: "12px 16px",
      borderRadius: 12,
      fontWeight: 800,
      textDecoration: "none",
      whiteSpace: "nowrap",
    }}
  >
    Archived
  </Link>

  <Link
    href="/builder"
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
    New solution
  </Link>
</div>
      </div>

      {!error && (
        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
            gap: 16,
            marginTop: 26,
          }}
        >
          <MetricCard label="Total solutions" value={solutions.length} />
          <MetricCard label="Draft" value={draftCount} tone="purple" />
          <MetricCard
            label="Submitted / Running"
            value={submittedCount}
            tone="blue"
          />
          <MetricCard label="Archived" value={archivedCount} tone="muted" />
        </section>
      )}

      {error && (
        <section
          className="card"
          style={{
            padding: 24,
            marginTop: 28,
            background: "#fef3f2",
            color: "#b42318",
          }}
        >
          <strong>Unable to load solutions</strong>
          <p style={{ marginBottom: 0 }}>{error}</p>
        </section>
      )}

      {!error && solutions.length === 0 && (
        <section className="card" style={{ padding: 30, marginTop: 28 }}>
          <h2 style={{ marginTop: 0 }}>No saved solutions yet</h2>
          <p style={{ color: "#526173" }}>
            Create one from the Builder using Save draft.
          </p>

          <Link href="/builder" style={{ color: "#075985", fontWeight: 800 }}>
            Open Builder →
          </Link>
        </section>
      )}

      {!error && solutions.length > 0 && (
        <section
          className="card"
          style={{
            marginTop: 24,
            overflow: "hidden",
            border: "1px solid #e8e4f4",
            boxShadow: "0 16px 40px rgba(44, 36, 86, 0.06)",
          }}
        >
          <div
            style={{
              padding: "20px 22px",
              borderBottom: "1px solid #ece8f5",
              display: "flex",
              justifyContent: "space-between",
              gap: 16,
              alignItems: "center",
            }}
          >
            <div>
              <h2 style={{ margin: 0, fontSize: 20 }}>Solution library</h2>
              <p style={{ margin: "5px 0 0", color: "#667085", fontSize: 14 }}>
                Saved designs and their latest orchestrator activity.
              </p>
            </div>
            <span style={{ color: "#6941c6", fontWeight: 800, fontSize: 14 }}>
              {solutions.length} active
            </span>
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#faf9ff" }}>
              <tr>
                <Th>Name</Th>
                <Th>Design</Th>
                <Th>Deployments</Th>
                <Th>Latest run</Th>
                <Th>Run health</Th>
                <Th>Last Activity</Th>
                <Th>Actions</Th>
              </tr>
            </thead>

            <tbody>
              {solutions.map((solution) => (
                <tr
                  key={solution.id}
                  style={{ borderTop: "1px solid #e4e9f2" }}
                >
                  <Td>
                    <div style={{ fontWeight: 900, color: "#0f172a" }}>
                      {solution.name}
                    </div>

                    <div
                      style={{
                        marginTop: 6,
                        color: "#667085",
                        fontSize: 13,
                        maxWidth: 420,
                      }}
                    >
                      {solution.description || "No description provided."}
                    </div>

                    <div style={{ marginTop: 10 }}>
                      <span
                        className="badge"
                        style={solutionStatusBadgeStyle(solution.status)}
                      >
                        {solution.status}
                      </span>
                    </div>
                  </Td>

                  <Td>
                    <div style={{ display: "grid", gap: 6 }}>
                      <span>
                        <strong>{solution.services_count}</strong> services
                      </span>
                      <span style={{ color: "#667085" }}>
                        {solution.connections_count} connections
                      </span>
                    </div>
                  </Td>

                  <Td>
                    <strong>{solution.deployments_count}</strong>
                  </Td>

                  <Td>
                    {solution.latest_deployment_status ? (
                      <div style={{ display: "grid", gap: 6 }}>
                        <span
                          className="badge"
                          style={statusBadgeStyle(
                            solution.latest_deployment_status
                          )}
                        >
                          {solution.latest_deployment_status}
                        </span>

                        {solution.latest_workflow_id && (
                          <Link
                            href={`/deployments/${solution.latest_workflow_id}`}
                            style={{
                              color: "#075985",
                              fontWeight: 800,
                              fontSize: 13,
                              textDecoration: "none",
                              fontFamily: "monospace",
                            }}
                          >
                            {solution.latest_workflow_id}
                          </Link>
                        )}
                      </div>
                    ) : (
                      <span style={{ color: "#667085" }}>Not deployed</span>
                    )}
                  </Td>

                  <Td>
                    <div
                      style={{
                        display: "flex",
                        gap: 8,
                        flexWrap: "wrap",
                        alignItems: "center",
                      }}
                    >
                      <MiniHealth
                        label="✓"
                        title="Completed deployments"
                        value={solution.completed_deployments_count}
                        tone="good"
                      />

                      <MiniHealth
                        label="✕"
                        title="Failed deployments"
                        value={solution.failed_deployments_count}
                        tone="bad"
                      />

                      <MiniHealth
                        label="•"
                        title="Running deployments"
                        value={solution.running_deployments_count}
                        tone="neutral"
                      />
                    </div>
                  </Td>

                  <Td>
  <div style={{ display: "grid", gap: 6 }}>
    <span>
      {formatDate(solution.latest_deployment_created_at || solution.updated_at)}
    </span>

    <span style={{ color: "#667085", fontSize: 13 }}>
      {solution.latest_deployment_created_at
        ? "Latest deployment"
        : "Design updated"}
    </span>
  </div>
</Td>

                  <Td>
                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                      <Link
                        href={`/solutions/${solution.id}`}
                        style={{
                          color: "white",
                          background: "#6d4aff",
                          fontWeight: 800,
                          textDecoration: "none",
                          whiteSpace: "nowrap",
                          padding: "8px 11px",
                          borderRadius: 9,
                          fontSize: 13,
                        }}
                      >
                        Open workspace →
                      </Link>

                      <Link
                        href={`/builder?solutionId=${solution.id}`}
                        style={{
                          color: "#5f42c7",
                          border: "1px solid #d9d0ff",
                          background: "#faf9ff",
                          fontWeight: 800,
                          textDecoration: "none",
                          padding: "8px 11px",
                          borderRadius: 9,
                          fontSize: 13,
                        }}
                      >
                        Edit in Builder
                      </Link>
                      <form action={archiveSolutionAction}>
  <input type="hidden" name="solutionId" value={solution.id} />
  <button
    type="submit"
    style={{
      border: "1px solid #fecdca",
      background: "white",
      color: "#b42318",
      fontWeight: 800,
      cursor: "pointer",
      padding: "8px 11px",
      borderRadius: 9,
      fontSize: 13,
    }}
  >
    Archive
  </button>
</form>
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}

async function archiveSolutionAction(formData: FormData) {
  "use server";

  const solutionId = String(formData.get("solutionId") || "");

  if (!solutionId) {
    return;
  }

  const urls = getApiBaseUrls();

  for (const baseUrl of urls) {
    try {
      const res = await fetch(`${baseUrl}/solutions/${solutionId}/archive`, {
        method: "PUT",
      });

      if (res.ok) {
        revalidatePath("/solutions");
        revalidatePath("/solutions/archived");
        redirect("/solutions");
      }
    } catch {
      continue;
    }
  }

  revalidatePath("/solutions");
  redirect("/solutions");
}

function MetricCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "purple" | "blue" | "muted";
}) {
  const tones = {
    neutral: { background: "#ffffff", color: "#17152b", accent: "#6d4aff" },
    purple: { background: "#f5f1ff", color: "#4d2ca3", accent: "#8b5cf6" },
    blue: { background: "#eef5ff", color: "#2457a6", accent: "#4f7cff" },
    muted: { background: "#f7f7fb", color: "#475467", accent: "#98a2b3" },
  };
  const selected = tones[tone];

  return (
    <div
      className="card"
      style={{
        padding: 18,
        background: selected.background,
        border: "1px solid #e8e4f4",
        boxShadow: "0 10px 26px rgba(44, 36, 86, 0.05)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
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
          fontSize: 30,
          fontWeight: 900,
          marginTop: 8,
        }}
      >
        {value}
      </div>
    </div>
  );
}


function MiniHealth({
  label,
  title,
  value,
  tone,
}: {
  label: string;
  title: string;
  value: number;
  tone: "good" | "bad" | "neutral";
}) {
  const background =
    tone === "good" ? "#ecfdf3" : tone === "bad" ? "#fef3f2" : "#f8fafc";

  const color =
    tone === "good" ? "#027a48" : tone === "bad" ? "#b42318" : "#344054";

  return (
    <span
      title={title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        background,
        color,
        borderRadius: 999,
        padding: "5px 8px",
        fontWeight: 800,
        fontSize: 13,
      }}
    >
      {label} {value}
    </span>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ textAlign: "left", padding: 16 }}>{children}</th>;
}

function Td({ children }: { children: React.ReactNode }) {
  return (
    <td style={{ padding: 16, color: "#344054", verticalAlign: "top" }}>
      {children}
    </td>
  );
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

function solutionStatusBadgeStyle(status: string) {
  const normalized = status.toLowerCase();

  if (normalized === "submitted" || normalized === "running") {
    return { background: "#eaf2ff", color: "#2457a6" };
  }

  if (normalized === "archived") {
    return { background: "#f2f4f7", color: "#475467" };
  }

  return { background: "#f2edff", color: "#6941c6" };
}
