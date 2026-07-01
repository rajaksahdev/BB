/**
 * Header auth control. Signed out: a dev-mode email sign-in (FR-05). Signed in:
 * email, tier, and monthly usage vs. the free-tier limit (FR-06).
 */

import { useState } from "react";
import { ApiError, type Me } from "../api";

interface Props {
  me: Me | null;
  signedIn: boolean;
  billingEnabled: boolean;
  onSignIn: (email: string) => Promise<void>;
  onSignOut: () => void;
  onUpgrade: () => void;
  onManageBilling: () => void;
}

export default function AuthBar({
  me,
  signedIn,
  billingEnabled,
  onSignIn,
  onSignOut,
  onUpgrade,
  onManageBilling,
}: Props) {
  const [email, setEmail] = useState("you@example.com");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await onSignIn(email);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  if (!signedIn || !me) {
    return (
      <form className="auth-bar" onSubmit={submit}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          aria-label="Email"
          required
        />
        <button type="submit" disabled={busy}>
          {busy ? "…" : "Sign in (dev)"}
        </button>
        {err && <span className="auth-err">{err}</span>}
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
