#!/usr/bin/env python3
"""Keepalive watchdog: probe a stall's /health on an interval.

Usage: keepalive.py <base_url> [--interval 300] [--fail-streak 3]

Prints one line per probe (timestamp, status, latency) and exits
non-zero when the failure streak reaches --fail-streak — wire it to
cron/systemd so a dead stall pages a human instead of quietly
delisting. (A stall nobody notices is down is a stall whose catalog
entry rots; see the Verdict Index issues in x402-loop-kits.)
"""

import argparse
import sys
import time
import urllib.request


def probe(base: str) -> bool:
    try:
        with urllib.request.urlopen(base.rstrip("/") + "/health", timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("--interval", type=float, default=300)
    ap.add_argument("--fail-streak", type=int, default=3)
    ap.add_argument("--once", action="store_true", help="probe once and exit")
    args = ap.parse_args()

    streak = 0
    while True:
        ok = probe(args.base_url)
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"{ts} {'OK' if ok else 'FAIL'} {args.base_url}", flush=True)
        if args.once:
            return 0 if ok else 1
        streak = 0 if ok else streak + 1
        if streak >= args.fail_streak:
            print(f"{ts} failure streak {streak} — exiting non-zero", flush=True)
            return 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
