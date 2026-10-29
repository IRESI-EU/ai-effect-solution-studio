export type StructuralReviewData = {
  added_operation: { node_id: string; label: string; operation: string };
  connections_added: Connection[];
  connections_removed: Connection[];
  unchanged: { node_id: string; label: string; configuration: unknown; operation_contract: unknown }[];
  compatibility: string;
  limitations: string;
};
type Connection = { id: string; source: string; target: string; data?: { binding?: { source_slot: string; target_slot: string } } };

export default function StructuralReview({ review }: { review: StructuralReviewData }) {
  const labels = new Map(review.unchanged.map(item => [item.node_id, item.label]));
  labels.set(review.added_operation.node_id, review.added_operation.label);
  const connection = (edge: Connection) => `${labels.get(edge.source) || edge.source}${edge.data?.binding ? ` / ${edge.data.binding.source_slot}` : ""} → ${labels.get(edge.target) || edge.target}${edge.data?.binding ? ` / ${edge.data.binding.target_slot}` : ""}`;
  return <section aria-label="Structural change review">
    <p><strong>Add {review.added_operation.label}</strong> ({review.added_operation.operation})</p>
    <p>Connections added:</p><ul>{review.connections_added.map(edge => <li key={edge.id}>{connection(edge)}</li>)}</ul>
    <p>Connections removed:</p><ul>{review.connections_removed.map(edge => <li key={edge.id}>{connection(edge)}</li>)}</ul>
    <p>Existing steps, settings, input and contract pins remain unchanged.</p>
    {review.unchanged.filter(item => item.configuration).map(item => <details key={item.node_id}><summary>{item.label} · unchanged settings</summary><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(item.configuration, null, 2)}</pre></details>)}
    <p>{review.compatibility}</p><p>{review.limitations}</p>
  </section>;
}
