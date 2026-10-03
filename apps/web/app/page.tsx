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

export const dynamic = "force-dynamic";

type Service = { provider?: string | null; lifecycle_status?: string | null };
type Solution = { id: string; name: string; updated_at: string };
type Deployment = {
  workflow_id: string;
  name: string;
  status: string;
  created_at: string;
};

type DashboardData = {
  services: Service[];
  solutions: Solution[];
  deployments: Deployment[];
  apiAvailable: boolean;
};

async function loadDashboardData(): Promise<DashboardData> {
  const apiBaseUrl =
    process.env.INTERNAL_API_URL ||
    "http://api:8080";

  try {
    const [servicesResponse, solutionsResponse, deploymentsResponse, healthResponse] =
      await Promise.all([
        fetch(`${apiBaseUrl}/services`, { cache: "no-store" }),
        fetch(`${apiBaseUrl}/solutions`, { cache: "no-store" }),
        fetch(`${apiBaseUrl}/deployments`, { cache: "no-store" }),
        fetch(`${apiBaseUrl}/health`, { cache: "no-store" }),
      ]);

    if (!servicesResponse.ok || !solutionsResponse.ok || !deploymentsResponse.ok) {
      throw new Error("Dashboard data is unavailable");
    }

    return {
      services: await servicesResponse.json(),
      solutions: await solutionsResponse.json(),
      deployments: await deploymentsResponse.json(),
      apiAvailable: healthResponse.ok,
    };
  } catch {
    return { services: [], solutions: [], deployments: [], apiAvailable: false };
  }
}

const journeys = [
  {
    title: "For node providers",
    text: "Publish a Dockerized service, validate its interface metadata, and submit it for governance review.",
    href: "/publish",
    cta: "Publish a service",
    icon: PackagePlus,
    colors: ["#eeeaff", "#6744df"],
  },
  {
    title: "For solution designers",
    text: "Discover services, connect them visually, validate readiness, and prepare a traceable workflow run.",
    href: "/builder",
    cta: "Build a solution",
    icon: Sparkles,
    colors: ["#eaf2ff", "#3b6fd8"],
  },
  {
    title: "For platform operators",
    text: "Review service submissions, manage lifecycle states, and inspect deployment evidence without hiding technical detail.",
    href: "/admin",
    cta: "Open governance",
    icon: Users,
    colors: ["#e9f8f1", "#20895e"],
  },
];

export default async function Page() {
  const data = await loadDashboardData();
  const activeServices = data.services.filter(
    (service) => (service.lifecycle_status || "active") === "active"
  ).length;
  const providers = new Set(
    data.services.map((service) => service.provider).filter(Boolean)
  ).size;
  const completedRuns = data.deployments.filter(
    (deployment) => deployment.status === "completed"
  ).length;
  const recentDeployments = [...data.deployments]
    .sort(
      (left, right) =>
        new Date(right.created_at).getTime() - new Date(left.created_at).getTime()
    )
    .slice(0, 3);

  const stats = [
    {
      label: "Services",
      value: String(data.services.length),
      text: `${activeServices} active catalogue entries`,
      icon: Boxes,
      colors: ["#eeeaff", "#6744df"],
    },
    {
      label: "Providers",
      value: String(providers),
      text: "Providers represented in the catalogue",
      icon: Building2,
      colors: ["#eaf2ff", "#3b6fd8"],
    },
    {
      label: "Saved solutions",
      value: String(data.solutions.length),
      text: "Draft and submitted workflow designs",
      icon: Network,
      colors: ["#e8f8fb", "#1489a4"],
    },
    {
      label: "Completed runs",
      value: String(completedRuns),
      text: `${data.deployments.length} deployment records in total`,
      icon: ShieldCheck,
      colors: ["#e9f8f1", "#20895e"],
    },
  ];

  return (
    <div className="page">
      <section className="dashboard-hero">
        <div className="dashboard-hero-orb dashboard-hero-orb-one" />
        <div className="dashboard-hero-orb dashboard-hero-orb-two" />
        <div className="dashboard-hero-content">
          <span className="dashboard-hero-label">
            <Sparkles size={15} /> AI-EFFECT Web portal
          </span>
          <h1>Turn trusted energy AI services into deployable solutions.</h1>
          <p>
            Explore services from AI-EFFECT nodes, compose a visual workflow,
            validate deployment readiness, and inspect evidence from WP3 runs.
          </p>
          <div className="dashboard-hero-actions">
            <Link href="/catalogue" className="dashboard-primary-action">
              Explore services <ArrowRight size={17} />
            </Link>
            <Link href="/builder" className="dashboard-secondary-action">
              Build a solution
            </Link>
          </div>
        </div>
      </section>

      {!data.apiAvailable && (
        <div className="dashboard-data-warning" role="status">
          Live portal data is temporarily unavailable. Start the local API and refresh this page.
        </div>
      )}

      <SectionHeading eyebrow="Live workspace" title="Portal overview" />
      <section className="dashboard-metric-grid">
        {stats.map(({ icon: Icon, ...stat }) => (
          <article className="card dashboard-metric-card" key={stat.label}>
            <div className="dashboard-metric-icon" style={{ background: stat.colors[0], color: stat.colors[1] }}>
              <Icon size={22} />
            </div>
            <strong className="dashboard-metric-value">{stat.value}</strong>
            <h3>{stat.label}</h3>
            <p>{stat.text}</p>
          </article>
        ))}
      </section>

      <SectionHeading eyebrow="Choose a path" title="What do you want to accomplish?" />
      <section className="dashboard-role-grid">
        {journeys.map(({ icon: Icon, ...item }) => (
          <article className="card dashboard-role-card" key={item.title}>
            <div className="dashboard-role-icon" style={{ background: item.colors[0], color: item.colors[1] }}>
              <Icon size={24} />
            </div>
            <div>
              <h2>{item.title}</h2>
              <p>{item.text}</p>
              <Link href={item.href}>{item.cta} <ArrowRight size={15} /></Link>
            </div>
          </article>
        ))}
      </section>

      <section className="dashboard-lower-grid">
        <div className="card dashboard-panel-card">
          <CardHeader
            title="Recent deployment activity"
            subtitle="Latest records stored by the portal"
            action={<Link href="/deployments">View deployments</Link>}
          />
          {recentDeployments.length === 0 ? (
            <p className="dashboard-empty-copy">No deployment activity is available yet.</p>
          ) : (
            recentDeployments.map((deployment) => (
              <div className="dashboard-activity-row" key={deployment.workflow_id}>
                <div className="dashboard-activity-icon"><CloudCog size={18} /></div>
                <div>
                  <strong>{deployment.name}</strong>
                  <span>{deployment.workflow_id}</span>
                </div>
                <div className="dashboard-activity-meta">
                  <span className={`dashboard-run-status status-${deployment.status}`}>
                    {deployment.status}
                  </span>
                  <time>{formatDate(deployment.created_at)}</time>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="card dashboard-panel-card">
          <CardHeader
            title="Connection model"
            subtitle="What the portal verifies automatically"
            action={
              <span className={data.apiAvailable ? "dashboard-api-online" : "dashboard-api-offline"}>
                {data.apiAvailable ? "API available" : "API unavailable"}
              </span>
            }
          />
          <StatusRow name="Catalogue API" detail={data.apiAvailable ? "Responding locally" : "Not reachable"} active={data.apiAvailable} />
          <StatusRow name="Service runtimes" detail="Checked during deployment preparation" />
          <StatusRow name="WP3 submission" detail="Confirmed immediately before every run" />
        </div>
      </section>
    </div>
  );
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return <div className="dashboard-section-heading"><div><span>{eyebrow}</span><h2>{title}</h2></div></div>;
}

function CardHeader({ title, subtitle, action }: { title: string; subtitle: string; action: React.ReactNode }) {
  return <div className="dashboard-card-header"><div><h2>{title}</h2><p>{subtitle}</p></div>{action}</div>;
}

function StatusRow({ name, detail, active = true }: { name: string; detail: string; active?: boolean }) {
  return <div className="dashboard-status-row"><span className={active ? "is-active" : "is-inactive"} /><div><strong>{name}</strong><small>{detail}</small></div><CheckCircle2 size={15} aria-hidden="true" /></div>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IE", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
