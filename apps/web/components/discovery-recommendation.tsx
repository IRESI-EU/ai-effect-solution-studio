"use client";

import CompositionReview from "./composition-review";
import { recommendationCreation, type Recommendation } from "../app/design-ai/session";

export default function DiscoveryRecommendation({ recommendation: item, busy, onCreate, compact = false }: {
  recommendation: Recommendation; busy: boolean; onCreate: () => void; compact?: boolean;
}) {
  const composed = item.mechanism === "catalogue_composed";
  const registered = item.mechanism === "registered_workflow";
  return <div className={`ai-discovery-card${compact ? " compact" : ""}`}><div className="ai-recommendation-body">
    <strong>{composed ? "Proposed new workflow design" : registered ? "Registered workflow recommendation" : "Relevant catalogue capability"}</strong>
    <h3>{item.label}</h3>
    {item.purpose && !(compact && composed) && <p>{item.purpose}</p>}
    {composed && item.composition_review ? <CompositionReview review={item.composition_review} compact={compact} /> : registered ? <>
      <p>Use the existing registered workflow with seed <strong>{item.recommended_seed}</strong>. Its supported steps and connection stay fixed.</p>
      {item.defaults_used?.includes("seed") && <p>Seed {item.recommended_seed} is the declared default. You can change it in the draft's supported input settings before saving.</p>}
      <ol>{item.steps.map(step => <li key={step.operation}>{step.title}</li>)}</ol>
      <p>{item.connection}.</p>
      <p>Expected after successful execution and capture: {item.expected_result_view.join(", ")}.</p>
      <p>Optional downloads: {item.optional_downloads.join(", ")}.</p>
    </> : <>
      <p>This service may help with your objective. It has no supported experiment creation path here.</p>
      <p>{item.input_requirements_known ? "Required information: " + (item.required_inputs?.map(input => input.purpose ? `${input.name} (${input.purpose})` : input.name).join(", ") || "No required inputs declared.") : "Input requirements are unresolved because a unique supported operation contract is unavailable."}</p>
      <p>Data availability and connections to other services have not been verified.</p>
    </>}
    {!(compact && composed) && <p>Runtime availability has not been checked. No experiment has been created or run by this conversation.</p>}
    <details><summary>Details and limitations</summary>
      {item.candidate_id && <p>Catalogue reference: <code>{item.candidate_id}</code></p>}
      {item.contract_resolution && <p>Operation contract: {item.contract_resolution === "resolved" ? "Resolved declared contract; no composition implied" : "Unavailable or unsupported"}</p>}
      {!!item.supported_settings?.length && <><p>Declared settings:</p><ul>{item.supported_settings.map(setting => <li key={setting.name}>{setting.title}: {setting.description}</li>)}</ul></>}
      <p>{item.availability}</p><ul>{item.limitations.map(reason => <li key={reason}>{reason}</li>)}</ul>
    </details></div>
    <button className="ai-primary ai-create-recommendation" disabled={busy || !recommendationCreation(item)} onClick={onCreate}>Create this experiment</button>
    {!recommendationCreation(item) && <p>Creation is unavailable for this capability. Continue the conversation to clarify your objective or required data.</p>}
  </div>;
}
