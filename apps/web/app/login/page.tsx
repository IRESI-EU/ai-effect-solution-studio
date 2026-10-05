"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useState } from "react";
import { LockKeyhole } from "lucide-react";
import { useAuth } from "../../components/auth-context";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Sign in failed");
      await refresh();
      const next = searchParams.get("next");
      router.replace(next && next.startsWith("/") && !next.startsWith("//") ? next : "/");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-brand-panel"><div className="auth-brand-mark">AI</div><span>AI-EFFECT Solution Studio</span><h1>Trusted energy AI, with access matched to each responsibility.</h1><p>Node teams publish services, solution designers compose deployments, and platform administrators govern the workspace.</p></section>
      <section className="auth-form-panel">
        <div className="auth-form-card">
          <div className="auth-form-icon"><LockKeyhole size={24} /></div>
          <span className="auth-eyebrow">Secure workspace</span><h2>Sign in</h2><p>Use the email address approved by the platform administrator.</p>
          <form onSubmit={submit} className="auth-form">
            <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {error && <div className="auth-error" role="alert">{error}</div>}
            <button type="submit" disabled={submitting}>{submitting ? "Signing in…" : "Sign in"}</button>
          </form>
          <p className="auth-footer-copy">Need an account? <Link href="/register">Request access</Link></p>
          <Link className="auth-public-link" href="/catalogue">Browse the public service catalogue</Link>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return <Suspense fallback={<div className="auth-loading">Loading sign in…</div>}><LoginForm /></Suspense>;
}
