"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { deploymentResultsUrl } from "../lib/experiment-journey";

type Attempt = {submission_id: string; phase: string; workflow_id: string | null};
type Review = {seed?: number; readiness: {status: string; checks?: {node_id: string; service_name: string; blocking: boolean; message: string; recommended_action: string}[]}; attempt: Attempt | null; execution_authorized: boolean};
async function request(id: string, path: string, body?: unknown) {
  const response = await fetch(`/api/design-ai/drafts/${encodeURIComponent(id)}/${path}`, {
    method: body === undefined ? "GET" : "POST", cache: "no-store",
    ...(body === undefined ? {} : {headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})});
  const value = await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof value?.detail === "string" ? value.detail : value?.detail?.message || `Request failed (HTTP ${response.status}).`);
  return value;
}

export default function ExperimentExecution({draftId, revision, saved}: {draftId: string; revision: number; saved: boolean}) {
  const router = useRouter();
  const [review, setReview] = useState<Review | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [busy, setBusy] = useState(false), [confirm, setConfirm] = useState(false);
  const [uncertain, setUncertain] = useState(false), [error, setError] = useState("");
  const inFlight = useRef(false), generation = useRef(0);
  useEffect(() => {
    const current = ++generation.current;
    setReview(null); setConfirm(false); setError("");
    request(draftId, "execution").then(value => {if (generation.current === current) setAttempt(value.attempt);})
      .catch(() => {if (generation.current === current) setError("Stored execution history could not be read. Check status before starting anything.");});
    return () => {generation.current++;};
  }, [draftId, revision, saved]);
  async function status() {
    setBusy(true);
    try {setAttempt((await request(draftId, "execution")).attempt); setError("");}
    catch (failure) {setError(failure instanceof Error ? failure.message : "Execution status is unavailable.");}
    finally {setBusy(false);}
  }
  async function prepare() {
    if (inFlight.current || !saved) return;
    inFlight.current = true; setBusy(true); setError(""); setConfirm(false);
    const current = generation.current;
    try {const value: Review = await request(draftId, "execution-review", {revision});
      if (generation.current === current) {setReview(value); setAttempt(value.attempt);}}
    catch (failure) {if (generation.current === current) setError(failure instanceof Error ? failure.message : "Readiness could not be checked.");}
    finally {inFlight.current = false; setBusy(false);}
  }
  async function execute() {
    if (inFlight.current || !saved || !confirm || !review?.execution_authorized || !attempt || attempt.phase !== "reviewed") return;
    inFlight.current = true; setBusy(true); setConfirm(false); setError("");
    try {
      const value = await request(draftId, "execute", {revision, submission_id: attempt.submission_id, confirm_execution: true});
      setAttempt(value.attempt);
      if (value.attempt?.workflow_id) router.push(deploymentResultsUrl(value.attempt.workflow_id));
    } catch (failure) {
      // Response/navigation loss cannot offer another dispatch. The attempt is
      // durable independently of browser-side history registration.
      setUncertain(true);
      setError(`${failure instanceof Error ? failure.message : "Execution confirmation could not be received."} Check the stored attempt; do not start again.`);
      try {setAttempt((await request(draftId, "execution")).attempt);} catch { /* Keep the known attempt visible. */ }
    } finally {inFlight.current = false; setBusy(false);}
  }
  const consumed = !!attempt && attempt.phase !== "reviewed";
  return <section className="ai-discovery-card" aria-label="Execution and results"><h3>Execution and results</h3>
    <p>{saved ? "Design saved. Saving has not started execution." : "Apply your changes and Save before reviewing execution."}</p>
    {error && <p role="alert">{error}</p>}
    {!consumed && !uncertain && <button disabled={!saved || busy} onClick={() => void prepare()}>{busy ? "Checking…" : "Review execution readiness"}</button>}
    {review && <><p>Validation and runtime readiness: <strong>{review.readiness.status === "ready" ? "Ready" : "Blocked"}</strong>.</p>
      {review.readiness.checks?.filter(check => check.blocking).map(check => <p key={check.node_id} role="status"><strong>{check.service_name}:</strong> {check.message} {check.recommended_action}</p>)}
      {review.seed !== undefined && <p>Saved seed: <strong>{review.seed}</strong>. Create a sample grid, then benchmark that same grid.</p>}
      {!review.execution_authorized && !consumed && <p role="status">Execution is locked until the operator separately authorizes one local run. No workflow has been submitted.</p>}
      {review.readiness.status === "ready" && review.execution_authorized && !consumed && !uncertain && <button disabled={busy || !saved} onClick={() => setConfirm(true)}>Start execution</button>}</>}
    {confirm && <div role="group" aria-label="Confirm execution"><p>This starts one local workflow using the reviewed saved seed. Results require successful execution and capture.</p>
      <button disabled={busy || !saved} onClick={() => void execute()}>Confirm and start execution</button><button disabled={busy} onClick={() => setConfirm(false)}>Cancel</button></div>}
    {attempt && <><p>Stored attempt: <code>{attempt.submission_id}</code> · {attempt.phase === "reviewed" ? "Reviewed; not submitted" : attempt.phase === "submitted" ? "Submitted; open its run for progress and results" : attempt.phase === "submission_failed" ? "Submission stopped before dispatch. This attempt is consumed; no workflow was started." : "Submission outcome uncertain. Operator reconciliation required; no automatic retry."}</p>
      {attempt.workflow_id && <Link href={deploymentResultsUrl(attempt.workflow_id)}>View this run’s results</Link>}</>}
    <button disabled={busy} onClick={() => void status()}>Check stored execution status</button>
  </section>;
}
