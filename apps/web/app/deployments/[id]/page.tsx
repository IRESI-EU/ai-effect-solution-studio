"use client";

import Link from "next/link";
import { ArrowLeft, CircleX } from "lucide-react";
import { serviceText } from "../../../lib/service-presentation";
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
  const [previewDirectory, setPreviewDirectory] = useState<any>(null);
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
    directoryContext?: any,
  ) {
    setPreviewDrawings(drawingOptions?.drawings || []);
    setSelectedDrawingIndex(drawingOptions?.selectedIndex ?? null);
    if (directoryContext) {
      setPreviewDirectory(directoryContext);
    } else {
      setPreviewDirectory(null);
    }
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
          workflow_id: workflowId || undefined,
        }),
      });

      if (!res.ok) {
        throw new Error("Preview request failed.");
      }

      const data = await res.json();
      if (data.kind === "directory" && data.available) {
        setPreviewDirectory(data);
      }
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

  const runStatus = (workflow?.status || deploymentRecord?.status || "").toLowerCase();
  const completedSteps = tasks.filter((task: any) => task.status === "completed").length;

  return (
    <div className="page run-page">
      <Link href="/deployments" className="back-link"><ArrowLeft size={16} aria-hidden="true" />Runs</Link>

      <header className="page-header">
        <div className="page-header__text">
          <div className="service-page__meta">
            {runStatus && <span className={"ae-badge " + statusTone(runStatus)}>{capitalise(runStatus)}</span>}
            <span className="ae-mono">{workflowId}</span>
          </div>
          <h1 className="page-header__title">{deploymentRecord?.name || "Run details"}</h1>
          <p className="page-header__lead">
            {tasks.length > 0 ? completedSteps + " of " + tasks.length + " steps completed." : "Waiting for the orchestrator to report steps."}
          </p>
        </div>
        {deploymentRecord?.solution_id && (
          <div className="page-header__actions">
            <Link href={"/builder?solutionId=" + encodeURIComponent(deploymentRecord.solution_id)} className="ae-btn ae-btn--secondary">Open in Builder</Link>
          </div>
        )}
      </header>

      {error && <div className="ae-alert ae-alert--danger run-alert"><CircleX size={20} aria-hidden="true" /><div>{error}</div></div>}
      {workflow?.error && <div className="ae-alert ae-alert--danger run-alert"><CircleX size={20} aria-hidden="true" /><div><span className="ae-alert__title">The run failed.</span> {workflow.error}</div></div>}

      {workflow && (
        <section className="ae-card run-summary">
          <dl className="run-summary__grid">
            <div><dt>Status</dt><dd>{capitalise(runStatus || "unknown")}</dd></div>
            <div><dt>Started</dt><dd>{formatWhen(workflow.created_at)}</dd></div>
            <div><dt>Last update</dt><dd>{formatWhen(workflow.updated_at)}</dd></div>
            <div><dt>Solution</dt><dd>{deploymentRecord?.solution_id ? <Link href={"/solutions/" + deploymentRecord.solution_id}>Open solution</Link> : "Not linked"}</dd></div>
          </dl>
        </section>
      )}

      <section className="section">
        <h2 className="section__title">Steps</h2>
        {!error && workflow && tasks.length === 0 && (
          <div className="ae-card empty-state"><h3>No steps yet</h3><p>Steps appear here as the orchestrator starts them.</p></div>
        )}
        <ol className="run-steps">
          {tasks.map((task: any, index: number) => (
            <li key={task.task_id} className="ae-card run-step">
              <div className="run-step__head">
                <span className="run-step__number" aria-hidden="true">{index + 1}</span>
                <div className="run-step__title">
                  <h3>{stepName(task.node_key)}</h3>
                  <span className="ae-mono">{task.node_key}</span>
                </div>
                <span className={"ae-badge " + statusTone(task.status)}>{capitalise(task.status)}</span>
              </div>
              {task.error && <p className="ae-field__error run-step__error">{task.error}</p>}
              <ReferenceList
                title="Results"
                refs={task.output_refs || []}
                onPreview={(ref) => previewReference(ref, undefined, findReferenceTaskId(ref, task.task_id, tasks))}
              />
              {(task.input_refs || []).length > 0 && (
                <details className="details run-step__inputs">
                  <summary>Inputs ({(task.input_refs || []).length})</summary>
                  <div className="details__body">
                    <ReferenceList
                      title=""
                      refs={task.input_refs || []}
                      onPreview={(ref) => previewReference(ref, undefined, findReferenceTaskId(ref, task.task_id, tasks))}
                    />
                  </div>
                </details>
              )}
            </li>
          ))}
        </ol>
      </section>

      {(previewLoading || preview) && (
        <section ref={previewSectionRef} className="ae-card section run-preview deployment-preview-card" aria-live="polite">
          <div className="run-preview__head">
            <h2 className="section__title">Result</h2>
            {!previewLoading && preview?.kind && <span className="ae-badge ae-badge--plain ae-badge--info">{String(preview.kind).toUpperCase()}</span>}
          </div>

          {(previewDirectory || preview?.kind === "directory") && (
            <ArtifactFileTabs
              directory={preview?.kind === "directory" ? preview : previewDirectory}
              activeUri={preview?.kind === "directory" ? null : preview?.uri}
              onPreview={previewReference}
            />
          )}

          {previewLoading && <p className="muted" style={{ margin: 0 }}>Loading the result...</p>}

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

function capitalise(value: string) {
  return value ? value.charAt(0).toUpperCase() + value.slice(1) : value;
}

function statusTone(status: string) {
  const s = (status || "").toLowerCase();
  if (s === "completed") return "ae-badge--success";
  if (s === "failed") return "ae-badge--danger";
  if (s === "running" || s === "submitted" || s === "pending") return "ae-badge--info";
  return "";
}

function formatWhen(value?: string) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IE", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(date);
}

function stepName(nodeKey: string) {
  const [container, operation] = String(nodeKey || "").split(":");
  return serviceText({ name: container || nodeKey, operation_name: operation || null }).title;
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
  onPreview: (
    ref: any,
    drawingOptions?: DrawingPreviewOptions,
    taskId?: string,
    directoryContext?: any,
  ) => void;
}) {
  if (preview.kind === "directory" && preview.available && Array.isArray(preview.files)) {
    return (
      <div className="deployment-json-preview">
        <PreviewHeader preview={preview} />
        {preview.files.length === 0 && <p>No previewable files were found in this output directory.</p>}
        {preview.files.length > 0 && <p>Select a file tab above to inspect its contents.</p>}
      </div>
    );
  }

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
          borderRadius: 8,
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
                      background: "var(--surface-sunken)",
                      color: "var(--ink-900)",
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
                        color: "var(--ink-900)",
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
            color: "var(--ink-600)",
            fontSize: 13,
            background: "var(--surface-sunken)",
          }}
        >
          Showing up to {preview.row_preview_limit || 20} rows.
        </div>
      </div>
    );
  }

  if (preview.kind === "json" && preview.content) {
    const drawings = Array.isArray(preview.content?.drawings) ? preview.content.drawings : [];
    const report =
      preview.content?.report ||
      (typeof preview.content?.summary === "string" ? preview.content : null);
    const sections = Array.isArray(preview.content?.sections) ? preview.content.sections : [];
    const fromGrpc = preview.source_kind === "grpc";
    return (
      <div className="deployment-json-preview">
        <PreviewHeader preview={preview} />
        {preview.note && <p style={{ color: "var(--ink-600)", fontSize: 13, margin: "4px 0 8px" }}>{String(preview.note)}</p>}
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
        {sections.length > 0 && (
          <div className="deployment-report-sections" style={{ display: "grid", gap: 10, margin: "8px 0" }}>
            {sections.map((section: any, index: number) => (
              <div key={index}>
                <strong>{String(section?.title || `Section ${index + 1}`)}</strong>
                {Array.isArray(section?.content) && (
                  <ul style={{ margin: "4px 0 0", paddingLeft: 18 }}>
                    {section.content.map((line: unknown, lineIndex: number) => (
                      <li key={lineIndex}>{String(line)}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
        {drawings.length > 0 && (
          <DrawingButtons drawings={drawings} selectedIndex={null} onPreview={onPreview} />
        )}
        <details className="deployment-raw-output" open={fromGrpc && sections.length === 0 && !report}>
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
          borderRadius: 8,
          background: "var(--danger-100)",
          color: "var(--danger-600)",
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
              borderRadius: 8,
              background: "white",
              color: "var(--ink-900)",
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
        borderRadius: 8,
        background: "var(--surface-sunken)",
        color: "var(--ink-900)",
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

function ArtifactFileTabs({
  directory,
  activeUri,
  onPreview,
}: {
  directory: any;
  activeUri?: string | null;
  onPreview: (
    ref: any,
    drawingOptions?: DrawingPreviewOptions,
    taskId?: string,
    directoryContext?: any,
  ) => void;
}) {
  if (!directory?.available || !Array.isArray(directory.files) || directory.files.length === 0) {
    return null;
  }

  return (
    <div className="deployment-drawing-buttons" aria-label="Output files">
      {directory.files.map((file: any) => {
        const isSelected = activeUri === file.uri;
        return (
          <button
            key={file.uri}
            type="button"
            className={isSelected ? "btn btn-primary" : "btn btn-secondary"}
            aria-pressed={isSelected}
            onClick={() => onPreview(file, undefined, undefined, directory)}
          >
            {file.name} ({formatArtifactSize(file.size_bytes)})
          </button>
        );
      })}
    </div>
  );
}

function formatArtifactSize(value: number | undefined) {
  if (!value || value < 1024) return `${value || 0} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
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
        <span style={{ color: "var(--ink-600)", fontSize: 13 }}>
          format: {preview.format}
        </span>
      )}

      {preview.content_type && (
        <span style={{ color: "var(--ink-600)", fontSize: 13 }}>
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
        borderRadius: 8,
        border: "1px solid #e8e4f4",
      }}
    >
      <div style={{ color: "var(--ink-600)", fontSize: 13 }}>{label}</div>
      <strong>{value}</strong>
    </div>
  );
}

function statusBadgeStyle(status: string) {
  const normalized = status.toLowerCase();

  if (normalized === "completed") {
    return { background: "var(--mint-100)", color: "var(--success-600)" };
  }

  if (normalized === "failed") {
    return { background: "var(--danger-100)", color: "var(--danger-600)" };
  }

  if (normalized === "running") {
    return { background: "var(--brand-50)", color: "var(--brand-600)" };
  }

  return { background: "var(--brand-50)", color: "var(--brand-600)" };
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
    <div className="run-refs">
      {title && <span className="run-refs__title">{title}</span>}
      {refs.length === 0 && <p className="muted run-refs__empty">None yet</p>}
      {refs.map((ref, index) => (
        <div key={ref.protocol + "-" + ref.uri + "-" + index} className="run-ref">
          <div className="run-ref__meta">
            <span className="ae-badge ae-badge--plain">{String(ref.protocol).toUpperCase()}</span>
            {ref.format && <span className="run-ref__format">{ref.format}</span>}
          </div>
          <span className="ae-mono run-ref__uri" title={ref.uri}>{ref.protocol === "inline" ? "Inline data" : ref.uri}</span>
          <button type="button" className="ae-btn ae-btn--secondary ae-btn--sm" onClick={() => onPreview(ref)}>View</button>
        </div>
      ))}
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
