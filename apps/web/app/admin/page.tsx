"use client";

import { useEffect, useMemo, useState } from "react";


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
};

export default function AdminPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionServiceId, setActionServiceId] = useState<string | null>(null);
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
        await loadServices();
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
              Service governance
            </h1>

            <p style={{ color: "#526173", fontSize: 17, maxWidth: 950 }}>
              Review imported and published services, manage lifecycle status,
              and control which provider nodes are available in Catalogue and
              Builder.
            </p>
          </div>

          <button
            onClick={loadServices}
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
