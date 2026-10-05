"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

type DeploymentRecord = {
  id: string;
  workflow_id: string;
  solution_id?: string | null;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
};

type DrawingReference = {
  uri: string;
  network_index?: number | string;
};

type DrawingPreviewOptions = {
  drawings: DrawingReference[];
  selectedIndex: number;
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
  const [previewDrawings, setPreviewDrawings] = useState<DrawingReference[]>([]);
  const [selectedDrawingIndex, setSelectedDrawingIndex] = useState<number | null>(null);
  const previewSectionRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!previewLoading && !preview) return;

    const frame = window.requestAnimationFrame(() => {
      previewSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [previewLoading, preview]);

  async function previewReference(
    ref: any,
    drawingOptions?: DrawingPreviewOptions,
    taskId?: string,
  ) {
    setPreviewDrawings(drawingOptions?.drawings || []);
    setSelectedDrawingIndex(drawingOptions?.selectedIndex ?? null);
    setPreviewLoading(true);
    setPreview(null);

    try {
      const res = await fetch("/api/data-references/preview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          protocol: ref.protocol,
          uri: ref.uri,
          format: ref.format,
          task_id: taskId,
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
        `/api/deployments/by-workflow/${workflowId}`
      );

      if (!deploymentRes.ok) {
        return;
      }

      const deployment: DeploymentRecord = await deploymentRes.json();
      setDeploymentRecord(deployment);

      if (deployment.status !== status) {
        const updateRes = await fetch(
          `/api/deployments/${deployment.id}`,
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
    let cancelled = false;
    let refreshTimer: ReturnType<typeof setTimeout> | undefined;

    async function load() {
      const { id } = await params;
      if (cancelled) return;
      setWorkflowId(id);

      try {
        const workflowRes = await fetch(
          `/api/orchestrator/workflows/${id}`
        );

        if (!workflowRes.ok) {
          throw new Error("Failed to load workflow.");
        }

        const workflowData = await workflowRes.json();
        if (cancelled) return;
        setWorkflow(workflowData);
        setError("");

        if (workflowData.status) {
          await syncDeploymentStatus(id, workflowData.status);
        }

        const tasksRes = await fetch(
          `/api/orchestrator/workflows/${id}/tasks`
        );

        if (!tasksRes.ok) {
          throw new Error("Failed to load workflow tasks.");
        }

        const tasksData = await tasksRes.json();
        if (cancelled) return;
        setTasks(tasksData.tasks || []);
        if (!["completed", "failed"].includes(workflowData.status)) {
          refreshTimer = setTimeout(load, 5000);
        }
      } catch {
        if (!cancelled) setError("Failed to load deployment details. Refresh the page to retry.");
      }
    }

    load();
    return () => {
      cancelled = true;
      if (refreshTimer) clearTimeout(refreshTimer);
    };
  }, [params]);

  return (
    <div className="page">
      <Link href="/deployments" style={{ color: "#075985", fontWeight: 800 }}>
        ← Back to deployments
      </Link>

      <section
        className="card"
        style={{
          padding: 30,
          marginTop: 20,
          background: "linear-gradient(135deg, #ffffff 0%, #f5f1ff 100%)",
          border: "1px solid #ded7f5",
          boxShadow: "0 18px 46px rgba(48, 35, 104, 0.08)",
        }}
      >
        <span className="badge">Orchestrator Deployment</span>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 20,
            alignItems: "flex-start",
            margin: "16px 0 24px",
          }}
        >
          <div>
            <h1 style={{ fontSize: 40, margin: 0 }}>Run details</h1>
            <div
              style={{
                marginTop: 10,
                color: "#667085",
                fontFamily: "monospace",
                wordBreak: "break-all",
              }}
            >
              Workflow {workflowId}
            </div>
          </div>
          {workflow?.status && (
            <span
              className="badge"
              style={{
                ...statusBadgeStyle(workflow.status),
                padding: "8px 12px",
              }}
            >
              {workflow.status}
            </span>
          )}
        </div>

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
            <strong>{deploymentRecord.name}</strong>
            {deploymentRecord.solution_id
              ? ` · Solution ${deploymentRecord.solution_id}`
              : " · No linked solution"}
            {" · "}Backend record synced as{" "}
            <strong>{deploymentRecord.status}</strong>.
          </div>
        )}
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
        <h2 style={{ marginTop: 0 }}>Tasks &amp; Data References</h2>
        <p style={{ color: "#667085", marginTop: -4, marginBottom: 20 }}>
          Orchestrator task states and the input or output artifacts attached to
          each workflow node.
        </p>

        {!error && workflow && tasks.length === 0 && (
          <div
            style={{
              padding: 18,
              borderRadius: 14,
              background: "#f8f7fc",
              color: "#667085",
            }}
          >
            No task records are available for this workflow yet.
          </div>
        )}

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

                <span
                  className="badge"
                  style={statusBadgeStyle(task.status)}
                >
                  {task.status}
                </span>
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
                  onPreview={(ref) =>
                    previewReference(ref, undefined, findReferenceTaskId(ref, task.task_id, tasks))
                  }
                />

                <ReferenceList
                  title="Output References"
                  refs={task.output_refs || []}
                  onPreview={(ref) =>
                    previewReference(ref, undefined, findReferenceTaskId(ref, task.task_id, tasks))
                  }
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {(previewLoading || preview) && (
        <section
          ref={previewSectionRef}
          className="card deployment-preview-card"
          aria-live="polite"
        >
          <div className="deployment-preview-heading">
            <div>
              <span className="badge">Result preview</span>
              <h2>Artifact / DataReference Preview</h2>
            </div>
            {!previewLoading && preview?.kind && (
              <span className="deployment-preview-kind">{preview.kind}</span>
            )}
          </div>

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

          {!previewLoading && preview && (
            <PreviewPanel
              preview={preview}
              drawings={previewDrawings}
              selectedDrawingIndex={selectedDrawingIndex}
              onPreview={previewReference}
            />
          )}
        </section>
      )}
    </div>
  );
}

function PreviewPanel({
  preview,
  drawings,
  selectedDrawingIndex,
  onPreview,
}: {
  preview: any;
  drawings: DrawingReference[];
  selectedDrawingIndex: number | null;
  onPreview: (ref: any, drawingOptions?: DrawingPreviewOptions) => void;
}) {
  if (preview.kind === "svg" && preview.available && preview.image_data_url) {
    return (
      <div className="deployment-svg-preview">
        <PreviewHeader preview={preview} />
        {drawings.length > 0 && (
          <div className="deployment-drawing-gallery-nav">
            <div className="deployment-drawing-gallery-heading">
              <div>
                <strong>Topology drawings</strong>
                <span>Select another drawing without returning to the output reference.</span>
              </div>
              <span>
                Drawing {(selectedDrawingIndex ?? 0) + 1} of {drawings.length}
              </span>
            </div>
            <DrawingButtons
              drawings={drawings}
              selectedIndex={selectedDrawingIndex}
              onPreview={onPreview}
            />
          </div>
        )}
        <img src={preview.image_data_url} alt="Workflow SVG output" style={{ display: "block", maxWidth: "100%", maxHeight: 700, margin: "auto" }} />
      </div>
    );
  }
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
    const drawings = Array.isArray(preview.content?.drawings) ? preview.content.drawings : [];
    const report = preview.content?.report;
    return (
      <div className="deployment-json-preview">
        <PreviewHeader preview={preview} />
        {report && typeof report === "object" && (
          <div className="deployment-report-summary">
            <div>
              <span>Result summary</span>
              <strong>{String(report.summary || report.title || "Report generated successfully")}</strong>
            </div>
            {report.recommended_network != null && (
              <div>
                <span>Recommended network</span>
                <strong>{String(report.recommended_network)}</strong>
              </div>
            )}
          </div>
        )}
        {drawings.length > 0 && (
          <DrawingButtons drawings={drawings} selectedIndex={null} onPreview={onPreview} />
        )}
        <details className="deployment-raw-output">
          <summary>View raw JSON output</summary>
          <pre>{JSON.stringify(preview.content, null, 2)}</pre>
        </details>
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

function DrawingButtons({
  drawings,
  selectedIndex,
  onPreview,
}: {
  drawings: DrawingReference[];
  selectedIndex: number | null;
  onPreview: (ref: any, drawingOptions?: DrawingPreviewOptions) => void;
}) {
  const previewableDrawings = drawings.filter(
    (drawing) =>
      typeof drawing?.uri === "string" && drawing.uri.toLowerCase().endsWith(".svg")
  );

  return (
    <div className="deployment-drawing-actions" aria-label="Available topology drawings">
      {previewableDrawings.map((drawing, index) => {
        const isSelected = selectedIndex === index;
        return (
          <button
            className={isSelected ? "is-selected" : undefined}
            key={`${drawing.uri}-${index}`}
            type="button"
            aria-pressed={isSelected}
            onClick={() =>
              onPreview(
                { protocol: "file", uri: drawing.uri, format: "svg" },
                { drawings: previewableDrawings, selectedIndex: index }
              )
            }
          >
            {isSelected ? "Viewing" : "View"} drawing {drawing.network_index ?? index + 1}
          </button>
        );
      })}
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
    <div
      style={{
        background: "rgba(255, 255, 255, 0.9)",
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

function statusBadgeStyle(status: string) {
  const normalized = status.toLowerCase();

  if (normalized === "completed") {
    return { background: "#dcfae6", color: "#027a48" };
  }

  if (normalized === "failed") {
    return { background: "#fee4e2", color: "#b42318" };
  }

  if (normalized === "running") {
    return { background: "#eaf2ff", color: "#2457a6" };
  }

  return { background: "#f2edff", color: "#6941c6" };
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
              type="button"
              onClick={() => onPreview(ref)}
              style={{
                marginTop: 10,
                border: "1px solid #d7ceff",
                background: "white",
                color: "#6941c6",
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

function findReferenceTaskId(ref: any, fallbackTaskId: string, tasks: any[]) {
  const producer = tasks.find((task) =>
    (task.output_refs || []).some(
      (output: any) =>
        output.protocol === ref.protocol &&
        output.uri === ref.uri &&
        output.format === ref.format,
    ),
  );
  return producer?.task_id || fallbackTaskId;
}
