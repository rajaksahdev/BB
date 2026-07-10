/**
 * Header auth control. Signed out: email/password sign-in + sign-up (Supabase)
 * or a dev-mode email sign-in (FR-05). Signed in: email, tier, and monthly
 * usage vs. the free-tier limit (FR-06).
 */

import { useState } from "react";
import { ApiError, type Me } from "../api";
import type { AuthMode } from "../useAuth";

interface Props {
  me: Me | null;
  signedIn: boolean;
  billingEnabled: boolean;
  mode: AuthMode;
  onSignInDev: (email: string) => Promise<void>;
  onSignIn: (email: string, password: string) => Promise<void>;
  /** Resolves true when email confirmation is pending. */
  onSignUp: (email: string, password: string) => Promise<boolean>;
  onSignOut: () => void;
  onUpgrade: () => void;
  onManageBilling: () => void;
}

export default function AuthBar({
  me,
  signedIn,
  billingEnabled,
  mode,
  onSignInDev,
  onSignIn,
  onSignUp,
  onSignOut,
  onUpgrade,
  onManageBilling,
}: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setErr(null);
    setInfo(null);
    try {
      await action();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : (e as Error).message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await run(async () => {
      if (mode === "dev") {
        await onSignInDev(email);
      } else {
        await onSignIn(email, password);
      }
    });
  }

  async function signUp() {
    await run(async () => {
      const needsConfirmation = await onSignUp(email, password);
      if (needsConfirmation) {
        setInfo("Check your email to confirm your account, then sign in.");
      }
    });
  }

  if (!signedIn || !me) {
    if (signedIn && !me) {
      // Session exists but /me hasn't loaded yet (e.g. free-tier API waking up).
      return <div className="auth-bar signed-in muted">Loading account…</div>;
    }
    return (
      <form className="auth-bar" onSubmit={submit}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          aria-label="Email"
          autoComplete="email"
          required
        />
        {mode === "supabase" && (
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="password"
            aria-label="Password"
            autoComplete="current-password"
            minLength={6}
            required
          />
        )}
        <button type="submit" disabled={busy}>
          {busy ? "…" : mode === "dev" ? "Sign in (dev)" : "Sign in"}
        </button>
        {mode === "supabase" && (
          <button type="button" disabled={busy} onClick={signUp}>
            Sign up
          </button>
        )}
        {err && <span className="auth-err">{err}</span>}
        {info && <span className="auth-info">{info}</span>}
      </form>
    );
  }

  const limitLabel =
    me.monthly_limit === null
      ? "Pro · unlimited"
      : `${me.usage_this_month} / ${me.monthly_limit} saved this month`;

  return (
    <div className="auth-bar signed-in">
      <div className="auth-user">
        <span className="auth-email">{me.email}</span>
        <span className={`tier-pill tier-${me.tier}`}>{me.tier}</span>
      </div>
      <span className="auth-usage">{limitLabel}</span>
      <div className="auth-actions">
        {billingEnabled && me.tier === "free" && (
          <button className="upgrade-btn" onClick={onUpgrade}>
            Upgrade to Pro
          </button>
        )}
        {billingEnabled && me.tier === "pro" && (
          <button className="link-btn" onClick={onManageBilling}>
            Manage billing
          </button>
        )}
        <button className="link-btn" onClick={onSignOut}>
          Sign out
        </button>
      </div>
    </div>
  );
}
