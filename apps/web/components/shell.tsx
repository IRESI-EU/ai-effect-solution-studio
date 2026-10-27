"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import {
  Boxes, ChevronRight, CircleUserRound, CloudCog, Database, LayoutDashboard,
  LogIn, LogOut, Menu, Network, PackagePlus, ShieldCheck, Sparkles, UserPlus, X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { nodeLabels, roleLabels, useAuth, type UserRole } from "./auth-context";

const allNavItems = [
  { label: "Dashboard", href: "/", icon: LayoutDashboard, roles: null },
  { label: "Catalogue", href: "/catalogue", icon: Boxes, roles: null },
  { label: "Publish service", href: "/publish", icon: PackagePlus, roles: ["node_manager", "platform_admin"] as UserRole[] },
  { label: "Build solution", href: "/builder", icon: Network, roles: ["solution_designer", "node_manager", "platform_admin"] as UserRole[] },
  { label: "Design with AI", href: "/design-ai", icon: Sparkles, roles: ["solution_designer", "node_manager", "platform_admin"] as UserRole[] },
  { label: "Solutions", href: "/solutions", icon: Database, roles: ["solution_designer", "node_manager", "platform_admin"] as UserRole[] },
  { label: "Deployments", href: "/deployments", icon: CloudCog, roles: ["solution_designer", "node_manager", "platform_admin"] as UserRole[] },
  { label: "My account", href: "/account", icon: CircleUserRound, roles: ["solution_designer", "node_manager", "platform_admin"] as UserRole[] },
  { label: "Admin", href: "/admin", icon: ShieldCheck, roles: ["platform_admin"] as UserRole[] },
];

const authPages = new Set(["/login", "/register", "/registration-pending"]);

function isPublicPath(pathname: string) {
  return pathname === "/" || pathname.startsWith("/catalogue");
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, logout } = useAuth();
  const environmentLabel = process.env.NEXT_PUBLIC_ENVIRONMENT_LABEL || "Local environment";
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [designAIEnabled, setDesignAIEnabled] = useState(false);

  useEffect(() => {
    fetch("/api/design-ai/config", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : null)
      .then((value) => setDesignAIEnabled(value?.enabled === true))
      .catch(() => setDesignAIEnabled(false));
  }, []);

  const navItems = useMemo(
    () => allNavItems.filter((item) => (item.href !== "/design-ai" || designAIEnabled) && (!item.roles || (user && item.roles.includes(user.role)))),
    [user, designAIEnabled],
  );
  const deniedByRole = !!user && (
    (pathname.startsWith("/admin") && user.role !== "platform_admin") ||
    (pathname.startsWith("/publish") && !["node_manager", "platform_admin"].includes(user.role))
  );

  useEffect(() => {
    if (!loading && !user && !isPublicPath(pathname) && !authPages.has(pathname)) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, pathname, router, user]);

  if (authPages.has(pathname)) return <>{children}</>;
  if ((!isPublicPath(pathname) && loading) || (!isPublicPath(pathname) && !user)) {
    return <div className="auth-loading">Checking your account…</div>;
  }
  if (deniedByRole) {
    return (
      <div className="auth-loading"><div className="access-denied-card">
        <ShieldCheck size={34} /><h1>Access restricted</h1>
        <p>Your account does not have permission to open this area.</p>
        <Link href="/">Return to dashboard</Link>
      </div></div>
    );
  }

  function isActive(href: string) {
    return href === "/" ? pathname === "/" : pathname.startsWith(href);
  }

  async function signOut() {
    await logout();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="app-shell">
      <button className="mobile-menu-button" type="button" aria-label={navigationOpen ? "Close navigation" : "Open navigation"} aria-expanded={navigationOpen} onClick={() => setNavigationOpen((open) => !open)}>
        {navigationOpen ? <X size={20} /> : <Menu size={20} />}
      </button>
      {navigationOpen && <button className="sidebar-backdrop" type="button" aria-label="Close navigation" onClick={() => setNavigationOpen(false)} />}

      <aside className={`sidebar${navigationOpen ? " sidebar-open" : ""}`}>
        <Link className="brand" href="/" aria-label="AI-EFFECT home">
          <Image className="brand-logo" src="/ai-effect-logo.png" alt="AI-EFFECT" width={184} height={48} priority />
        </Link>
        <div className="sidebar-section-label">Workspace</div>
        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map(({ label, href, icon: Icon }) => {
            const active = isActive(href);
            return <Link key={href} href={href} className={active ? "active" : undefined} aria-current={active ? "page" : undefined} onClick={() => setNavigationOpen(false)}>
              <Icon size={19} strokeWidth={1.9} aria-hidden="true" /><span>{label}</span>{active && <ChevronRight className="nav-arrow" size={16} aria-hidden="true" />}
            </Link>;
          })}
        </nav>

        <div className="orchestrator-card">
          <div className="orchestrator-title"><span className="status-dot" aria-hidden="true" /><strong>WP3 Orchestrator</strong></div>
          <p>Workflow submissions are checked by the backend before they reach WP3.</p>
          <div className="orchestrator-status"><span>Connection</span><strong>Checked on deploy</strong></div>
        </div>

        {user ? (
          <div className="sidebar-user authenticated-user-card">
            <div className="sidebar-user-avatar"><CircleUserRound size={22} aria-hidden="true" /></div>
            <Link href="/account" className="sidebar-user-copy"><strong>{user.display_name}</strong><span>{roleLabels[user.role]}</span>{user.node && <small>{nodeLabels[user.node]}</small>}</Link>
            <button type="button" className="sidebar-logout" onClick={signOut} aria-label="Sign out" title="Sign out"><LogOut size={17} /></button>
          </div>
        ) : (
          <div className="sidebar-auth-actions">
            <Link href="/login"><LogIn size={17} /> Sign in</Link>
            <Link href="/register"><UserPlus size={17} /> Request access</Link>
          </div>
        )}
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-copy"><strong>Trusted Energy AI Marketplace</strong><span>Discover, compose, validate, and run energy AI services</span></div>
          <div className="topbar-actions"><span className="environment-pill"><span aria-hidden="true" /> {environmentLabel}</span>
            {user ? <div className="topbar-avatar" aria-label={`Signed in as ${user.display_name}`}>{user.display_name.slice(0, 2).toUpperCase()}</div> : <Link className="topbar-sign-in" href="/login">Sign in</Link>}
          </div>
        </header>
        <main className="content-surface">{children}</main>
      </div>
    </div>
  );
}
