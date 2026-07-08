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
  error?: string;
};

function getApiBaseUrls() {
  if (process.env.INTERNAL_API_URL) {
    return [process.env.INTERNAL_API_URL];
  }

  return ["http://api:8080", "http://localhost:18080"];
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

      return {
        solutions: Array.isArray(data) ? data : [],
      };
    } catch {
      continue;
    }
  }

  return {
    solutions: [],
    error:
      "Could not load saved solutions. The web app could not reach the Solution Studio API.",
  };
}

export default async function SolutionsPage() {
  const { solutions, error } = await getSolutions();

  return (
    <div className="page">
      <span className="badge">AI Vendor Workspace</span>

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
          <p style={{ color: "#526173", fontSize: 17, maxWidth: 950 }}>
            Reopen saved workflow designs, inspect operational health, edit them
            in the Builder, validate them, and submit them to the orchestrator.
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
      background: "#075985",
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
        <section className="card" style={{ marginTop: 28, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#f8fafc" }}>
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
                      <span className="badge">{solution.status}</span>
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
                          color: "#075985",
                          fontWeight: 800,
                          textDecoration: "none",
                          whiteSpace: "nowrap",
                        }}
                      >
                        Open workspace →
                      </Link>

                      <Link
                        href={`/builder?solutionId=${solution.id}`}
                        style={{
                          color: "#475467",
                          fontWeight: 800,
                          textDecoration: "none",
                        }}
                      >
                        Edit
                      </Link>
                      <form action={archiveSolutionAction}>
  <input type="hidden" name="solutionId" value={solution.id} />
  <button
    type="submit"
    style={{
      border: "none",
      background: "transparent",
      color: "#b42318",
      fontWeight: 800,
      cursor: "pointer",
      padding: 0,
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