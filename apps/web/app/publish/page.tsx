"use client";

import { useMemo, useState, type CSSProperties } from "react";
import Link from "next/link";

const API_BASE_URL = "http://localhost:18080";

type ValidationMessage = {
  level: "success" | "warning" | "error";
  message: string;
};

type ImportedService = {
  id: string | null;
  name: string;
  provider: string;
  category: string;
  version: string;
  description?: string | null;
  trust_badge: string;
  lifecycle_status: string;
  repository_url: string;
  repository_branch: string;
  manifest_path: string;
  interface_type: string;
  orchestration_mode: string;
  adapter_type?: string | null;
  container_name: string;
  image?: string | null;
  dockerfile?: string | null;
  internal_port: string;
  health_path: string;
  input_type?: string | null;
  output_type?: string | null;
  operation_name: string;
  input_message_name?: string | null;
  output_message_name?: string | null;
  proto_uri?: string | null;
  contract_uri?: string | null;
  interface_contract?: Record<string, unknown>;
};

type PreviewResponse = {
  status: "valid" | "warning" | "invalid";
  raw_manifest: Record<string, unknown>;
  service: ImportedService | null;
  validation: ValidationMessage[];
};

type ConfirmedService = {
  id: string;
  name: string;
  provider: string;
  category: string;
  version: string;
  status: string;
  trust_badge: string;
  lifecycle_status: string;
  container_name: string;
  operation_name: string;
  proto_uri: string;
};

const exampleManifest = `{
  "schema_version": "1.0",
  "service": {
    "id": "example-http-service-ui",
    "name": "Example HTTP AI Service from UI",
    "provider": "Example Node",
    "category": "Example Inference",
    "version": "1.0.0",
    "description": "A Dockerized REST/FastAPI-style AI service onboarded through an AI-EFFECT sidecar adapter.",
    "trust_badge": "pending_review"
  },
  "runtime": {
    "type": "docker",
    "container_name": "example-http-service-ui-adapter",
    "image": "ghcr.io/iresi-eu/example-http-service-adapter:1.0.0",
    "internal_port": "8080",
    "health_path": "/health"
  },
  "interface": {
    "type": "http",
    "operation_name": "Predict",
    "input_type": "JSON DataReference",
    "output_type": "Prediction Result DataReference",
    "contract_uri": "openapi.json",
    "http": {
      "method": "POST",
      "path": "/predict",
      "input_content_type": "application/json",
      "output_content_type": "application/json"
    }
  },
  "orchestration": {
    "mode": "sidecar",
    "adapter": "http-json"
  }
}`;

export default function PublishServicePage() {
  const [mode, setMode] = useState<"git" | "manual">("manual");

  const [repoUrl, setRepoUrl] = useState("https://github.com/IRESI-EU/ai-effect-solution-studio");
  const [branch, setBranch] = useState("main");
  const [manifestPath, setManifestPath] = useState("examples/service-manifest/ai-effect.http.example.json");
  const [manifestText, setManifestText] = useState(exampleManifest);

  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [confirmed, setConfirmed] = useState<ConfirmedService | null>(null);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canConfirm = useMemo(() => {
    return Boolean(preview?.service && preview.raw_manifest && preview.status !== "invalid");
  }, [preview]);

  const activeStep = confirmed
    ? 4
    : preview?.status === "invalid"
      ? 2
      : preview?.status === "valid" || preview?.status === "warning"
        ? 3
        : 1;

  async function previewFromGit() {
    setLoading(true);
    setConfirmed(null);
    setError(null);
    setPreview(null);

    try {
      const response = await fetch(`${API_BASE_URL}/services/import/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_url: repoUrl,
          branch,
          manifest_path: manifestPath,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || "Git manifest preview failed.");
      }

      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Git manifest preview failed.");
    } finally {
      setLoading(false);
    }
  }

  async function previewManual() {
    setLoading(true);
    setConfirmed(null);
    setError(null);
    setPreview(null);

    try {
      const manifest = JSON.parse(manifestText);

      const response = await fetch(`${API_BASE_URL}/services/import/preview-manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_url: repoUrl || "manual-upload",
          branch: branch || "main",
          manifest_path: manifestPath || "ai-effect.service.json",
          manifest,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data?.detail || "Manual manifest preview failed.");
      }

      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Manual manifest preview failed.");
    } finally {
      setLoading(false);
    }
  }

  async function confirmImport() {
    if (!preview?.raw_manifest) {
      setError("Preview a valid manifest before confirming import.");
      return;
    }

    setConfirming(true);
    setError(null);
    setConfirmed(null);

    try {
      const response = await fetch(`${API_BASE_URL}/services/import/confirm-manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_url: repoUrl || "manual-upload",
          branch: branch || "main",
          manifest_path: manifestPath || "ai-effect.service.json",
          manifest: preview.raw_manifest,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 409) {
          throw new Error(data?.detail || "This service already exists in the registry.");
        }
        throw new Error(formatApiError(data?.detail) || "Service import failed.");
      }

      setConfirmed(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Service import failed.");
    } finally {
      setConfirming(false);
    }
  }

  function loadExample() {
    setMode("manual");
    setRepoUrl("https://github.com/IRESI-EU/ai-effect-solution-studio");
    setBranch("main");
    setManifestPath("examples/service-manifest/ai-effect.http.example.json");
    setManifestText(exampleManifest);
    setPreview(null);
    setConfirmed(null);
    setError(null);
  }

  return (
    <main className="page publish-page" style={pageStyle}>
      <section style={heroStyle}>
        <p style={eyebrowStyle}>Node Provider Onboarding</p>
        <h1 style={titleStyle}>Publish my service</h1>
        <p style={subtitleStyle}>
          Add a Dockerized AI service to the AI-EFFECT marketplace through a guided workflow. The
          service will be submitted for review before becoming fully validated.
        </p>

        <div style={heroActionsStyle}>
          <Link href="/catalogue" style={secondaryButtonStyle}>
            View Catalogue
          </Link>
          <Link href="/admin" style={secondaryButtonStyle}>
            Admin Governance
          </Link>
        </div>
      </section>

      <div className="publish-workbench">
        <aside className="card publish-step-card">
          <p style={{ ...eyebrowStyle, marginBottom: 16 }}>Onboarding progress</p>
          {[
            ["1", "Service profile", "Provider and service identity"],
            ["2", "Interface contract", "Inputs, outputs and protocol"],
            ["3", "Deployment details", "Container and runtime settings"],
            ["4", "Review & submit", "Validate and publish for review"],
          ].map(([number, title, description], index) => (
            <div className={`publish-step${index + 1 === activeStep ? " publish-step-active" : ""}`} key={number}>
              <span className="publish-step-number">{number}</span>
              <div><strong>{title}</strong><small>{description}</small></div>
            </div>
          ))}
          <div className="publish-step-note">
            <strong>Manifest-powered</strong>
            <span>The guided steps map directly to your existing AI-EFFECT service manifest.</span>
          </div>
        </aside>

        <div className="publish-main-column">
      <section style={cardStyle}>
        <div style={{ marginBottom: 17 }}>
          <p style={eyebrowStyle}>Import manifest</p>
          <h2 style={{ ...sectionTitleStyle, marginTop: 6 }}>Service declaration</h2>
          <p style={{ ...helpTextStyle, marginTop: 7 }}>Choose how to load the manifest that describes your service.</p>
        </div>
        <div style={tabRowStyle}>
          <button
            type="button"
            onClick={() => setMode("manual")}
            style={mode === "manual" ? activeTabStyle : tabStyle}
          >
            Paste manifest JSON
          </button>
          <button
            type="button"
            onClick={() => setMode("git")}
            style={mode === "git" ? activeTabStyle : tabStyle}
          >
            Import from Git repository
          </button>
        </div>

        <div style={noticeStyle}>
          <strong>Required:</strong> every service must be Dockerized and must declare an
          AI-EFFECT service manifest. A <code>.proto</code> file is required only for
          <code> grpc</code> services.
        </div>

        <div style={gridStyle}>
          <label style={labelStyle}>
            Repository URL
            <input
              value={repoUrl}
              onChange={(event) => setRepoUrl(event.target.value)}
              placeholder="https://github.com/OWNER/REPO"
              style={inputStyle}
            />
          </label>

          <label style={labelStyle}>
            Branch or tag
            <input
              value={branch}
              onChange={(event) => setBranch(event.target.value)}
              placeholder="main"
              style={inputStyle}
            />
          </label>

          <label style={{ ...labelStyle, gridColumn: "1 / -1" }}>
            Manifest path
            <input
              value={manifestPath}
              onChange={(event) => setManifestPath(event.target.value)}
              placeholder="ai-effect.service.json"
              style={inputStyle}
            />
          </label>
        </div>

        {mode === "manual" ? (
          <div style={{ marginTop: 18 }}>
            <div style={rowBetweenStyle}>
              <label style={sectionLabelStyle}>Manifest JSON</label>
              <button type="button" onClick={loadExample} style={smallButtonStyle}>
                Load example HTTP manifest
              </button>
            </div>

            <textarea
              value={manifestText}
              onChange={(event) => setManifestText(event.target.value)}
              spellCheck={false}
              style={textareaStyle}
            />

            <button
              type="button"
              onClick={previewManual}
              disabled={loading}
              style={primaryButtonStyle}
            >
              {loading ? "Previewing..." : "Preview pasted manifest"}
            </button>
          </div>
        ) : (
          <div style={{ marginTop: 18 }}>
            <p style={helpTextStyle}>
              Git import currently works for public repositories. For private repositories,
              use pasted manifest JSON until authenticated GitHub import is added.
            </p>
            <button
              type="button"
              onClick={previewFromGit}
              disabled={loading}
              style={primaryButtonStyle}
            >
              {loading ? "Previewing..." : "Preview from Git"}
            </button>
          </div>
        )}

        {error && <div style={errorBoxStyle}>{error}</div>}
      </section>

      {preview && (
        <section style={cardStyle}>
          <div style={rowBetweenStyle}>
            <div>
              <p style={eyebrowStyle}>Manifest preview</p>
              <h2 style={sectionTitleStyle}>Validation result</h2>
            </div>
            <span style={statusBadgeStyle(preview.status)}>{preview.status.toUpperCase()}</span>
          </div>

          <div style={validationListStyle}>
            {preview.validation.map((item, index) => (
              <div key={`${item.level}-${index}`} style={validationItemStyle(item.level)}>
                <strong>{item.level.toUpperCase()}</strong>
                <span>{item.message}</span>
              </div>
            ))}
          </div>

          {preview.service && <ServicePreview service={preview.service} />}

          <div style={confirmRowStyle}>
            <button
              type="button"
              onClick={confirmImport}
              disabled={!canConfirm || confirming}
              style={{
                ...primaryButtonStyle,
                opacity: !canConfirm || confirming ? 0.6 : 1,
                cursor: !canConfirm || confirming ? "not-allowed" : "pointer",
              }}
            >
              {confirming ? "Importing..." : "Confirm import to Catalogue"}
            </button>
          </div>
        </section>
      )}

      {confirmed && (
        <section style={successCardStyle}>
          <p style={eyebrowStyle}>Service imported</p>
          <h2 style={sectionTitleStyle}>{confirmed.name}</h2>
          <p style={successTextStyle}>
            The service was added to the registry as <strong>{confirmed.trust_badge}</strong> and
            lifecycle status <strong>{confirmed.lifecycle_status}</strong>.
          </p>

          <div style={detailsGridStyle}>
            <Detail label="Service ID" value={confirmed.id} />
            <Detail label="Provider" value={confirmed.provider} />
            <Detail label="Category" value={confirmed.category} />
            <Detail label="Operation" value={confirmed.operation_name} />
            <Detail label="Container" value={confirmed.container_name} />
            <Detail label="Contract / proto_uri" value={confirmed.proto_uri} />
          </div>

          <div style={heroActionsStyle}>
            <Link href="/catalogue" style={primaryLinkStyle}>
              Open Catalogue
            </Link>
            <Link href="/builder" style={secondaryButtonStyle}>
              Open Builder
            </Link>
            <Link href="/admin" style={secondaryButtonStyle}>
              Review in Admin
            </Link>
          </div>
        </section>
      )}
        <aside className="publish-review-callout">
          <span aria-hidden="true">i</span>
          <div><strong>Review before publication</strong><p>Your service will be reviewed by the AI-EFFECT team before it is available in the catalogue.</p></div>
        </aside>
        </div>
      </div>
    </main>
  );
}

function ServicePreview({ service }: { service: ImportedService }) {
  return (
    <div style={previewBoxStyle}>
      <h3 style={previewTitleStyle}>{service.name}</h3>
      <p style={previewDescriptionStyle}>{service.description || "No description provided."}</p>

      <div style={detailsGridStyle}>
        <Detail label="Service ID" value={service.id || "generated on import"} />
        <Detail label="Provider" value={service.provider} />
        <Detail label="Category" value={service.category} />
        <Detail label="Version" value={service.version} />
        <Detail label="Interface type" value={service.interface_type} />
        <Detail label="Orchestration mode" value={service.orchestration_mode} />
        <Detail label="Adapter type" value={service.adapter_type || "none"} />
        <Detail label="Docker image" value={service.image || service.dockerfile || "missing"} />
        <Detail label="Container" value={service.container_name} />
        <Detail label="Internal port" value={service.internal_port} />
        <Detail label="Health path" value={service.health_path} />
        <Detail label="Operation" value={service.operation_name} />
        <Detail label="Input type" value={service.input_type || "not declared"} />
        <Detail label="Output type" value={service.output_type || "not declared"} />
        <Detail label="Contract URI" value={service.contract_uri || "not declared"} />
        <Detail label="Compatibility proto_uri" value={service.proto_uri || "not declared"} />
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div style={detailStyle}>
      <span style={detailLabelStyle}>{label}</span>
      <span style={detailValueStyle}>{value}</span>
    </div>
  );
}

function formatApiError(detail: unknown): string | null {
  if (!detail) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "message" in item) {
          return String((item as { message: unknown }).message);
        }
        return JSON.stringify(item);
      })
      .join(" ");
  }
  return JSON.stringify(detail);
}

function statusBadgeStyle(status: PreviewResponse["status"]): CSSProperties {
  if (status === "valid") {
    return {
      ...badgeStyle,
      background: "#ecfdf5",
      color: "#047857",
      borderColor: "#a7f3d0",
    };
  }

  if (status === "warning") {
    return {
      ...badgeStyle,
      background: "#fffbeb",
      color: "#92400e",
      borderColor: "#fde68a",
    };
  }

  return {
    ...badgeStyle,
    background: "#fef2f2",
    color: "#b91c1c",
    borderColor: "#fecaca",
  };
}

function validationItemStyle(level: ValidationMessage["level"]): CSSProperties {
  if (level === "success") {
    return {
      ...validationItemBaseStyle,
      borderColor: "#bbf7d0",
      background: "#f0fdf4",
    };
  }

  if (level === "warning") {
    return {
      ...validationItemBaseStyle,
      borderColor: "#fde68a",
      background: "#fffbeb",
    };
  }

  return {
    ...validationItemBaseStyle,
    borderColor: "#fecaca",
    background: "#fef2f2",
  };
}

const pageStyle: CSSProperties = {
  maxWidth: 1380,
};

const heroStyle: CSSProperties = {
  marginBottom: 24,
};

const eyebrowStyle: CSSProperties = {
  margin: 0,
  fontSize: 12,
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#6543df",
};

const titleStyle: CSSProperties = {
  margin: "8px 0",
  fontSize: 42,
  lineHeight: 1.1,
  color: "#0f172a",
};

const subtitleStyle: CSSProperties = {
  maxWidth: 820,
  margin: "0 0 18px",
  fontSize: 16,
  lineHeight: 1.6,
  color: "#475569",
};

const heroActionsStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 10,
  marginTop: 18,
};

const cardStyle: CSSProperties = {
  background: "#ffffff",
  border: "1px solid #e5e4f1",
  borderRadius: 18,
  padding: 22,
  boxShadow: "0 12px 32px rgba(30, 24, 70, 0.07)",
  marginBottom: 22,
};

const successCardStyle: CSSProperties = {
  ...cardStyle,
  borderColor: "#bbf7d0",
  background: "#f0fdf4",
};

const tabRowStyle: CSSProperties = {
  display: "flex",
  gap: 8,
  marginBottom: 16,
  flexWrap: "wrap",
};

const tabStyle: CSSProperties = {
  border: "1px solid #cbd5e1",
  background: "#f8fafc",
  color: "#334155",
  borderRadius: 999,
  padding: "9px 14px",
  fontWeight: 700,
  cursor: "pointer",
};

const activeTabStyle: CSSProperties = {
  ...tabStyle,
  background: "#f0ecff",
  color: "#4f2bc9",
  borderColor: "#c9bcfa",
};

const noticeStyle: CSSProperties = {
  padding: 14,
  borderRadius: 14,
  background: "#f8fafc",
  border: "1px solid #e2e8f0",
  color: "#475569",
  fontSize: 14,
  lineHeight: 1.5,
  marginBottom: 18,
};

const gridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
  gap: 14,
};

const labelStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 7,
  fontSize: 13,
  fontWeight: 700,
  color: "#334155",
};

const sectionLabelStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 800,
  color: "#334155",
};

const inputStyle: CSSProperties = {
  width: "100%",
  border: "1px solid #cbd5e1",
  borderRadius: 12,
  padding: "11px 12px",
  fontSize: 14,
};

const textareaStyle: CSSProperties = {
  width: "100%",
  minHeight: 360,
  border: "1px solid #cbd5e1",
  borderRadius: 14,
  padding: 14,
  marginTop: 8,
  fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  fontSize: 13,
  lineHeight: 1.45,
  resize: "vertical",
};

const primaryButtonStyle: CSSProperties = {
  marginTop: 14,
  border: "none",
  background: "linear-gradient(135deg, #5b2cf2, #4320ca)",
  color: "#ffffff",
  borderRadius: 12,
  padding: "11px 16px",
  fontWeight: 800,
  cursor: "pointer",
};

const smallButtonStyle: CSSProperties = {
  border: "1px solid #cbd5e1",
  background: "#ffffff",
  color: "#334155",
  borderRadius: 10,
  padding: "7px 10px",
  fontWeight: 700,
  cursor: "pointer",
};

const secondaryButtonStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  border: "1px solid #cbd5e1",
  background: "#ffffff",
  color: "#334155",
  borderRadius: 12,
  padding: "10px 14px",
  fontWeight: 800,
  textDecoration: "none",
};

const primaryLinkStyle: CSSProperties = {
  ...secondaryButtonStyle,
  borderColor: "#5b2cf2",
  background: "#5b2cf2",
  color: "#ffffff",
};

const helpTextStyle: CSSProperties = {
  margin: "0 0 12px",
  color: "#64748b",
  fontSize: 14,
  lineHeight: 1.5,
};

const errorBoxStyle: CSSProperties = {
  marginTop: 16,
  padding: 14,
  borderRadius: 14,
  border: "1px solid #fecaca",
  background: "#fef2f2",
  color: "#991b1b",
  fontWeight: 700,
};

const rowBetweenStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
};

const sectionTitleStyle: CSSProperties = {
  margin: "4px 0 0",
  fontSize: 24,
  color: "#0f172a",
};

const badgeStyle: CSSProperties = {
  border: "1px solid",
  borderRadius: 999,
  padding: "7px 11px",
  fontSize: 12,
  fontWeight: 900,
};

const validationListStyle: CSSProperties = {
  display: "grid",
  gap: 10,
  marginTop: 16,
};

const validationItemBaseStyle: CSSProperties = {
  border: "1px solid",
  borderRadius: 14,
  padding: 12,
  display: "grid",
  gap: 4,
  color: "#334155",
  fontSize: 14,
};

const previewBoxStyle: CSSProperties = {
  marginTop: 18,
  border: "1px solid #e2e8f0",
  borderRadius: 16,
  padding: 18,
  background: "#f8fafc",
};

const previewTitleStyle: CSSProperties = {
  margin: 0,
  color: "#0f172a",
  fontSize: 22,
};

const previewDescriptionStyle: CSSProperties = {
  margin: "8px 0 16px",
  color: "#475569",
  lineHeight: 1.5,
};

const detailsGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
  gap: 10,
};

const detailStyle: CSSProperties = {
  border: "1px solid #e2e8f0",
  background: "#ffffff",
  borderRadius: 12,
  padding: 11,
  display: "grid",
  gap: 4,
};

const detailLabelStyle: CSSProperties = {
  fontSize: 11,
  color: "#64748b",
  textTransform: "uppercase",
  fontWeight: 800,
  letterSpacing: "0.04em",
};

const detailValueStyle: CSSProperties = {
  color: "#0f172a",
  fontSize: 13,
  wordBreak: "break-word",
};

const confirmRowStyle: CSSProperties = {
  marginTop: 18,
};

const successTextStyle: CSSProperties = {
  color: "#166534",
  lineHeight: 1.5,
};
