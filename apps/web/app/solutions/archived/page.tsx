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

  return ["http://api:8080"];
}

async function getArchivedSolutions(): Promise<SolutionsResult> {
  const urls = getApiBaseUrls();

  for (const baseUrl of urls) {
    try {
      const res = await fetch(
        `${baseUrl}/solutions/summary?archived_only=true`,
        {
          cache: "no-store",
        }
      );

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
      "Could not load archived solutions. The web app could not reach the Solution Studio API.",
  };
}

export default async function ArchivedSolutionsPage() {
  const { solutions, error } = await getArchivedSolutions();

  return (
    <div className="page">
      <Link href="/solutions" style={{ color: "#075985", fontWeight: 800 }}>
        ← Back to active solutions
      </Link>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 20,
          alignItems: "flex-start",
          marginTop: 24,
        }}
      >
        <div>
          <span className="badge">Lifecycle Management</span>

          <h1 style={{ fontSize: 40, marginBottom: 8 }}>
            Archived solutions
          </h1>

          <p style={{ color: "#526173", fontSize: 17, maxWidth: 950 }}>
            Archived solutions are hidden from the active workspace but retain
            their deployment history, workflow records, and audit trail.
          </p>
        </div>
      </div>

      {!error && (
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
            <div style={{ color: "#667085", fontSize: 13, fontWeight: 700 }}>
              Archived solutions
            </div>
            <div style={{ color: "#4d2ca3", fontSize: 32, fontWeight: 900, marginTop: 6 }}>
              {solutions.length}
            </div>
          </div>
          <div
            className="card"
            style={{
              padding: 20,
              display: "flex",
              alignItems: "center",
              color: "#526173",
              border: "1px solid #e8e4f4",
            }}
          >
            Restore a solution to return it to the active workspace and Builder.
            Historical deployments remain linked throughout the lifecycle.
          </div>
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
          <strong>Unable to load archived solutions</strong>
          <p style={{ marginBottom: 0 }}>{error}</p>
        </section>
      )}

      {!error && solutions.length === 0 && (
        <section className="card" style={{ padding: 30, marginTop: 28 }}>
          <h2 style={{ marginTop: 0 }}>No archived solutions</h2>
          <p style={{ color: "#526173", marginBottom: 0 }}>
            Archived solutions will appear here when you archive them from the
            active solutions list.
          </p>
        </section>
      )}

      {!error && solutions.length > 0 && (
        <section
          className="card"
          style={{
            marginTop: 22,
            overflow: "hidden",
            border: "1px solid #e8e4f4",
            boxShadow: "0 16px 40px rgba(44, 36, 86, 0.06)",
          }}
        >
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead style={{ background: "#faf9ff" }}>
              <tr>
                <Th>Name</Th>
                <Th>Design</Th>
                <Th>Deployments</Th>
                <Th>Latest run</Th>
                <Th>Archived</Th>
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
                        style={{ background: "#f2f4f7", color: "#344054" }}
                      >
                        archived
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
                    <div style={{ display: "grid", gap: 6 }}>
                      <span>{formatDate(solution.updated_at)}</span>
                      <span style={{ color: "#667085", fontSize: 13 }}>
                        Archived / restored state changed
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

                      <form action={restoreSolutionAction}>
                        <input
                          type="hidden"
                          name="solutionId"
                          value={solution.id}
                        />
                        <button
                          type="submit"
                          style={{
                            border: "1px solid #6d4aff",
                            background: "#6d4aff",
                            color: "white",
                            padding: "8px 10px",
                            borderRadius: 10,
                            fontWeight: 800,
                            cursor: "pointer",
                          }}
                        >
                          Restore
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

async function restoreSolutionAction(formData: FormData) {
  "use server";

  const solutionId = String(formData.get("solutionId") || "");

  if (!solutionId) {
    return;
  }

  const urls = getApiBaseUrls();

  for (const baseUrl of urls) {
    try {
      const res = await fetch(`${baseUrl}/solutions/${solutionId}/restore`, {
        method: "PUT",
      });

      if (res.ok) {
        revalidatePath("/solutions");
        revalidatePath("/solutions/archived");
        redirect("/solutions/archived");
      }
    } catch {
      continue;
    }
  }

  revalidatePath("/solutions");
  revalidatePath("/solutions/archived");
  redirect("/solutions/archived");
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
