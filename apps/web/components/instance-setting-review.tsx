export type ParameterReview = {
  changes: { node_id: string; label: string; key: string; title: string; description: string; before: unknown; after: unknown }[];
  unchanged: { node_id: string; label: string; parameters: Record<string, unknown>; titles: Record<string, string> }[];
  contract_pins: Record<string, { contract_id: string; contract_version: string }>;
};

const value = (item: unknown) => item === undefined || item === null ? "not set" : String(item);

export default function InstanceSettingReview({ review }: { review: ParameterReview }) {
  const changedKeys = new Set(review.changes.map(change => change.key));
  return <div aria-label="Instance setting proposal">
    {review.changes.map(change => <p key={`${change.node_id}:${change.key}`}><strong>{change.label}:</strong> {change.title} changes from {value(change.before)} to {value(change.after)}.</p>)}
    {review.unchanged.map(instance => <p key={instance.node_id}><strong>{instance.label}</strong> stays unchanged{Object.entries(instance.parameters).filter(([key]) => changedKeys.has(key)).map(([key, setting]) => ` · ${instance.titles[key]} stays at ${value(setting)}`)}.</p>)}
    <p>This updates a limit or setting only. No experiment has run; a maximum does not guarantee that many results.</p>
    <details><summary>Technical parameter details</summary>{review.changes.map(change => <p key={`${change.node_id}:${change.key}`}><code>{change.node_id}</code> · <code>{change.key}</code>: {value(change.before)} → {value(change.after)}<br />{change.description}<br />Contract {review.contract_pins[change.node_id]?.contract_id} · version {review.contract_pins[change.node_id]?.contract_version}</p>)}</details>
  </div>;
}
