import Link from "next/link";

const nav = [
  ["Dashboard", "/"],
  ["Catalogue", "/catalogue"],
  ["Publish service", "/publish"],
  ["Build solution", "/builder"],
  ["Solutions", "/solutions"],
  ["Deployments", "/deployments"],
  ["Admin", "/admin"],
];

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside style={{ width: 280, background: "#071426", color: "white", padding: 24 }}>
        <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 8 }}>AI-EFFECT</div>
        <div style={{ color: "#9fb3c8", fontSize: 14, marginBottom: 32 }}>
          Solution Studio
        </div>

        <nav style={{ display: "grid", gap: 10 }}>
          {nav.map(([label, href]) => (
            <Link
              key={href}
              href={href}
              style={{
                padding: "12px 14px",
                borderRadius: 12,
                color: "#dbeafe",
                background: "rgba(255,255,255,0.06)",
              }}
            >
              {label}
            </Link>
          ))}
        </nav>

        <div style={{ marginTop: 40, padding: 16, borderRadius: 16, background: "#0f2947" }}>
          <div style={{ fontWeight: 700 }}>WP3 Orchestrator</div>
          <p style={{ color: "#b9cee5", fontSize: 13, lineHeight: 1.5 }}>
            Connected through backend adapter layer.
          </p>
        </div>
      </aside>

      <main style={{ flex: 1 }}>
        <header
          style={{
            height: 72,
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0 32px",
            background: "white",
            borderBottom: "1px solid #e4e9f2",
          }}
        >
          <div>
            <strong>Trusted Energy AI Marketplace</strong>
            <div style={{ color: "#667085", fontSize: 13 }}>
              Publish, compose, validate, and deploy AI services
            </div>
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span className="badge">MVP Environment</span>
            <div style={{ width: 36, height: 36, borderRadius: "50%", background: "#dbeafe" }} />
          </div>
        </header>

        {children}
      </main>
    </div>
  );
}