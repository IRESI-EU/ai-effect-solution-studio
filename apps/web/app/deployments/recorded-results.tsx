import { artifactMessage } from "./results";
import { executionLabel } from "../../lib/experiment-journey";

export default function RecordedResults({ evidence, status, tasks = [] }: { evidence: any; status: string; tasks?: any[] }) {
  if (!evidence) return null;
  const seed = evidence.execution_input?.seed ?? evidence.executed_seed;
  return <section id="results" className="card" style={{ padding: 30, marginTop: 20, scrollMarginTop: 90 }} aria-label="Experiment results">
    <h2 style={{ marginTop: 0 }}>Experiment results</h2>
    <p><strong>{executionLabel(status)}</strong>{evidence.state !== "available" && <> · <strong>{["pending", "delayed"].includes(evidence.state) ? "Results pending" : "Results unavailable"}</strong></>}</p>
    <p>{status === "failed" ? "Execution failed. " : !["completed", "failed"].includes(status) ? "Execution in progress. " : ""}{evidence.message}</p>
    <p><strong>Recorded seed: {seed ?? "Unavailable — no execution input captured"}</strong>{seed !== undefined && !evidence.execution_input?.seed ? " (runtime default; no seed submitted)" : ""}</p>
    {evidence.input_source && <p style={{ color: "#526173" }}>{evidence.input_source}</p>}
    {tasks.length > 0 && <ul aria-label="Task progress">{tasks.map(task => <li key={task.task_id}>
      <strong>{task.node_key === "grid_synth_service:ConfigureAndSynthesize" ? "Grid generation" : task.node_key === "benchmark-runner:RunBenchmark" ? "Benchmark" : task.node_key}</strong>: {task.status}
    </li>)}</ul>}
    {evidence.grid && <p><strong>Generated grid:</strong> {evidence.grid.nodes} nodes · {evidence.grid.edges} edges · seed {evidence.grid.seed}</p>}
    {evidence.artifacts.length > 0 && <><h3>Downloads (optional)</h3><div style={{ display: "grid", gap: 10 }}>
      {evidence.artifacts.map((artifact: any) => <div key={artifact.id}>
        {artifact.state === "available" ? <a className="btn btn-secondary" style={{ display: "inline-flex", textDecoration: "none", padding: "8px 12px", border: "1px solid #c9bbfb", borderRadius: 8, color: "#50319c", background: "#f8f5ff", maxWidth: "100%", boxSizing: "border-box" }} href={artifact.download_url} download>Download {artifact.label}</a> : <><strong>{artifact.label}</strong>{" · "}{artifactMessage(artifact.state)}</>}
        {artifact.sha256 && <details style={{ marginTop: 5 }}><summary>File details</summary>
          <small>Task {artifact.task_id} · {artifact.size_bytes} bytes</small><br />
          <code style={{ overflowWrap: "anywhere" }}>SHA-256: {artifact.sha256}</code>
        </details>}
      </div>)}
    </div></>}
    {evidence.benchmark && <>
      <h3>Recorded benchmark results</h3>
      <p>{evidence.benchmark.scenario_count} scenario(s) · {evidence.benchmark.episodes.length} episode(s)</p>
      {evidence.benchmark.episodes.map((episode: any, index: number) => <p key={index}>
        Episode {episode.episode_index}: <code>steps</code> = {episode.steps} · <code>overload_violations</code> = {episode.overload_violations} · <code>runtime_seconds</code> = {episode.runtime_seconds} seconds · <code>terminated</code> = {String(episode.terminated)}
      </p>)}
      <p style={{ color: "#526173" }}>Metric names and values are recorded by the benchmark. KPI units were not supplied; no safety or optimality claim is made.</p>
      <div style={{ overflowX: "auto" }}><table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
        <thead><tr><th>Metric name</th><th>Recorded value</th><th>Unit</th></tr></thead>
        <tbody>{Object.entries(evidence.benchmark.kpis).map(([name, value]) => <tr key={name}>
          <td style={{ padding: "8px 8px 8px 0" }}><code>{name}</code></td><td style={{ overflowWrap: "anywhere" }}>{JSON.stringify(value)}</td><td>Not recorded</td>
        </tr>)}</tbody>
      </table></div>
    </>}
    {evidence.source && <details style={{ marginTop: 16 }}><summary>Technical evidence and limitations</summary>
      <p>{evidence.source}</p><p>Baseline source revision: <code>{evidence.source_revision}</code></p>
      {evidence.grid && <p>Grid ID: <code>{evidence.grid.grid_id}</code></p>}
      {evidence.capture_version && <p>Derived capture runtime: {evidence.capture_version}<br />Adapter SHA-256: <code style={{ overflowWrap: "anywhere" }}>{evidence.adapter_sha256}</code></p>}
      {Object.entries(evidence.images || {}).map(([name, id]) => <p key={name} style={{ overflowWrap: "anywhere" }}>{name}: <code>{String(id)}</code></p>)}
      <p>{evidence.limitations}</p>
    </details>}
  </section>;
}
