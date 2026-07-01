/**
 * Minimal auth state for Phase 3/4. In dev mode the backend accepts a
 * `dev:<email>` bearer token (no Supabase needed), so "signing in" just stores
 * that token. The same shape will hold a real Supabase JWT later.
 */

import { useCallback, useEffect, useState } from "react";
import { getMe, setAuthToken, type Me } from "./api";

const TOKEN_KEY = "btlab.token";

export interface Auth {
  token: string | null;
  me: Me | null;
  signInDev: (email: string) => Promise<void>;
  signOut: () => void;
  refreshMe: () => Promise<void>;
}

export function useAuth(): Auth {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [me, setMe] = useState<Me | null>(null);

  // Keep the api module's token in sync with our state.
  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  const refreshMe = useCallback(async () => {
    if (!token) {
      setMe(null);
      return;
    }
    try {
      setMe(await getMe());
    } catch {
      // Token rejected (e.g. expired/invalid) — drop it.
      localStorage.removeItem(TOKEN_KEY);
      setAuthToken(null);
      setToken(null);
      setMe(null);
    }
  }, [token]);

  // Load /me whenever the token changes.
  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const signInDev = useCallback(async (email: string) => {
    const t = `dev:${email.trim().toLowerCase()}`;
    setAuthToken(t);
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setMe(await getMe()); // surfaces a bad email immediately
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setAuthToken(null);
    setToken(null);
    setMe(null);
  }, []);

  return { token, me, signInDev, signOut, refreshMe };
}
