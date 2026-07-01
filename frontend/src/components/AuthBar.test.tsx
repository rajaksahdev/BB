import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import AuthBar from "./AuthBar";
import type { Me } from "../api";

const noop = () => {};
const asyncNoop = async () => {};

const FREE_ME: Me = {
  id: "1",
  email: "free@example.com",
  tier: "free",
  usage_this_month: 2,
  monthly_limit: 5,
  remaining: 3,
};

describe("AuthBar", () => {
  it("shows a sign-in form when signed out", () => {
    render(
      <AuthBar
        me={null}
        signedIn={false}
        billingEnabled={false}
        onSignIn={asyncNoop}
        onSignOut={noop}
        onUpgrade={noop}
        onManageBilling={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows usage and an Upgrade button for a free user when billing is on", () => {
    render(
      <AuthBar
        me={FREE_ME}
        signedIn={true}
        billingEnabled={true}
        onSignIn={asyncNoop}
        onSignOut={noop}
        onUpgrade={noop}
        onManageBilling={noop}
      />,
    );
    expect(screen.getByText(/2 \/ 5 saved this month/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /upgrade to pro/i })).toBeInTheDocument();
  });

  it("hides the Upgrade button when billing is disabled", () => {
    render(
      <AuthBar
        me={FREE_ME}
        signedIn={true}
        billingEnabled={false}
        onSignIn={asyncNoop}
        onSignOut={noop}
        onUpgrade={noop}
        onManageBilling={noop}
      />,
    );
    expect(screen.queryByRole("button", { name: /upgrade to pro/i })).not.toBeInTheDocument();
  });

  it("shows Manage billing (not Upgrade) for a Pro user", () => {
    const proMe: Me = { ...FREE_ME, tier: "pro", monthly_limit: null, remaining: null };
    render(
      <AuthBar
        me={proMe}
        signedIn={true}
        billingEnabled={true}
        onSignIn={asyncNoop}
        onSignOut={noop}
        onUpgrade={noop}
        onManageBilling={noop}
      />,
    );
    expect(screen.getByRole("button", { name: /manage billing/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /upgrade to pro/i })).not.toBeInTheDocument();
  });
});
