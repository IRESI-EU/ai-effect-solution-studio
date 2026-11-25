"use client";

import { useEffect, useMemo, useState } from "react";
import { ServiceRuntimeManager } from "../../components/service-runtime-manager";


type Service = {
  id: string;
  name: string;
  provider: string;
  category: string;
  description?: string | null;
  input_type: string;
  output_type: string;
  version: string;
  status: string;
  trust_badge: string;
  lifecycle_status?: "active" | "deprecated" | "archived" | string;
  container_name?: string | null;
  operation_name?: string | null;
  internal_host?: string | null;
  internal_port?: string | null;
  interface_contract?: {
    onboarding?: {
      source_type?: string;
      source_revision?: string | null;
      runtime_status?: "needs_deployment" | "already_running";
      revision_pinned?: boolean;
      image_reviewed?: boolean;
      secrets_external?: boolean;
      health_verified?: boolean;
      registration_only_acknowledged?: boolean;
    };
    runtime_verification?: {
      status?: "verified" | "failed" | "not_verified";
      runtime_url?: string | null;
      http_status?: number | null;
      failure_reason?: string | null;
      message?: string;
    };
  } | null;
};

type UserRole = "solution_designer" | "node_manager" | "platform_admin";
type NodeCode = "germany" | "portugal" | "denmark" | "dutch";
type PortalUser = {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  node: NodeCode | null;
  status: "pending" | "active" | "rejected" | "suspended";
  created_at: string;
  last_login_at: string | null;
};

type LegacyOwnership = {
  solutions: Array<{ id: string; name: string; status: string; updated_at: string }>;
  deployments: Array<{ id: string; name: string; workflow_id: string; solution_id: string | null; status: string; created_at: string }>;
  services: Array<{ id: string; name: string; provider: string; status: string }>;
};

export default function AdminPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [users, setUsers] = useState<PortalUser[]>([]);
  const [legacy, setLegacy] = useState<LegacyOwnership>({ solutions: [], deployments: [], services: [] });
  const [ownershipChoices, setOwnershipChoices] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [actionServiceId, setActionServiceId] = useState<string | null>(null);
  const [actionUserId, setActionUserId] = useState<string | null>(null);
  const [actionOwnershipId, setActionOwnershipId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<
    "all" | "active" | "deprecated" | "archived"
  >("all");

  async function loadServices() {
    setError("");

    const res = await fetch(
      "/api/services?include_archived=true"
    );

    if (!res.ok) {
      throw new Error("Failed to load services.");
    }

    const data = await res.json();
    setServices(Array.isArray(data) ? data : []);
  }

  async function loadUsers() {
    const res = await fetch("/api/admin/users", { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load users.");
    const data = await res.json();
    setUsers(Array.isArray(data) ? data : []);
  }

  async function loadLegacyOwnership() {
    const res = await fetch("/api/admin/ownership/unassigned", { cache: "no-store" });
    if (!res.ok) throw new Error("Failed to load legacy ownership records.");
    setLegacy(await res.json());
  }

  async function assignLegacyRecord(kind: "solutions" | "deployments" | "services", id: string) {
    const choice = ownershipChoices[id];
    if (!choice) return;
    const label = kind === "services" ? "node" : "user";
    if (!window.confirm(`Assign this existing ${kind.slice(0, -1)} to the selected ${label}? Existing data will not be deleted.`)) return;
    setActionOwnershipId(id);
    setError("");
    try {
      const body = kind === "services"
        ? { node: choice }
        : kind === "solutions"
          ? { user_id: choice, include_unowned_deployments: true }
          : { user_id: choice };
      const response = await fetch(`/api/admin/ownership/${kind}/${id}/assign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Ownership assignment failed.");
      await Promise.all([loadLegacyOwnership(), loadServices()]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Ownership assignment failed.");
    } finally {
      setActionOwnershipId(null);
    }
  }

  function editUser(userId: string, changes: Partial<PortalUser>) {
    setUsers((current) => current.map((user) => user.id === userId ? { ...user, ...changes } : user));
  }

  async function updateUserStatus(user: PortalUser, action: "approve" | "reject" | "suspend" | "reactivate") {
    const prompt = action === "approve"
      ? `Confirm that you have verified ${user.email} and the requested affiliation before approving this account.`
      : `${action[0].toUpperCase()}${action.slice(1)} access for ${user.email}?`;
    const confirmed = window.confirm(prompt);
    if (!confirmed) return;
    setActionUserId(user.id);
    setError("");
    try {
      const response = await fetch(`/api/admin/users/${user.id}/${action}`, {
        method: "POST",
        headers: action === "approve" ? { "Content-Type": "application/json" } : undefined,
        body: action === "approve" ? JSON.stringify({ role: user.role, node: user.node }) : undefined,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Could not ${action} user.`);
      await loadUsers();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not ${action} user.`);
    } finally {
      setActionUserId(null);
    }
  }

  async function updateLifecycle(
    serviceId: string,
    action: "activate" | "deprecate" | "archive" | "restore"
  ) {
    const labels = {
      activate: "activate",
      deprecate: "deprecate",
      archive: "archive",
      restore: "restore",
    };

    const confirmed = window.confirm(
      `Are you sure you want to ${labels[action]} this service?`
    );

    if (!confirmed) {
      return;
    }

    setActionServiceId(serviceId);
    setError("");

    try {
      const res = await fetch(
        `/api/services/${serviceId}/${action}`,
        {
          method: "PUT",
        }
      );

      if (!res.ok) {
        throw new Error("Lifecycle update failed.");
      }

      await loadServices();
    } catch {
      setError("Could not update the service lifecycle status.");
    } finally {
      setActionServiceId(null);
    }
  }

  async function updateReview(
    serviceId: string,
    action: "approve" | "reject" | "reopen"
  ) {
    const labels = {
      approve: "approve",
      reject: "reject",
      reopen: "reopen the review for",
    };

    const confirmed = window.confirm(
      `Are you sure you want to ${labels[action]} this service?`
    );

    if (!confirmed) {
      return;
    }

    setActionServiceId(serviceId);
    setError("");

    try {
      const res = await fetch(
        `/api/services/${serviceId}/review/${action}`,
        {
          method: "POST",
        }
      );

      if (!res.ok) {
        throw new Error("Review update failed.");
      }

      await loadServices();
    } catch {
      setError("Could not update the service review status.");
    } finally {
      setActionServiceId(null);
    }
  }

  useEffect(() => {
    async function init() {
      try {
        await Promise.all([loadServices(), loadUsers(), loadLegacyOwnership()]);
      } catch {
        setError("Could not load services from the backend.");
      } finally {
        setLoading(false);
      }
    }

    init();
  }, []);

  const filteredServices = useMemo(() => {
    if (filter === "all") {
      return services;
    }

    return services.filter(
      (service) => getLifecycle(service) === filter
    );
  }, [services, filter]);

  const counts = useMemo(() => {
    return {
      all: services.length,
      active: services.filter((service) => getLifecycle(service) === "active")
        .length,
      deprecated: services.filter(
        (service) => getLifecycle(service) === "deprecated"
      ).length,
      archived: services.filter(
        (service) => getLifecycle(service) === "archived"
      ).length,
    };
  }, [services]);

  return (
    
      <div className="page">
        <span className="badge">Admin Governance</span>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 20,
            alignItems: "flex-start",
          }}
        >
          <div>
            <h1 style={{ fontSize: 40, marginBottom: 8 }}>
              Platform administration
            </h1>

            <p style={{ color: "#526173", fontSize: 17, maxWidth: 950 }}>
              Approve user registrations, assign roles and nodes, and govern
              services available in Catalogue and Builder.
            </p>
          </div>

          <button
            onClick={() => void Promise.all([loadServices(), loadUsers(), loadLegacyOwnership()])}
            style={{
              border: "1px solid #bae6fd",
              background: "white",
              color: "#075985",
              borderRadius: 12,
              padding: "12px 16px",
              fontWeight: 800,
              cursor: "pointer",
              whiteSpace: "nowrap",
            }}
          >
            Refresh
          </button>
        </div>

        <section className="card" style={{ marginTop: 24, overflow: "hidden" }}>
          <div style={{ padding: 20, borderBottom: "1px solid #e4e9f2" }}>
            <span className="badge">User access</span>
            <h2 style={{ margin: "10px 0 5px" }}>Registrations and onboarded users</h2>
            <p style={{ margin: 0, color: "#667085" }}>Verify each email and affiliation before approval. Node Managers can only govern services belonging to their assigned node.</p>
          </div>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", minWidth: 900 }}>
              <thead style={{ background: "#f8fafc" }}><tr><Th>User</Th><Th>Access level</Th><Th>Node</Th><Th>Status</Th><Th>Activity</Th><Th>Actions</Th></tr></thead>
              <tbody>
                {users.length === 0 && <tr><td colSpan={6} style={{ padding: 24, color: "#667085" }}>No user registrations found.</td></tr>}
                {users.map((user) => {
                  const busy = actionUserId === user.id;
                  return <tr key={user.id} style={{ borderTop: "1px solid #e4e9f2" }}>
                    <Td><strong style={{ display: "block" }}>{user.display_name}</strong><span style={{ color: "#667085" }}>{user.email}</span></Td>
                    <Td><select value={user.role} disabled={busy || user.status === "active"} onChange={(event) => editUser(user.id, { role: event.target.value as UserRole, node: event.target.value === "platform_admin" ? null : user.node })} style={{ padding: "8px 10px" }}><option value="solution_designer">Solution Designer</option><option value="node_manager">Node Manager</option><option value="platform_admin">Platform Admin</option></select></Td>
                    <Td><select value={user.node || ""} disabled={busy || user.status === "active" || user.role === "platform_admin"} onChange={(event) => editUser(user.id, { node: (event.target.value || null) as NodeCode | null })} style={{ padding: "8px 10px" }}><option value="">No node</option><option value="germany">German</option><option value="portugal">Portuguese</option><option value="denmark">Danish</option><option value="dutch">Dutch</option></select></Td>
                    <Td><span className="badge" style={userStatusStyle(user.status)}>{user.status}</span></Td>
                    <Td><span style={{ display: "block", color: "#667085" }}>Joined {formatAdminDate(user.created_at)}</span><small style={{ color: "#98a2b3" }}>{user.last_login_at ? `Last login ${formatAdminDate(user.last_login_at)}` : "Never signed in"}</small></Td>
                    <Td><div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      {(user.status === "pending" || user.status === "rejected") && <button disabled={busy || (user.role === "node_manager" && !user.node)} onClick={() => updateUserStatus(user, "approve")} style={buttonStyle("success", busy)}>Approve</button>}
                      {user.status === "pending" && <button disabled={busy} onClick={() => updateUserStatus(user, "reject")} style={buttonStyle("danger", busy)}>Reject</button>}
                      {user.status === "active" && <button disabled={busy} onClick={() => updateUserStatus(user, "suspend")} style={buttonStyle("warning", busy)}>Suspend</button>}
                      {user.status === "suspended" && <button disabled={busy} onClick={() => updateUserStatus(user, "reactivate")} style={buttonStyle("primary", busy)}>Reactivate</button>}
                    </div></Td>
                  </tr>;
                })}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card" style={{ marginTop: 24, padding: 20 }}>
          <span className="badge">Runtime verification</span>
          <h2 style={{ margin: "10px 0 5px" }}>Service connection and WP3 metadata</h2>
          <p style={{ margin: "0 0 16px", color: "#667085" }}>Edit the platform-network address separately from the logical WP3 container name, then verify connectivity from the portal API network. Connectivity does not certify operation correctness.</p>
          <div style={{ display: "grid", gap: 10 }}>
            {services.map((service) => <ServiceRuntimeManager key={service.id} service={service} onUpdated={loadServices} />)}
          </div>
        </section>

        <section className="card" style={{ marginTop: 24, overflow: "hidden" }}>
          <div style={{ padding: 20, borderBottom: "1px solid #e4e9f2" }}>
            <span className="badge">Data preservation</span>
            <h2 style={{ margin: "10px 0 5px" }}>Existing records awaiting ownership</h2>
            <p style={{ margin: 0, color: "#667085" }}>Records created before user login remain unchanged. Assign them after approving the correct account. Assigning a solution also assigns its currently unowned linked deployments.</p>
          </div>
          {legacy.solutions.length + legacy.deployments.length + legacy.services.length === 0 ? (
            <div style={{ padding: 24, color: "#027a48", fontWeight: 800 }}>All existing records have an owner.</div>
          ) : (
            <div style={{ padding: 20, display: "grid", gap: 24 }}>
              <LegacyTable title="Solutions" empty="No unassigned solutions." rows={legacy.solutions.map((item) => ({ id: item.id, primary: item.name, secondary: `${item.status} · updated ${formatAdminDate(item.updated_at)}` }))} choices={ownershipChoices} setChoice={(id, value) => setOwnershipChoices((current) => ({ ...current, [id]: value }))} options={users.filter((user) => user.status === "active").map((user) => ({ value: user.id, label: `${user.display_name} (${user.email})` }))} busyId={actionOwnershipId} onAssign={(id) => assignLegacyRecord("solutions", id)} />
              <LegacyTable title="Deployments not yet assigned" empty="No unassigned deployments." rows={legacy.deployments.map((item) => ({ id: item.id, primary: item.name, secondary: `${item.status} · ${item.workflow_id}` }))} choices={ownershipChoices} setChoice={(id, value) => setOwnershipChoices((current) => ({ ...current, [id]: value }))} options={users.filter((user) => user.status === "active").map((user) => ({ value: user.id, label: `${user.display_name} (${user.email})` }))} busyId={actionOwnershipId} onAssign={(id) => assignLegacyRecord("deployments", id)} />
              <LegacyTable title="Services without a node owner" empty="No unassigned services." rows={legacy.services.map((item) => ({ id: item.id, primary: item.name, secondary: item.provider }))} choices={ownershipChoices} setChoice={(id, value) => setOwnershipChoices((current) => ({ ...current, [id]: value }))} options={[{ value: "germany", label: "German Node" }, { value: "portugal", label: "Portuguese Node" }, { value: "denmark", label: "Danish Node" }, { value: "dutch", label: "Dutch Node" }]} busyId={actionOwnershipId} onAssign={(id) => assignLegacyRecord("services", id)} />
            </div>
          )}
        </section>

        <section
          className="card"
          style={{
            padding: 20,
            marginTop: 24,
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: 14,
          }}
        >
          <SummaryCard label="All services" value={counts.all} />
          <SummaryCard label="Active" value={counts.active} tone="good" />
          <SummaryCard
            label="Deprecated"
            value={counts.deprecated}
            tone="warning"
          />
          <SummaryCard label="Archived" value={counts.archived} tone="muted" />
        </section>

        <section
          className="card"
          style={{
            marginTop: 20,
            padding: 18,
            display: "flex",
            justifyContent: "space-between",
            gap: 14,
            alignItems: "center",
            flexWrap: "wrap",
          }}
        >
          <div style={{ color: "#526173" }}>
            Active services are available normally. Deprecated services remain
            visible with a warning. Archived services are hidden from Catalogue
            and Builder but retained for audit and old solution history.
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <FilterButton
              active={filter === "all"}
              onClick={() => setFilter("all")}
            >
              All
            </FilterButton>
            <FilterButton
              active={filter === "active"}
              onClick={() => setFilter("active")}
            >
              Active
            </FilterButton>
            <FilterButton
              active={filter === "deprecated"}
              onClick={() => setFilter("deprecated")}
            >
              Deprecated
            </FilterButton>
            <FilterButton
              active={filter === "archived"}
              onClick={() => setFilter("archived")}
            >
              Archived
            </FilterButton>
          </div>
        </section>

        <section className="card" style={{ marginTop: 24, overflow: "hidden" }}>
          {loading && (
            <div style={{ padding: 24, color: "#667085" }}>
              Loading services...
            </div>
          )}

          {error && (
            <div style={{ padding: 24, color: "#b42318", fontWeight: 800 }}>
              {error}
            </div>
          )}

          {!loading && !error && (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead style={{ background: "#f8fafc" }}>
                <tr>
                  <Th>Service</Th>
                  <Th>Provider</Th>
                  <Th>Lifecycle</Th>
                  <Th>Trust</Th>
                  <Th>Runtime</Th>
                  <Th>Actions</Th>
                </tr>
              </thead>

              <tbody>
                {filteredServices.length === 0 && (
                  <tr>
                    <td colSpan={6} style={{ padding: 24, color: "#667085" }}>
                      No services found for this filter.
                    </td>
                  </tr>
                )}

                {filteredServices.map((service) => {
                  const lifecycle = getLifecycle(service);
                  const reviewState = getReviewState(service);
                  const busy = actionServiceId === service.id;

                  return (
                    <tr
                      key={service.id}
                      style={{ borderTop: "1px solid #e4e9f2" }}
                    >
                      <Td>
                        <div style={{ fontWeight: 900, color: "#0f172a" }}>
                          {service.name}
                        </div>

                        <div
                          style={{
                            color: "#667085",
                            fontSize: 13,
                            marginTop: 5,
                            maxWidth: 420,
                          }}
                        >
                          {service.description || "No description provided."}
                        </div>

                        <div
                          style={{
                            color: "#667085",
                            fontSize: 12,
                            marginTop: 8,
                            fontFamily: "monospace",
                          }}
                        >
                          {service.id}
                        </div>
                      </Td>

                      <Td>
                        <div style={{ fontWeight: 800 }}>
                          {service.provider}
                        </div>
                        <div style={{ color: "#667085", fontSize: 13 }}>
                          {service.category}
                        </div>
                        <div style={{ color: "#667085", fontSize: 13 }}>
                          v{service.version}
                        </div>
                      </Td>

                      <Td>
                        <span
                          className="badge"
                          style={lifecycleBadgeStyle(lifecycle)}
                        >
                          {lifecycle}
                        </span>

                        {lifecycle === "deprecated" && (
                          <div
                            style={{
                              marginTop: 8,
                              color: "#b54708",
                              fontSize: 13,
                              maxWidth: 220,
                            }}
                          >
                            Existing solutions may still run, but this service
                            should not be preferred for new work.
                          </div>
                        )}

                        {lifecycle === "archived" && (
                          <div
                            style={{
                              marginTop: 8,
                              color: "#667085",
                              fontSize: 13,
                              maxWidth: 220,
                            }}
                          >
                            Hidden from Catalogue and Builder.
                          </div>
                        )}
                      </Td>

                      <Td>
                        <span
                          className="badge"
                          style={reviewBadgeStyle(reviewState)}
                        >
                          {service.trust_badge}
                        </span>
                        <div
                          style={{ color: "#667085", fontSize: 13, marginTop: 8 }}
                        >
                          Status: {service.status}
                        </div>
                      </Td>

                      <Td>
                        <div style={{ fontFamily: "monospace", fontSize: 13 }}>
                          {service.internal_host || service.container_name}:
                          {service.internal_port || "?"}
                        </div>
                        <div style={{ color: "#667085", fontSize: 13, marginTop: 6 }}>
                          {service.operation_name || "No operation"}
                        </div>
                        <div style={{ marginTop: 7, fontSize: 12, fontWeight: 800, color: service.interface_contract?.runtime_verification?.status === "verified" ? "#027a48" : "#b54708" }}>
                          {service.interface_contract?.runtime_verification?.status === "verified"
                            ? `Runtime verified${service.interface_contract.runtime_verification.http_status ? ` · HTTP ${service.interface_contract.runtime_verification.http_status}` : ""}`
                            : service.status === "approved"
                              ? "Governance approved · awaiting runtime verification"
                              : "Runtime not verified"}
                        </div>
                        {service.interface_contract?.onboarding && (
                          <div style={{ marginTop: 9, fontSize: 12, color: "#667085", lineHeight: 1.45 }}>
                            <strong style={{ display: "block", color: service.interface_contract.onboarding.runtime_status === "already_running" ? "#027a48" : "#b54708" }}>
                              {service.interface_contract.onboarding.runtime_status === "already_running"
                                ? "Provider claims runtime is running"
                                : "Operator deployment required"}
                            </strong>
                            Source: {service.interface_contract.onboarding.source_type || "not recorded"}
                            {service.interface_contract.onboarding.source_revision
                              ? ` · ${service.interface_contract.onboarding.source_revision}`
                              : ""}
                            <br />
                            Evidence: {[
                              service.interface_contract.onboarding.revision_pinned,
                              service.interface_contract.onboarding.image_reviewed,
                              service.interface_contract.onboarding.secrets_external,
                              service.interface_contract.onboarding.health_verified,
                            ].filter(Boolean).length}/4 provider checks
                          </div>
                        )}
                      </Td>

                      <Td>
                        <div
                          style={{
                            display: "flex",
                            gap: 10,
                            flexWrap: "wrap",
                            alignItems: "center",
                          }}
                        >
                          {lifecycle === "archived" && (
                            <button
                              onClick={() =>
                                updateLifecycle(service.id, "restore")
                              }
                              disabled={busy}
                              style={buttonStyle("primary", busy)}
                            >
                              {busy ? "Updating..." : "Restore"}
                            </button>
                          )}

                          {lifecycle !== "archived" &&
                            reviewState === "pending_review" && (
                              <>
                                <button
                                  onClick={() =>
                                    updateReview(service.id, "approve")
                                  }
                                  disabled={busy}
                                  style={buttonStyle("success", busy)}
                                >
                                  {busy ? "Updating..." : "Approve"}
                                </button>
                                <button
                                  onClick={() =>
                                    updateReview(service.id, "reject")
                                  }
                                  disabled={busy}
                                  style={buttonStyle("danger", busy)}
                                >
                                  Reject
                                </button>
                              </>
                            )}

                          {lifecycle === "active" &&
                            reviewState === "rejected" && (
                              <button
                                onClick={() =>
                                  updateReview(service.id, "reopen")
                                }
                                disabled={busy}
                                style={buttonStyle("primary", busy)}
                              >
                                {busy ? "Updating..." : "Reopen review"}
                              </button>
                            )}

                          {lifecycle === "active" &&
                            reviewState !== "rejected" && (
                              <button
                                onClick={() =>
                                  updateLifecycle(service.id, "deprecate")
                                }
                                disabled={busy}
                                style={buttonStyle("warning", busy)}
                              >
                                Deprecate
                              </button>
                            )}

                          {lifecycle === "deprecated" && (
                            <button
                              onClick={() =>
                                updateLifecycle(service.id, "activate")
                              }
                              disabled={busy}
                              style={buttonStyle("neutral", busy)}
                            >
                              Activate
                            </button>
                          )}

                          {lifecycle !== "archived" && (
                            <button
                              onClick={() =>
                                updateLifecycle(service.id, "archive")
                              }
                              disabled={busy}
                              style={buttonStyle("danger", busy)}
                            >
                              Archive
                            </button>
                          )}
                        </div>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </section>
      </div>
    
  );
}

function SummaryCard({
  label,
  value,
  tone = "neutral",
}: {
  label: string;
  value: number;
  tone?: "neutral" | "good" | "warning" | "muted";
}) {
  const background =
    tone === "good"
      ? "#ecfdf3"
      : tone === "warning"
      ? "#fffaeb"
      : tone === "muted"
      ? "#f2f4f7"
      : "#f8fafc";

  const color =
    tone === "good"
      ? "#027a48"
      : tone === "warning"
      ? "#b54708"
      : "#344054";

  return (
    <div style={{ background, color, padding: 16, borderRadius: 14 }}>
      <div style={{ fontSize: 13 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 900, marginTop: 4 }}>{value}</div>
    </div>
  );
}

function LegacyTable({ title, empty, rows, choices, setChoice, options, busyId, onAssign }: { title: string; empty: string; rows: Array<{ id: string; primary: string; secondary: string }>; choices: Record<string, string>; setChoice: (id: string, value: string) => void; options: Array<{ value: string; label: string }>; busyId: string | null; onAssign: (id: string) => void }) {
  return <div><h3 style={{ margin: "0 0 10px" }}>{title}</h3>{rows.length === 0 ? <p style={{ color: "#667085" }}>{empty}</p> : <div style={{ display: "grid", gap: 8 }}>{rows.map((row) => <div key={row.id} style={{ display: "grid", gridTemplateColumns: "minmax(220px, 1fr) minmax(240px, .7fr) auto", gap: 10, alignItems: "center", padding: 12, border: "1px solid #e4e9f2", borderRadius: 12 }}><div><strong style={{ display: "block" }}>{row.primary}</strong><small style={{ color: "#667085" }}>{row.secondary}</small></div><select value={choices[row.id] || ""} onChange={(event) => setChoice(row.id, event.target.value)} style={{ padding: "9px 10px" }}><option value="">Select owner</option>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select><button disabled={!choices[row.id] || busyId === row.id} onClick={() => onAssign(row.id)} style={buttonStyle("primary", busyId === row.id)}>{busyId === row.id ? "Assigning…" : "Assign"}</button></div>)}</div>}</div>;
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        border: active ? "1px solid #075985" : "1px solid #d0d5dd",
        background: active ? "#e0f2fe" : "white",
        color: active ? "#075985" : "#344054",
        padding: "8px 12px",
        borderRadius: 999,
        fontWeight: 800,
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th style={{ textAlign: "left", padding: 16 }}>{children}</th>;
}

function Td({ children }: { children: React.ReactNode }) {
  return (
    <td style={{ padding: 16, color: "#344054", verticalAlign: "top" }}>
      {children}
    </td>
  );
}

function getLifecycle(service: Service) {
  return service.lifecycle_status || "active";
}

function userStatusStyle(status: PortalUser["status"]) {
  if (status === "active") return { background: "#dcfae6", color: "#027a48" };
  if (status === "pending") return { background: "#fef0c7", color: "#b54708" };
  if (status === "suspended") return { background: "#f2f4f7", color: "#475467" };
  return { background: "#fee4e2", color: "#b42318" };
}

function formatAdminDate(value: string) {
  return new Intl.DateTimeFormat("en-IE", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
}

function getReviewState(service: Service) {
  const status = service.status.toLowerCase();
  const trustBadge = service.trust_badge.toLowerCase();

  if (status === "rejected" || trustBadge === "rejected") {
    return "rejected";
  }

  if (
    status === "approved" ||
    status === "validated" ||
    trustBadge === "validated"
  ) {
    return "validated";
  }

  return "pending_review";
}

function reviewBadgeStyle(status: string) {
  if (status === "validated") {
    return {
      background: "#dcfae6",
      color: "#027a48",
    };
  }

  if (status === "rejected") {
    return {
      background: "#fee4e2",
      color: "#b42318",
    };
  }

  return {
    background: "#f4ebff",
    color: "#6941c6",
  };
}

function lifecycleBadgeStyle(status: string) {
  if (status === "active") {
    return {
      background: "#dcfae6",
      color: "#027a48",
    };
  }

  if (status === "deprecated") {
    return {
      background: "#fef0c7",
      color: "#b54708",
    };
  }

  if (status === "archived") {
    return {
      background: "#f2f4f7",
      color: "#344054",
    };
  }

  return {};
}

function buttonStyle(
  tone: "primary" | "success" | "warning" | "danger" | "neutral",
  disabled: boolean
) {
  const colors = {
    primary: {
      border: "1px solid #bae6fd",
      background: "white",
      color: "#075985",
    },
    success: {
      border: "1px solid #abefc6",
      background: "white",
      color: "#027a48",
    },
    warning: {
      border: "1px solid #fedf89",
      background: "white",
      color: "#b54708",
    },
    danger: {
      border: "1px solid #fecdca",
      background: "white",
      color: "#b42318",
    },
    neutral: {
      border: "1px solid #d0d5dd",
      background: "white",
      color: "#344054",
    },
  };

  return {
    ...colors[tone],
    padding: "8px 10px",
    borderRadius: 10,
    fontWeight: 800,
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.6 : 1,
  };
}
