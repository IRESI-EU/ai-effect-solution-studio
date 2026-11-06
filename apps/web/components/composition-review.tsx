export type CompositionReviewData = {
  steps: { title: string; purpose: string; settings: Record<string, string | number | boolean> }[];
  connection: string; binding: {source_slot: string; target_slot: string; transport: string; schema_fingerprint: string};
  unresolved_requirements: unknown[]; runtime_checked: false; execution_supported: false;
};

export default function CompositionReview({ review }: { review: CompositionReviewData }) {
  return <div className="ai-composition-review">
    <p>New catalogue-composed design · two processing steps. No saved workflow template is copied.</p>
    <ol>{review.steps.map((step,index) => <li key={index}><strong>{step.title}</strong><p>{step.purpose}</p>
      {Object.keys(step.settings).length ? <p>Proposed settings: {Object.entries(step.settings).map(([key,value]) => `${key}: ${String(value)}`).join(" · ")}</p> : <p>No configurable settings declared.</p>}
    </li>)}</ol>
    <p>{review.connection}.</p>
    <p>Required inputs and proposed settings are satisfied by the declared contracts. Unspecified values come only from registry defaults.</p>
    <p>Design review only. Runtime readiness, execution and scientific validity remain unverified. Execution is unavailable for this design.</p>
    <details><summary>Connection details</summary><p><code>{review.binding.source_slot}</code> → <code>{review.binding.target_slot}</code> · {review.binding.transport}</p><p>Schema/version fingerprint: <code>{review.binding.schema_fingerprint}</code></p></details>
  </div>;
}
