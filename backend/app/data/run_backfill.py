"""CLI: backfill candles from Binance, then print a gap report.

Examples:
  python -m app.data.run_backfill                       # default: 3y, BTC+ETH, 1h+1d
  python -m app.data.run_backfill --years 2
  python -m app.data.run_backfill --symbols BTCUSDT ETHUSDT SOLUSDT --intervals 1h 1d
"""

import argparse
import json
import logging
from datetime import UTC, datetime, timedelta

from app.data.backfill import backfill
from app.data.gaps import gap_report

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
DEFAULT_INTERVALS = ["1h", "1d"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Binance candles into Postgres.")
    parser.add_argument("--years", type=float, default=3.0, help="History window in years.")
    parser.add_argument("--symbols", nargs="+", default=DEFAULT_SYMBOLS)
    parser.add_argument("--intervals", nargs="+", default=DEFAULT_INTERVALS)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    end = datetime.now(tz=UTC)
    start = end - timedelta(days=args.years * 365)

    summaries = []
    for symbol in args.symbols:
        for interval in args.intervals:
            summaries.append(backfill(symbol, interval, start, end))

    print("\n=== BACKFILL SUMMARY ===")
    for s in summaries:
        print(f"  {s['symbol']:<10} {s['interval']:<4} fetched={s['fetched']:>7} written={s['written']:>7}")

    print("\n=== GAP REPORT ===")
    for symbol in args.symbols:
        for interval in args.intervals:
            rep = gap_report(symbol, interval)
            print(
                f"  {symbol:<10} {interval:<4} count={rep['count']:>7} "
                f"gaps={rep['gap_segments']:>3} missing={rep['missing_candles']:>4} "
                f"range={rep.get('first', '-')[:10]}..{rep.get('last', '-')[:10]}"
            )
            if rep["gaps"]:
                print("    sample gaps:", json.dumps(rep["gaps"][:3]))


if __name__ == "__main__":
    main()
