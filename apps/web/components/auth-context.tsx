"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

export type UserRole = "solution_designer" | "node_manager" | "platform_admin";
export type NodeCode = "germany" | "portugal" | "denmark" | "dutch";

export type PortalUser = {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  node: NodeCode | null;
  status: "pending" | "active" | "rejected" | "suspended";
};

type AuthContextValue = {
  user: PortalUser | null;
  loading: boolean;
  refresh: () => Promise<PortalUser | null>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<PortalUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/me", { cache: "no-store" });
      if (!response.ok) {
        setUser(null);
        return null;
      }
      const currentUser = (await response.json()) as PortalUser;
      setUser(currentUser);
      return currentUser;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, loading, refresh, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export const roleLabels: Record<UserRole, string> = {
  solution_designer: "Solution Designer",
  node_manager: "Node Manager",
  platform_admin: "Platform Admin",
};

export const nodeLabels: Record<NodeCode, string> = {
  germany: "German Node",
  portugal: "Portuguese Node",
  denmark: "Danish Node",
  dutch: "Dutch Node",
};
