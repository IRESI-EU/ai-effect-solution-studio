import { connectionSummary } from "../lib/connection-review";
export type StructuralReviewData = {
  added_operation: { node_id: string; label: string; operation: string };
  connections_added: Connection[];
  connections_removed: Connection[];
  unchanged: { node_id: string; label: string; configuration: unknown; operation_contract: unknown }[];
  authority?: Record<string, unknown>;
  compatibility: string;
  limitations: string;
};
type Connection = { id: string; source: string; target: string; data?: { binding?: { source_slot: string; target_slot: string } } };

export default function StructuralReview({ review }: { review: StructuralReviewData }) {
  const labels = new Map(review.unchanged.map(item => [item.node_id, item.label]));
  labels.set(review.added_operation.node_id, review.added_operation.label);
  const input = review.connections_added.find(edge => edge.data?.binding);
  const link = (edge: Connection) => `${labels.get(edge.source) || "Unknown step"} → ${labels.get(edge.target) || "Unknown step"}`;
  return <section aria-label="Structural change review" className="structural-review">
    <p className="structural-lead"><strong>Add {review.added_operation.label}</strong></p>
    {input && <p>{connectionSummary(labels.get(input.source) || "Unknown step", review.added_operation.label, input.data?.binding)}</p>}
    <p>Existing steps and settings stay unchanged.</p>
    {review.unchanged.flatMap(item => {
      const parameters = (item.configuration as {parameters?: Record<string, unknown>} | null)?.parameters;
      return parameters ? [<p key={item.node_id} className="structural-unchanged"><strong>{item.label}</strong>: {Object.entries(parameters).map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`).join(" · ")}</p>] : [];
    })}
    <p>{review.connections_added.length} connections added · {review.connections_removed.length} removed. {review.connections_removed.length > 0 && "Replaces the previous connection to workflow output."}</p>
    <details><summary>Connection changes</summary>
      <p>Added</p><ul>{review.connections_added.map(edge => <li key={edge.id}>{link(edge)}</li>)}</ul>
      <p>Removed</p><ul>{review.connections_removed.map(edge => <li key={edge.id}>{link(edge)}</li>)}</ul>
    </details>
    <p><strong>Apply changes the design; it does not execute it.</strong> Runtime availability is unchecked.</p>
    <details><summary>Technical details</summary>
      <p>{review.compatibility}</p><p>{review.limitations}</p>
      <p>Operation: {review.added_operation.operation}</p>
      <pre>{JSON.stringify({added_instance: review.added_operation.node_id, contracts: review.authority,
        unchanged: review.unchanged, connections_added: review.connections_added, connections_removed: review.connections_removed}, null, 2)}</pre>
    </details>
  </section>;
}
