"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type DeploymentRecord = {
  id: string;
  workflow_id: string;
  solution_id?: string | null;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export default function DeploymentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [workflowId, setWorkflowId] = useState("");
  const [workflow, setWorkflow] = useState<any>(null);
  const [deploymentRecord, setDeploymentRecord] =
    useState<DeploymentRecord | null>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  async function previewReference(ref: any) {
    setPreviewLoading(true);
    setPreview(null);

    try {
      const res = await fetch("http://localhost:18080/data-references/preview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          protocol: ref.protocol,
          uri: ref.uri,
          format: ref.format,
        }),
      });

      if (!res.ok) {
        throw new Error("Preview request failed.");
      }

      const data = await res.json();
      setPreview(data);
    } catch {
      setPreview({
        kind: "error",
        available: false,
        message: "Could not preview this DataReference.",
      });
    } finally {
      setPreviewLoading(false);
    }
  }

  async function syncDeploymentStatus(workflowId: string, status: string) {
    try {
      const deploymentRes = await fetch(
        `http://localhost:18080/deployments/by-workflow/${workflowId}`
      );

      if (!deploymentRes.ok) {
        return;
      }

      const deployment: DeploymentRecord = await deploymentRes.json();
      setDeploymentRecord(deployment);

      if (deployment.status !== status) {
        const updateRes = await fetch(
          `http://localhost:18080/deployments/${deployment.id}`,
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              status,
            }),
          }
        );

        if (updateRes.ok) {
          const updatedDeployment: DeploymentRecord = await updateRes.json();
          setDeploymentRecord(updatedDeployment);
        }
      }
    } catch {
      // Status sync should not block the deployment detail page.
      // The orchestrator remains the source of truth for this view.
    }
  }

  useEffect(() => {
    async function load() {
      const { id } = await params;
      setWorkflowId(id);

      try {
        const workflowRes = await fetch(
          `http://localhost:18080/orchestrator/workflows/${id}`
        );

        if (!workflowRes.ok) {
          throw new Error("Failed to load workflow.");
        }

        const workflowData = await workflowRes.json();
        setWorkflow(workflowData);

        if (workflowData.status) {
          await syncDeploymentStatus(id, workflowData.status);
        }

        const tasksRes = await fetch(
          `http://localhost:18080/orchestrator/workflows/${id}/tasks`
        );

        if (!tasksRes.ok) {
          throw new Error("Failed to load workflow tasks.");
        }

        const tasksData = await tasksRes.json();
        setTasks(tasksData.tasks || []);
      } catch {
        setError("Failed to load deployment details.");
      }
    }

    load();
  }, [params]);

  return (
    <div className="page">
      <Link href="/deployments" style={{ color: "#075985", fontWeight: 800 }}>
        ← Back to deployments
      </Link>

      <section className="card" style={{ padding: 30, marginTop: 20 }}>
        <span className="badge">Orchestrator Deployment</span>
        <h1 style={{ fontSize: 40 }}>Workflow {workflowId}</h1>

        {error && <p style={{ color: "#b42318" }}>{error}</p>}

        {workflow && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 16,
            }}
          >
            <Info label="Status" value={workflow.status} />
            <Info label="Created" value={workflow.created_at || "-"} />
            <Info label="Updated" value={workflow.updated_at || "-"} />
            <Info label="Error" value={workflow.error || "None"} />
          </div>
        )}

        {deploymentRecord && (
          <div
            style={{
              marginTop: 18,
              padding: 14,
              borderRadius: 14,
              background: "#f8fafc",
              color: "#526173",
              fontSize: 14,
            }}
          >
            Backend deployment record synced as{" "}
            <strong>{deploymentRecord.status}</strong>.
          </div>
        )}
      </section>

      <section className="card" style={{ padding: 30, marginTop: 20 }}>
        <h2>Tasks & Data References</h2>

        <div style={{ display: "grid", gap: 16 }}>
          {tasks.map((task: any) => (
            <div
              key={task.task_id}
              style={{
                padding: 18,
                borderRadius: 16,
                background: task.status === "completed" ? "#ecfdf3" : "#f8fafc",
                border: "1px solid #d6dee9",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 12,
                }}
              >
                <div>
                  <strong>{task.node_key}</strong>
                  <div style={{ color: "#526173", marginTop: 6 }}>
                    Task ID: {task.task_id}
                  </div>
                </div>

                <span className="badge">{task.status}</span>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 14,
                  marginTop: 18,
                }}
              >
                <ReferenceList
                  title="Input References"
                  refs={task.input_refs || []}
                  onPreview={previewReference}
                />

                <ReferenceList
                  title="Output References"
                  refs={task.output_refs || []}
                  onPreview={previewReference}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {(previewLoading || preview) && (
        <section className="card" style={{ padding: 30, marginTop: 20 }}>
          <h2>Artifact / DataReference Preview</h2>

          {previewLoading && (
            <div
              style={{
                padding: 16,
                borderRadius: 14,
                background: "#f8fafc",
                color: "#667085",
              }}
            >
              Loading preview...
            </div>
          )}

          {!previewLoading && preview && <PreviewPanel preview={preview} />}
        </section>
      )}
    </div>
  );
}

function PreviewPanel({ preview }: { preview: any }) {
  if (preview.kind === "csv" && preview.rows && preview.columns) {
    return (
      <div
        style={{
          border: "1px solid #e4e9f2",
          borderRadius: 14,
          overflow: "hidden",
          background: "white",
        }}
      >
        <PreviewHeader preview={preview} />

        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontFamily: "sans-serif",
              fontSize: 14,
            }}
          >
            <thead>
              <tr>
                {preview.columns.map((column: string) => (
                  <th
                    key={column}
                    style={{
                      textAlign: "left",
                      padding: 12,
                      borderBottom: "1px solid #d6dee9",
                      background: "#f8fafc",
                      color: "#344054",
                    }}
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {preview.rows.map((row: any, rowIndex: number) => (
                <tr key={rowIndex}>
                  {preview.columns.map((column: string) => (
                    <td
                      key={column}
                      style={{
                        padding: 12,
                        borderBottom: "1px solid #e4e9f2",
                        color: "#344054",
                      }}
                    >
                      {String(row[column] ?? "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div
          style={{
            padding: 12,
            color: "#667085",
            fontSize: 13,
            background: "#f8fafc",
          }}
        >
          Showing up to {preview.row_preview_limit || 20} rows.
        </div>
      </div>
    );
  }

  if (preview.kind === "json" && preview.content) {
    return (
      <div
        style={{
          padding: 16,
          borderRadius: 14,
          background: "#f8fafc",
          color: "#344054",
          overflowX: "auto",
        }}
      >
        <PreviewHeader preview={preview} />
        <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
          {JSON.stringify(preview.content, null, 2)}
        </pre>
      </div>
    );
  }

  if (preview.available === false) {
    return (
      <div
        style={{
          padding: 18,
          borderRadius: 14,
          background: "#fef3f2",
          color: "#b42318",
          border: "1px solid #fecdca",
        }}
      >
        <PreviewHeader preview={preview} />

        <p style={{ marginTop: 12, marginBottom: 0, lineHeight: 1.6 }}>
          {preview.message || "This artifact is not available for preview."}
        </p>

        {preview.recommendation && (
          <div
            style={{
              marginTop: 14,
              padding: 14,
              borderRadius: 12,
              background: "white",
              color: "#344054",
            }}
          >
            <strong>Recommended artifact publishing options</strong>
            <ul style={{ marginBottom: 0, lineHeight: 1.7 }}>
              {preview.recommendation.local_demo && (
                <li>{preview.recommendation.local_demo}</li>
              )}
              {preview.recommendation.platform_ready && (
                <li>{preview.recommendation.platform_ready}</li>
              )}
            </ul>
          </div>
        )}

        {preview.uri && (
          <div
            style={{
              marginTop: 14,
              fontFamily: "monospace",
              fontSize: 13,
              wordBreak: "break-all",
            }}
          >
            {preview.uri}
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      style={{
        padding: 16,
        borderRadius: 14,
        background: "#f8fafc",
        color: "#344054",
        whiteSpace: "pre-wrap",
        fontFamily: "monospace",
        overflowX: "auto",
      }}
    >
      <PreviewHeader preview={preview} />
      {typeof preview.content === "string"
        ? preview.content
        : JSON.stringify(preview, null, 2)}
    </div>
  );
}

function PreviewHeader({ preview }: { preview: any }) {
  return (
    <div
      style={{
        display: "flex",
        gap: 10,
        alignItems: "center",
        marginBottom: 12,
        fontFamily: "sans-serif",
      }}
    >
      <span className="badge">{preview.kind || "reference"}</span>

      {preview.format && (
        <span style={{ color: "#667085", fontSize: 13 }}>
          format: {preview.format}
        </span>
      )}

      {preview.content_type && (
        <span style={{ color: "#667085", fontSize: 13 }}>
          content-type: {preview.content_type}
        </span>
      )}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: "#f8fafc", padding: 16, borderRadius: 14 }}>
      <div style={{ color: "#667085", fontSize: 13 }}>{label}</div>
      <strong>{value}</strong>
    </div>
  );
}

function ReferenceList({
  title,
  refs,
  onPreview,
}: {
  title: string;
  refs: any[];
  onPreview: (ref: any) => void;
}) {
  return (
    <div style={{ background: "white", borderRadius: 14, padding: 14 }}>
      <strong>{title}</strong>

      {refs.length === 0 && (
        <p style={{ color: "#667085", marginBottom: 0 }}>None</p>
      )}

      <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
        {refs.map((ref, index) => (
          <div
            key={`${ref.protocol}-${ref.uri}-${index}`}
            style={{
              padding: 12,
              borderRadius: 12,
              background: "#f8fafc",
              border: "1px solid #e4e9f2",
            }}
          >
            <div>
              <span className="badge">{ref.protocol}</span>
              <span style={{ marginLeft: 8, color: "#667085", fontSize: 13 }}>
                {ref.format}
              </span>
            </div>

            <div
              style={{
                marginTop: 10,
                fontFamily: "monospace",
                fontSize: 13,
                color: "#344054",
                wordBreak: "break-all",
              }}
            >
              {ref.uri}
            </div>

            <button
              onClick={() => onPreview(ref)}
              style={{
                marginTop: 10,
                border: "1px solid #bae6fd",
                background: "white",
                color: "#075985",
                borderRadius: 10,
                padding: "8px 12px",
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              Preview
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}