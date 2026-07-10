/**
 * Auth state. Two modes, chosen by whether Supabase env vars are configured:
 *
 *  - "supabase": real email/password auth via supabase-js. The session (and
 *    its auto-refreshing access token) is managed by the Supabase client; we
 *    mirror the access token into the api module for Bearer auth.
 *  - "dev": the backend accepts a `dev:<email>` bearer token (AUTH_DEV_MODE),
 *    so "signing in" just stores that token. Local development only.
 */

import { useCallback, useEffect, useState } from "react";
import { ApiError, getMe, setAuthToken, type Me } from "./api";
import { supabase } from "./supabase";

const TOKEN_KEY = "btlab.token"; // dev-mode token storage only

export type AuthMode = "supabase" | "dev";

export interface Auth {
  mode: AuthMode;
  token: string | null;
  me: Me | null;
  /** Dev mode only. */
  signInDev: (email: string) => Promise<void>;
  /** Supabase mode only. */
  signIn: (email: string, password: string) => Promise<void>;
  /** Supabase mode only. Resolves true when email confirmation is pending. */
  signUp: (email: string, password: string) => Promise<boolean>;
  signOut: () => void;
  refreshMe: () => Promise<void>;
}

export function useAuth(): Auth {
  const mode: AuthMode = supabase ? "supabase" : "dev";
  const [token, setToken] = useState<string | null>(() =>
    supabase ? null : localStorage.getItem(TOKEN_KEY),
  );
  const [me, setMe] = useState<Me | null>(null);

  // Keep the api module's token in sync with our state.
  useEffect(() => {
    setAuthToken(token);
  }, [token]);

  // Supabase mode: adopt the persisted session and follow auth changes
  // (sign-in, sign-out, automatic token refresh).
  useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => {
      setToken(data.session?.access_token ?? null);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setToken(session?.access_token ?? null);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  const refreshMe = useCallback(async () => {
    if (!token) {
      setMe(null);
      return;
    }
    try {
      setMe(await getMe());
    } catch (e) {
      if (supabase) {
        // Don't drop the Supabase session on transient API errors (e.g. the
        // free-tier server waking up); only a definitive 401 signs out.
        if (e instanceof ApiError && e.status === 401) {
          void supabase.auth.signOut();
        }
        setMe(null);
      } else {
        // Dev token rejected (e.g. AUTH_DEV_MODE off) — drop it.
        localStorage.removeItem(TOKEN_KEY);
        setAuthToken(null);
        setToken(null);
        setMe(null);
      }
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

  const signIn = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error("Supabase auth is not configured.");
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error(error.message);
    // onAuthStateChange picks up the session and sets the token.
  }, []);

  const signUp = useCallback(async (email: string, password: string) => {
    if (!supabase) throw new Error("Supabase auth is not configured.");
    const { data, error } = await supabase.auth.signUp({ email, password });
    if (error) throw new Error(error.message);
    // No session back == the project requires email confirmation first.
    return data.session === null;
  }, []);

  const signOut = useCallback(() => {
    if (supabase) {
      void supabase.auth.signOut();
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    setAuthToken(null);
    setToken(null);
    setMe(null);
  }, []);

  return { mode, token, me, signInDev, signIn, signUp, signOut, refreshMe };
}
