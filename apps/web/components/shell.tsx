"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  ChevronRight,
  CircleUserRound,
  CloudCog,
  Database,
  LayoutDashboard,
  Menu,
  Network,
  PackagePlus,
  ShieldCheck,
  X,
} from "lucide-react";
import { useState } from "react";

const navItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard },
  { label: "Catalogue", href: "/catalogue", icon: Boxes },
  { label: "Publish service", href: "/publish", icon: PackagePlus },
  { label: "Build solution", href: "/builder", icon: Network },
  { label: "Solutions", href: "/solutions", icon: Database },
  { label: "Deployments", href: "/deployments", icon: CloudCog },
  { label: "Admin", href: "/admin", icon: ShieldCheck },
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [navigationOpen, setNavigationOpen] = useState(false);

  function isActive(href: string) {
    return href === "/" ? pathname === "/" : pathname.startsWith(href);
  }

  return (
    <div className="app-shell">
      <button
        className="mobile-menu-button"
        type="button"
        aria-label={navigationOpen ? "Close navigation" : "Open navigation"}
        aria-expanded={navigationOpen}
        onClick={() => setNavigationOpen((open) => !open)}
      >
        {navigationOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {navigationOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Close navigation"
          onClick={() => setNavigationOpen(false)}
        />
      )}

      <aside className={`sidebar${navigationOpen ? " sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">AI</div>
          <div className="brand-copy">
            <strong>AI-EFFECT</strong>
            <span>Solution Studio</span>
          </div>
        </div>

        <div className="sidebar-section-label">Workspace</div>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map(({ label, href, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                className={active ? "active" : undefined}
                aria-current={active ? "page" : undefined}
                onClick={() => setNavigationOpen(false)}
              >
                <Icon size={19} strokeWidth={1.9} aria-hidden="true" />
                <span>{label}</span>
                {active && <ChevronRight className="nav-arrow" size={16} aria-hidden="true" />}
              </Link>
            );
          })}
        </nav>

        <div className="orchestrator-card">
          <div className="orchestrator-title">
            <span className="status-dot" aria-hidden="true" />
            <strong>WP3 Orchestrator</strong>
          </div>
          <p>Connected through the backend adapter layer and ready for trusted workflows.</p>
          <div className="orchestrator-status">
            <span>System status</span>
            <strong>Operational</strong>
          </div>
        </div>

        <div className="sidebar-user">
          <div className="sidebar-user-avatar"><CircleUserRound size={22} aria-hidden="true" /></div>
          <div className="sidebar-user-copy">
            <strong>TEF Operator</strong>
            <span>admin@ai-effect.eu</span>
          </div>
          <ChevronRight size={16} aria-hidden="true" />
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-copy">
            <strong>Trusted Energy AI Marketplace</strong>
            <span>Publish, compose, validate, and deploy AI services</span>
          </div>
          <div className="topbar-actions">
            <span className="environment-pill"><span aria-hidden="true" /> MVP Environment</span>
            <div className="topbar-avatar" aria-label="Signed in as TEF Operator">AS</div>
          </div>
        </header>

        <main className="content-surface">{children}</main>
      </div>
    </div>
  );
}
