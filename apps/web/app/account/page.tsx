"use client";

import { FormEvent, useState } from "react";
import { KeyRound, UserRound } from "lucide-react";
import { nodeLabels, roleLabels, useAuth } from "../../components/auth-context";
import { useRouter } from "next/navigation";

export default function AccountPage() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("The new passwords do not match.");
      return;
    }
    setSaving(true);
    try {
      const response = await fetch("/api/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = Array.isArray(data.detail) ? data.detail.map((item: { msg?: string }) => item.msg).filter(Boolean).join(". ") : data.detail;
        throw new Error(detail || "Password could not be changed.");
      }
      await logout();
      router.replace("/login");
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Password could not be changed.");
    } finally {
      setSaving(false);
    }
  }

  if (!user) return <div className="page">Loading account…</div>;

  return <div className="page"><span className="badge">My account</span><h1 style={{ fontSize: 40, marginBottom: 8 }}>Account and security</h1><p style={{ color: "#526173", fontSize: 17 }}>Review your approved access and change your password.</p><div style={{ display: "grid", gridTemplateColumns: "minmax(280px,.75fr) minmax(340px,1fr)", gap: 20, marginTop: 24 }}><section className="card" style={{ padding: 25 }}><div className="auth-form-icon"><UserRound size={23} /></div><h2>{user.display_name}</h2><dl className="account-details"><div><dt>Email</dt><dd>{user.email}</dd></div><div><dt>Role</dt><dd>{roleLabels[user.role]}</dd></div><div><dt>Node</dt><dd>{user.node ? nodeLabels[user.node] : "Not assigned"}</dd></div><div><dt>Status</dt><dd>{user.status}</dd></div></dl></section><section className="card" style={{ padding: 25 }}><div className="auth-form-icon"><KeyRound size={23} /></div><h2>Change password</h2><p style={{ color: "#667085" }}>Changing your password signs out every active session, including this one.</p><form className="auth-form" onSubmit={changePassword}><label>Current password<input required type="password" autoComplete="current-password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label><label>New password<input required type="password" minLength={12} autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /><small>At least 12 characters with uppercase, lowercase and a number.</small></label><label>Confirm new password<input required type="password" minLength={12} autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>{error && <div className="auth-error" role="alert">{error}</div>}<button type="submit" disabled={saving}>{saving ? "Changing password…" : "Change password"}</button></form></section></div></div>;
}
