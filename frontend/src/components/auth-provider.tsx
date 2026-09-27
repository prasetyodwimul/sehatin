"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { ApiError, SESSION_EXPIRED_EVENT } from "@/lib/api";
import { getCurrentUser, logoutAccount, type AuthUser } from "@/lib/auth";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  refreshAuth: () => Promise<AuthUser | null>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue>({
  status: "unauthenticated",
  user: null,
  refreshAuth: async () => {
    try { return await getCurrentUser(); } catch { return null; }
  },
  logout: logoutAccount,
});

export function AuthProvider({ children, initialUser, autoRefresh = true }: { children: React.ReactNode; initialUser?: AuthUser | null; autoRefresh?: boolean }) {
  const hasInitialState = initialUser !== undefined;
  const [status, setStatus] = useState<AuthStatus>(hasInitialState ? (initialUser ? "authenticated" : "unauthenticated") : "loading");
  const [user, setUser] = useState<AuthUser | null>(initialUser ?? null);

  const refreshAuth = useCallback(async () => {
    try {
      const current = await getCurrentUser();
      setUser(current);
      setStatus("authenticated");
      return current;
    } catch (error) {
      if (error instanceof ApiError && error.status !== 401) {
        setUser(null);
        setStatus("unauthenticated");
        throw error;
      }
      setUser(null);
      setStatus("unauthenticated");
      return null;
    }
  }, []);

  const logout = useCallback(async () => {
    await logoutAccount();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  useEffect(() => {
    const handleSessionExpired = () => {
      setUser(null);
      setStatus("unauthenticated");
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
  }, []);

  useEffect(() => {
    if (!autoRefresh || hasInitialState) return;
    let mounted = true;
    getCurrentUser().then((current) => {
      if (!mounted) return;
      setUser(current);
      setStatus("authenticated");
    }).catch(() => {
      if (!mounted) return;
      setUser(null);
      setStatus("unauthenticated");
    });
    return () => { mounted = false; };
  }, [autoRefresh, hasInitialState]);

  const value = useMemo(() => ({ status, user, refreshAuth, logout }), [logout, refreshAuth, status, user]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() { return useContext(AuthContext); }
