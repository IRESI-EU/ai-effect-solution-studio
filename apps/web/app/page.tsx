"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
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
import { useAuth } from "../components/auth-context";

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

async function loadDashboardData(authenticated: boolean): Promise<DashboardData> {
  try {
    const [servicesResponse, healthResponse, solutionsResponse, deploymentsResponse] = await Promise.all([
      fetch("/api/services", { cache: "no-store" }),
      fetch("/api/health", { cache: "no-store" }),
      authenticated ? fetch("/api/solutions", { cache: "no-store" }) : Promise.resolve(null),
      authenticated ? fetch("/api/deployments", { cache: "no-store" }) : Promise.resolve(null),
    ]);
    if (!servicesResponse.ok) throw new Error("Dashboard data is unavailable");

    return {
      services: await servicesResponse.json(),
      solutions: solutionsResponse?.ok ? await solutionsResponse.json() : [],
      deployments: deploymentsResponse?.ok ? await deploymentsResponse.json() : [],
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

export default function Page() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData>({ services: [], solutions: [], deployments: [], apiAvailable: true });

  useEffect(() => {
    void loadDashboardData(!!user).then(setData);
  }, [user]);
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
      value: user ? String(data.solutions.length) : "—",
      text: user ? "Your draft and submitted workflow designs" : "Sign in to view your saved solutions",
      icon: Network,
      colors: ["#e8f8fb", "#1489a4"],
    },
    {
      label: "Completed runs",
      value: user ? String(completedRuns) : "—",
      text: user ? `${data.deployments.length} deployment records in your workspace` : "Sign in to view deployment activity",
      icon: ShieldCheck,
      colors: ["#e9f8f1", "#20895e"],
    },
  ];

  return (
    <div className="page">
      <section className="dashboard-hero">
        <div className="dashboard-hero-content">
          <h1>Build trusted energy AI solutions</h1>
          <p>
            Find services from AI-EFFECT nodes, combine them into a workflow by hand or with Design with AI, and run
            them on the AI-EFFECT testing and experimentation facility.
          </p>
          <div className="dashboard-hero-actions">
            <Link href="/builder" className="ae-btn ae-btn--primary">
              Build a solution <ArrowRight size={16} />
            </Link>
            <Link href="/catalogue" className="ae-btn ae-btn--secondary">
              Browse the catalogue
            </Link>
          </div>
        </div>
      </section>

      {!data.apiAvailable && (
        <div className="dashboard-data-warning" role="status">
          Live data is temporarily unavailable. Refresh the page in a moment.
        </div>
      )}

      <SectionHeading eyebrow="" title="Your workspace" />
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

      <SectionHeading eyebrow="" title="What would you like to do?" />
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
            title="Recent runs"
            subtitle="The latest workflows you deployed"
            action={<Link href="/deployments">View all runs</Link>}
          />
          {recentDeployments.length === 0 ? (
            <p className="dashboard-empty-copy">No runs yet. Build a solution and deploy it to see it here.</p>
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
            title="Platform status"
            subtitle="Checked automatically"
            action={
              <span className={data.apiAvailable ? "dashboard-api-online" : "dashboard-api-offline"}>
                {data.apiAvailable ? "Online" : "Offline"}
              </span>
            }
          />
          <StatusRow name="Catalogue" detail={data.apiAvailable ? "Available" : "Not reachable"} active={data.apiAvailable} />
          <StatusRow name="Node services" detail="Checked when you prepare a deployment" />
          <StatusRow name="Orchestrator" detail="Confirmed before every run" />
        </div>
      </section>
    </div>
  );
}

function SectionHeading({ title }: { eyebrow?: string; title: string }) {
  return <div className="dashboard-section-heading"><h2 className="section__title">{title}</h2></div>;
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
