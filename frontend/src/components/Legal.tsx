/**
 * Legal pages: Terms of Service and Refund Policy, served at /terms and
 * /refunds (the Render static site rewrites all paths to index.html, and App
 * routes on pathname). Payment-provider reviews expect both to be reachable
 * by URL, so keep these as real paths — not modal/state-only views.
 */

const SUPPORT_EMAIL = "sahdevrajak678@gmail.com";
const EFFECTIVE_DATE = "July 13, 2026";

interface Props {
  page: "terms" | "refunds";
  onBack: () => void;
}

export default function Legal({ page, onBack }: Props) {
  return (
    <div className="legal">
      <button className="link-btn legal-back" onClick={onBack}>
        ← Back to BacktestLab
      </button>
      {page === "terms" ? <Terms /> : <Refunds />}
      <p className="legal-contact">
        Questions? Contact us at <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>.
      </p>
    </div>
  );
}

function Terms() {
  return (
    <article>
      <h2>Terms of Service</h2>
      <p className="legal-date">Effective date: {EFFECTIVE_DATE}</p>

      <p>
        These Terms of Service (“Terms”) govern your use of BacktestLab (“the Service”), a
        web-based tool for backtesting cryptocurrency trading strategies against historical
        market data. By using the Service you agree to these Terms.
      </p>

      <h3>1. What BacktestLab is — and isn’t</h3>
      <p>
        BacktestLab is a research and educational software tool. It simulates how a trading
        strategy would have performed on historical price data. The Service:
      </p>
      <ul>
        <li>does <strong>not</strong> provide financial, investment, or trading advice;</li>
        <li>does <strong>not</strong> execute real trades or connect to exchange accounts;</li>
        <li>does <strong>not</strong> hold, transfer, or custody funds or cryptocurrency;</li>
        <li>does <strong>not</strong> sell trading signals or recommendations.</li>
      </ul>
      <p>
        Backtest results are hypothetical. Past performance does not guarantee future
        results. Any trading decisions you make are entirely your own responsibility.
      </p>

      <h3>2. Accounts</h3>
      <p>
        You can run backtests without an account. Creating an account (email and password)
        lets you save backtests. You are responsible for keeping your credentials secure and
        for all activity under your account. You must be at least 18 years old to create an
        account.
      </p>

      <h3>3. Plans and billing</h3>
      <p>
        The Service offers a free plan with usage limits and a paid Pro subscription that
        raises those limits. Payments are processed by Lemon Squeezy, our merchant of record,
        which handles checkout, billing, and applicable taxes. Subscriptions renew
        automatically at the end of each billing period unless canceled. You can cancel at
        any time from the billing portal; access continues until the end of the paid period.
        Refunds are handled per our <a href="/refunds">Refund Policy</a>.
      </p>

      <h3>4. Acceptable use</h3>
      <p>You agree not to:</p>
      <ul>
        <li>abuse, overload, or attempt to disrupt the Service or its infrastructure;</li>
        <li>attempt to access other users’ data or circumvent usage limits;</li>
        <li>resell, scrape, or redistribute the Service or its data without permission;</li>
        <li>use the Service for any unlawful purpose.</li>
      </ul>

      <h3>5. Market data</h3>
      <p>
        Historical price data is sourced from public market data APIs (currently Binance
        public market data). We do not guarantee its accuracy, completeness, or availability,
        and the data providers are not affiliated with BacktestLab.
      </p>

      <h3>6. Intellectual property</h3>
      <p>
        The Service, including its software, design, and content, is owned by BacktestLab.
        Your saved backtest configurations remain yours; you grant us the right to store and
        process them to operate the Service.
      </p>

      <h3>7. Availability and changes</h3>
      <p>
        The Service is provided “as is” and “as available.” We may modify, suspend, or
        discontinue features at any time. We may update these Terms; material changes will be
        posted on this page with a new effective date, and continued use constitutes
        acceptance.
      </p>

      <h3>8. Limitation of liability</h3>
      <p>
        To the maximum extent permitted by law, BacktestLab shall not be liable for any
        indirect, incidental, or consequential damages, or for any trading or investment
        losses, arising from use of the Service. Our total liability for any claim is limited
        to the amount you paid us in the twelve months preceding the claim.
      </p>

      <h3>9. Termination</h3>
      <p>
        You may stop using the Service or delete your account at any time. We may suspend or
        terminate accounts that violate these Terms.
      </p>
    </article>
  );
}

function Refunds() {
  return (
    <article>
      <h2>Refund Policy</h2>
      <p className="legal-date">Effective date: {EFFECTIVE_DATE}</p>

      <p>
        We want you to be happy with BacktestLab Pro. You can try every core feature on the
        free plan before paying, and if Pro isn’t right for you, this policy explains how
        refunds work.
      </p>

      <h3>14-day money-back guarantee</h3>
      <p>
        If you are not satisfied with your first Pro purchase, contact us within{" "}
        <strong>14 days</strong> of the purchase date and we will issue a full refund — no
        questions asked.
      </p>

      <h3>Renewals</h3>
      <p>
        Subscription renewals charged in error, or that you did not intend, are refundable if
        you contact us within <strong>14 days</strong> of the renewal charge, provided the
        Pro features were not substantially used after the renewal. To avoid unwanted
        renewals, you can cancel any time before the renewal date — you keep Pro access until
        the end of the period you already paid for.
      </p>

      <h3>How to request a refund</h3>
      <p>
        Email us at the address below from the email associated with your account, including
        your order number if you have it (it’s in your Lemon Squeezy receipt). Refunds are
        processed by Lemon Squeezy, our merchant of record, back to your original payment
        method — typically within 5–10 business days depending on your bank.
      </p>

      <h3>Cancellation</h3>
      <p>
        Canceling is separate from a refund: you can cancel your subscription at any time
        from the billing portal (Manage billing) and no further charges will occur. A
        cancellation alone does not trigger a refund for the current period.
      </p>
    </article>
  );
}
