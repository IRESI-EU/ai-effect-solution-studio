"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useAuth } from "../../components/auth-context";
import { apiErrorMessage } from "../../lib/solution-design";

type Solution = { id: string; name: string; status: string; created_by_user_id: string | null };
export default function SavedSolutionEntry({ legacy }: { legacy: ReactNode }) {
  const { user } = useAuth();
  const [mode, setMode] = useState<"loading" | "normal" | "legacy" | "disabled">("loading");
  const [solutions, setSolutions] = useState<Solution[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [goal, setGoal] = useState("");
  const creating = useRef(false);
  useEffect(() => {
    let current = true;
    setMode("loading"); setError(""); setSolutions([]);
    if (!user) { setMode("disabled"); return; }
    (async () => {
      const response = await fetch("/api/design-ai/config", { cache: "no-store" });
      const config = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(config, "Could not load assistant settings"));
      if (!current) return;
      if (!config.enabled) { setMode("disabled"); return; }
      if (!config.saved_solution_workspace) { setMode("legacy"); return; }
      setMode("normal");
      const list = await fetch("/api/solutions", { cache: "no-store" });
      const value = await list.json();
      if (!list.ok) throw new Error(apiErrorMessage(value, "Could not load saved solutions"));
      if (current) setSolutions(value.filter((solution: Solution) => solution.status !== "archived" && solution.created_by_user_id === user.id));
    })().catch(reason => { if (current) setError(reason.message); });
    return () => { current = false; };
  }, [user?.id]);
  async function create() {
    if (creating.current || !goal.trim()) return;
    creating.current = true; setBusy(true); setError("");
    try {
      const response = await fetch("/api/solutions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        name: "New AI-EFFECT solution", description: "", nodes: [], edges: [], design_metadata: { run_input: null, assistant_goal: goal.trim() },
      }) });
      const value = await response.json();
      if (!response.ok) throw new Error(apiErrorMessage(value, "Could not create a solution"));
      window.location.assign(`/builder?solutionId=${encodeURIComponent(value.id)}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create a solution"); }
    finally { creating.current = false; setBusy(false); }
  }
  if (mode === "legacy") return legacy;
  return <div className="page"><h1>Design with AI</h1>
    {error && <p role="alert">{error}</p>}
    {mode === "loading" ? <p>Loading your workspace…</p> : mode === "disabled" ? <p>Sign in to an enabled design workspace to use the assistant.</p> : <>
      <p>Chat and manual editing share one saved solution in Builder. Start a solution or continue one of your own.</p>
      <form onSubmit={event => { event.preventDefault(); void create(); }}>
        <label style={{display:"grid",gap:8,marginBlock:12}}>What would you like to build?
          <textarea value={goal} onChange={event=>setGoal(event.target.value)} maxLength={4000} rows={3} disabled={busy} required />
        </label>
        <p>Your goal opens in the same saved Builder solution. Send it to discover current catalogue services, clarify choices and review a connected proposal. Starting a solution makes no AI request or Run.</p>
        <button disabled={busy || !goal.trim()}>{busy ? "Creating…" : "Start with this goal"}</button>
      </form>
      <ul>{solutions.map(solution => <li key={solution.id}><Link href={`/builder?solutionId=${encodeURIComponent(solution.id)}`}>{solution.name}</Link></li>)}</ul>
    </>}
  </div>;
}
