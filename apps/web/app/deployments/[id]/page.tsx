"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function DeploymentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const [workflowId, setWorkflowId] = useState("");
  const [workflow, setWorkflow] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<any>(null);

  async function previewReference(ref: any) {
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

    const data = await res.json();
    setPreview(data);
  }

  useEffect(() => {
    async function load() {
      const { id } = await params;
      setWorkflowId(id);

      try {
        const workflowRes = await fetch(
          `http://localhost:18080/orchestrator/workflows/${id}`
        );
        const workflowData = await workflowRes.json();
        setWorkflow(workflowData);

        const tasksRes = await fetch(
          `http://localhost:18080/orchestrator/workflows/${id}/tasks`
        );
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
        <span className="badge">WP3 Orchestrator Deployment</span>
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

      {preview && (
        <section className="card" style={{ padding: 30, marginTop: 20 }}>
          <h2>Artifact / DataReference Preview</h2>

          <div
            style={{
              padding: 16,
              borderRadius: 14,
              background: preview.available === false ? "#fef3f2" : "#f8fafc",
              color: preview.available === false ? "#b42318" : "#344054",
              whiteSpace: "pre-wrap",
              fontFamily: "monospace",
              overflowX: "auto",
            }}
          >
            {preview.kind === "csv" && preview.rows ? (
  <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "sans-serif" }}>
    <thead>
      <tr>
        {preview.columns.map((column: string) => (
          <th
            key={column}
            style={{
              textAlign: "left",
              padding: 10,
              borderBottom: "1px solid #d6dee9",
              background: "#f8fafc",
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
                padding: 10,
                borderBottom: "1px solid #e4e9f2",
              }}
            >
              {row[column]}
            </td>
          ))}
        </tr>
      ))}
    </tbody>
  </table>
) : (
  preview.content || preview.message || JSON.stringify(preview, null, 2)
)}
          </div>
        </section>
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