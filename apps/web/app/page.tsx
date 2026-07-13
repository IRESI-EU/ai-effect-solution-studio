import Link from "next/link";
import {
  ArrowRight,
  Boxes,
  Building2,
  CheckCircle2,
  CloudCog,
  Network,
  PackagePlus,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";

const stats = [
  { label: "Services", value: "12", text: "Validated and draft AI services", detail: "+3 this month", icon: Boxes, colors: ["#eeeaff", "#6744df"] },
  { label: "Providers", value: "5", text: "AI-EFFECT onboarding nodes", detail: "Across 4 regions", icon: Building2, colors: ["#eaf2ff", "#3b6fd8"] },
  { label: "Workflows", value: "8", text: "Solution drafts and deployments", detail: "2 currently active", icon: Network, colors: ["#e8f8fb", "#1489a4"] },
  { label: "Trust checks", value: "24", text: "Interface and metadata validations", detail: "100% passing", icon: ShieldCheck, colors: ["#e9f8f1", "#20895e"] },
];

const journeys = [
  {
    title: "For nodes",
    text: "Publish Dockerized AI services using guided metadata, interface validation, and governance approval.",
    href: "/publish",
    cta: "Publish my service",
    icon: PackagePlus,
    colors: ["#eeeaff", "#6744df"],
  },
  {
    title: "For AI vendors",
    text: "Discover trusted services, compose them visually, validate compatibility, and deploy AI solutions.",
    href: "/builder",
    cta: "Build a solution",
    icon: Sparkles,
    colors: ["#eaf2ff", "#3b6fd8"],
  },
  {
    title: "For TEF operators",
    text: "Review services, assign trust badges, monitor executions, and maintain platform governance.",
    href: "/admin",
    cta: "Review platform",
    icon: Users,
    colors: ["#e9f8f1", "#20895e"],
  },
];

const activity = [
  { title: "Service validated", text: "Grid Load Forecaster passed all trust checks", time: "12 min ago", icon: ShieldCheck },
  { title: "Workflow saved", text: "Renewable Dispatch Optimizer was updated", time: "1 hour ago", icon: Network },
  { title: "Deployment completed", text: "Workflow run wf-2038 completed successfully", time: "3 hours ago", icon: CloudCog },
];

export default function Page() {
  return (
    <div className="page">
      <section
        className="dashboard-hero"
        style={{
          position: "relative",
          overflow: "hidden",
          minHeight: 310,
          padding: "44px 48px",
          borderRadius: 22,
          color: "white",
          background: "linear-gradient(118deg, #25117e 0%, #5030da 55%, #7547ed 100%)",
          boxShadow: "0 20px 44px rgba(60, 32, 164, 0.22)",
        }}
      >
        <div style={{ position: "absolute", width: 360, height: 360, right: -90, top: -170, borderRadius: "50%", background: "rgba(255,255,255,0.08)" }} />
        <div style={{ position: "absolute", width: 230, height: 230, right: 205, bottom: -175, borderRadius: "50%", background: "rgba(158,123,255,0.34)" }} />
        <div style={{ position: "relative", zIndex: 2, maxWidth: 850 }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "7px 11px", border: "1px solid rgba(255,255,255,0.2)", borderRadius: 999, background: "rgba(255,255,255,0.09)", fontSize: 11, fontWeight: 800 }}>
            <Sparkles size={15} /> AI-EFFECT Solution Studio
          </span>
          <h1 style={{ maxWidth: 850, margin: "18px 0 14px", color: "white", fontSize: "clamp(36px, 4.5vw, 56px)", lineHeight: 1.04, letterSpacing: "-0.045em" }}>
            Build trusted energy AI solutions from validated service building blocks.
          </h1>
          <p style={{ maxWidth: 760, margin: 0, color: "#ded9fb", fontSize: 16, lineHeight: 1.65 }}>
            A marketplace and visual workflow studio for node providers, AI vendors, and TEF operators, built on top of the AI-EFFECT WP3 orchestrator.
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 27 }}>
            <Link href="/catalogue" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "12px 17px", borderRadius: 10, background: "white", color: "#4a29dd", fontWeight: 800, boxShadow: "0 9px 24px rgba(23,12,83,0.2)" }}>
              Explore catalogue <ArrowRight size={17} />
            </Link>
            <Link href="/publish" style={{ display: "inline-flex", alignItems: "center", padding: "12px 17px", border: "1px solid rgba(255,255,255,0.35)", borderRadius: 10, background: "rgba(255,255,255,0.08)", color: "white", fontWeight: 800 }}>
              Publish my service
            </Link>
          </div>
        </div>
      </section>

      <SectionHeading eyebrow="At a glance" title="Platform overview" trailing={<span style={{ display: "flex", alignItems: "center", gap: 7, color: "#71778f", fontSize: 11 }}><span style={{ width: 7, height: 7, borderRadius: "50%", background: "#22b979" }} /> Live MVP data</span>} />
      <section className="dashboard-metric-grid">
        {stats.map(({ icon: Icon, ...stat }) => (
          <article className="card dashboard-metric-card" key={stat.label} style={{ position: "relative", padding: 20 }}>
            <div style={{ display: "grid", width: 42, height: 42, placeItems: "center", borderRadius: 12, background: stat.colors[0], color: stat.colors[1] }}><Icon size={22} /></div>
            <div style={{ position: "absolute", top: 19, right: 20, fontSize: 30, fontWeight: 900, letterSpacing: "-0.04em" }}>{stat.value}</div>
            <h3 style={{ margin: "15px 0 3px", fontSize: 15 }}>{stat.label}</h3>
            <p style={{ margin: 0, color: "#68708a", fontSize: 11 }}>{stat.text}</p>
            <div style={{ marginTop: 13, color: "#85899b", fontSize: 10 }}>{stat.detail}</div>
          </article>
        ))}
      </section>

      <SectionHeading eyebrow="Get started" title="What would you like to do?" />
      <section className="dashboard-role-grid">
        {journeys.map(({ icon: Icon, ...item }) => (
          <article className="card dashboard-role-card" key={item.title} style={{ display: "flex", gap: 16, padding: 22 }}>
            <div style={{ display: "grid", width: 46, height: 46, flex: "0 0 46px", placeItems: "center", borderRadius: 13, background: item.colors[0], color: item.colors[1] }}><Icon size={24} /></div>
            <div>
              <h2 style={{ margin: "1px 0 8px", fontSize: 16 }}>{item.title}</h2>
              <p style={{ minHeight: 50, margin: "0 0 13px", color: "#606880", fontSize: 12, lineHeight: 1.55 }}>{item.text}</p>
              <Link href={item.href} style={{ display: "inline-flex", alignItems: "center", gap: 6, color: "#5d3ddd", fontSize: 11, fontWeight: 850 }}>{item.cta} <ArrowRight size={15} /></Link>
            </div>
          </article>
        ))}
      </section>

      <section className="dashboard-lower-grid">
        <div className="card" style={{ padding: 22 }}>
          <CardHeader title="Recent activity" subtitle="The latest changes across your workspace" action={<Link href="/deployments" style={{ color: "#5d3ddd", fontSize: 11, fontWeight: 800 }}>View all</Link>} />
          <div>
            {activity.map(({ icon: Icon, ...item }) => (
              <div className="dashboard-activity-row" key={item.title} style={{ display: "grid", gridTemplateColumns: "36px 1fr auto", alignItems: "center", gap: 12, padding: "13px 0", borderBottom: "1px solid #efedf5" }}>
                <div style={{ display: "grid", width: 34, height: 34, placeItems: "center", borderRadius: 10, background: "#f0edff", color: "#6544de" }}><Icon size={18} /></div>
                <div style={{ display: "grid", gap: 2 }}><strong style={{ fontSize: 11 }}>{item.title}</strong><span style={{ color: "#72778c", fontSize: 10 }}>{item.text}</span></div>
                <time style={{ color: "#9699a8", fontSize: 9 }}>{item.time}</time>
              </div>
            ))}
          </div>
        </div>

        <div className="card" style={{ padding: 22 }}>
          <CardHeader title="Platform status" subtitle="AI-EFFECT infrastructure" action={<span style={{ padding: "5px 9px", borderRadius: 999, background: "#e9f7f0", color: "#198456", fontSize: 9, fontWeight: 850 }}>All operational</span>} />
          <StatusRow name="WP3 Orchestrator" detail="Connected" />
          <StatusRow name="Catalogue API" detail="Healthy" />
          <StatusRow name="Trust validation" detail="Healthy" />
        </div>
      </section>
    </div>
  );
}

function SectionHeading({ eyebrow, title, trailing }: { eyebrow: string; title: string; trailing?: React.ReactNode }) {
  return <div style={{ display: "flex", alignItems: "end", justifyContent: "space-between", margin: "28px 2px 14px" }}><div><span style={{ color: "#6949e6", fontSize: 9, fontWeight: 900, letterSpacing: "0.12em", textTransform: "uppercase" }}>{eyebrow}</span><h2 style={{ margin: "5px 0 0", fontSize: 20, letterSpacing: "-0.02em" }}>{title}</h2></div>{trailing}</div>;
}

function CardHeader({ title, subtitle, action }: { title: string; subtitle: string; action: React.ReactNode }) {
  return <div style={{ display: "flex", alignItems: "start", justifyContent: "space-between", paddingBottom: 15, borderBottom: "1px solid #efedf5" }}><div><h2 style={{ margin: 0, fontSize: 16 }}>{title}</h2><p style={{ margin: "4px 0 0", color: "#73788d", fontSize: 10 }}>{subtitle}</p></div>{action}</div>;
}

function StatusRow({ name, detail }: { name: string; detail: string }) {
  return <div style={{ display: "grid", gridTemplateColumns: "8px 1fr auto", alignItems: "center", gap: 10, padding: "16px 3px", borderBottom: "1px solid #efedf5" }}><span style={{ width: 7, height: 7, borderRadius: "50%", background: "#2abe7d", boxShadow: "0 0 0 4px #e8f8f0" }} /><div style={{ display: "grid", gap: 2 }}><strong style={{ fontSize: 11 }}>{name}</strong><span style={{ color: "#74798e", fontSize: 9 }}>{detail}</span></div><span style={{ color: "#198456", fontSize: 9, fontWeight: 800 }}><CheckCircle2 size={14} /></span></div>;
}
