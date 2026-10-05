"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { UserPlus } from "lucide-react";
import type { NodeCode, UserRole } from "../../components/auth-context";

type RegistrationRole = Exclude<UserRole, "platform_admin">;

export default function RegisterPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<RegistrationRole>("solution_designer");
  const [node, setNode] = useState<NodeCode | "">("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (role === "node_manager" && !node) {
      setError("Select the node you work with.");
      return;
    }
    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ display_name: displayName, email, password, requested_role: role, node: node || null }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(". ") : data.detail;
        throw new Error(detail || "Registration could not be submitted");
      }
      router.push(`/registration-pending?email=${encodeURIComponent(email)}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Registration could not be submitted");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-brand-panel"><div className="auth-brand-mark">AI</div><span>AI-EFFECT Solution Studio</span><h1>Request access to the shared AI-EFFECT workspace.</h1><p>Select your intended responsibility and affiliated node. An administrator will verify the request before access is activated.</p></section>
      <section className="auth-form-panel">
        <div className="auth-form-card auth-form-card-wide">
          <div className="auth-form-icon"><UserPlus size={24} /></div><span className="auth-eyebrow">Approval required</span><h2>Create an access request</h2>
          <form onSubmit={submit} className="auth-form auth-form-grid">
            <label>Full name<input required minLength={2} autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
            <label>Email address<input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label>Requested access<select value={role} onChange={(event) => setRole(event.target.value as RegistrationRole)}><option value="solution_designer">Solution Designer</option><option value="node_manager">Node Manager / Researcher</option></select></label>
            <label>Affiliated node<select required={role === "node_manager"} value={node} onChange={(event) => setNode(event.target.value as NodeCode | "")}><option value="">{role === "node_manager" ? "Select a node" : "No node / not applicable"}</option><option value="germany">German Node</option><option value="portugal">Portuguese Node</option><option value="denmark">Danish Node</option><option value="netherlands">Dutch Node</option></select></label>
            <label className="auth-form-full">Password<input required type="password" minLength={12} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} /><small>At least 12 characters with uppercase, lowercase and a number.</small></label>
            {error && <div className="auth-error auth-form-full" role="alert">{error}</div>}
            <button className="auth-form-full" type="submit" disabled={submitting}>{submitting ? "Submitting…" : "Submit registration request"}</button>
          </form>
          <p className="auth-footer-copy">Already approved? <Link href="/login">Sign in</Link></p>
        </div>
      </section>
    </main>
  );
}
