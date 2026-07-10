/**
 * Supabase client — created only when the project env vars are present.
 *
 * With VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY set (production), useAuth
 * runs real email/password auth and the backend verifies the issued JWT
 * against the project's JWKS. Without them (local dev), the app falls back to
 * the backend's `dev:<email>` token mode.
 */

import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined;

export const supabase: SupabaseClient | null =
  url && anonKey ? createClient(url, anonKey) : null;
