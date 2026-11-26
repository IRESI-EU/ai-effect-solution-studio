"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useRouter } from "next/navigation";
import {
  Boxes, CloudCog, Database, LayoutDashboard, LogIn, LogOut, Menu, Network, PackagePlus, ShieldCheck, UserPlus, X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { nodeLabels, roleLabels, useAuth, type UserRole } from "./auth-context";

const signedIn: UserRole[] = ["solution_designer", "node_manager", "platform_admin"];
const navGroups: { label: string; items: { label: string; href: string; icon: typeof LayoutDashboard; roles: UserRole[] | null }[] }[] = [
  {
    label: "Workspace",
    items: [
      { label: "Dashboard", href: "/", icon: LayoutDashboard, roles: null },
      { label: "Catalogue", href: "/catalogue", icon: Boxes, roles: null },
      { label: "Builder", href: "/builder", icon: Network, roles: signedIn },
      { label: "Solutions", href: "/solutions", icon: Database, roles: signedIn },
      { label: "Runs", href: "/deployments", icon: CloudCog, roles: signedIn },
    ],
  },
  { label: "Node team", items: [{ label: "Publish a service", href: "/publish", icon: PackagePlus, roles: ["node_manager", "platform_admin"] }] },
  { label: "Administration", items: [{ label: "Users and services", href: "/admin", icon: ShieldCheck, roles: ["platform_admin"] }] },
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

  const visibleGroups = useMemo(
    () =>
      navGroups
        .map((group) => ({ ...group, items: group.items.filter((item) => !item.roles || (user && item.roles.includes(user.role))) }))
        .filter((group) => group.items.length > 0),
    [user],
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

  // The Builder needs the full width for the canvas: the menu shrinks to icons there
  // and opens over the page when hovered or focused.
  const compact = pathname.startsWith("/builder");

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
    <div className={`app-shell${compact ? " app-shell--compact" : ""}`}>
      <button className="mobile-menu-button" type="button" aria-label={navigationOpen ? "Close navigation" : "Open navigation"} aria-expanded={navigationOpen} onClick={() => setNavigationOpen((open) => !open)}>
        {navigationOpen ? <X size={20} /> : <Menu size={20} />}
      </button>
      {navigationOpen && <button className="sidebar-backdrop" type="button" aria-label="Close navigation" onClick={() => setNavigationOpen(false)} />}

      <aside className={`sidebar${navigationOpen ? " sidebar-open" : ""}`}>
        <Link className="brand" href="/" aria-label="AI-EFFECT home">
          <Image className="brand-logo" src="/brand/ai-effect-logo-white.png" alt="AI-EFFECT" width={115} height={30} priority />
        </Link>
        {visibleGroups.map((group) => (
          <div key={group.label}>
            <div className="sidebar-section-label">{group.label}</div>
            <nav className="sidebar-nav" aria-label={group.label}>
              {group.items.map(({ label, href, icon: Icon }) => {
                const active = isActive(href);
                return (
                  <Link key={href} href={href} className={active ? "active" : undefined} aria-current={active ? "page" : undefined} title={compact ? label : undefined} onClick={() => setNavigationOpen(false)}>
                    <Icon strokeWidth={1.75} aria-hidden="true" />
                    <span>{label}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}
        <div className="sidebar-spacer" />

        {user ? (
          <div className="sidebar-user">
            <div className="sidebar-user-avatar" aria-hidden="true">{user.display_name.slice(0, 2).toUpperCase()}</div>
            <Link href="/account" className="sidebar-user-copy" onClick={() => setNavigationOpen(false)}>
              <strong>{user.display_name}</strong>
              <span>{roleLabels[user.role]}{user.node ? ` · ${nodeLabels[user.node]}` : ""}</span>
            </Link>
            <button type="button" className="sidebar-logout" onClick={signOut} aria-label="Sign out" title="Sign out"><LogOut size={16} /></button>
          </div>
        ) : (
          <div className="sidebar-auth-actions">
            <Link href="/login"><LogIn size={16} /> Sign in</Link>
            <Link href="/register"><UserPlus size={16} /> Request access</Link>
          </div>
        )}
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-actions">
            {environmentLabel !== "Production" && <span className="environment-pill"><span aria-hidden="true" />{environmentLabel}</span>}
            {user ? (
              <Link href="/account" className="topbar-avatar" aria-label={`Account: ${user.display_name}`}>{user.display_name.slice(0, 2).toUpperCase()}</Link>
            ) : (
              <Link className="topbar-sign-in" href="/login">Sign in</Link>
            )}
          </div>
        </header>
        <main className="content-surface">{children}</main>
      </div>
    </div>
  );
}
