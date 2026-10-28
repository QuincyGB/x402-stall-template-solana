"""Freshness guard for snapshot-consuming products.

The pattern (the Verdict Row fleet's, learned in production on
2026-10-27): any product that serves answers derived from a
periodically refreshed snapshot — a catalog diff, an alert feed, a
watchlist — must refuse to serve when the snapshot is older than
its refresh cadence. Serving stale data as if it were current is
worse than an error: buyers act on it. The fleet shipped this the
hard way — an index product initially had no guard at all, and the
defect only surfaced when a neighbouring claim was re-verified
against the live service.

The guard is deliberately tiny and framework-free. Wire it in two
places:

- a PAID route checks before answering; stale -> raise
  StaleSnapshotError, which the handler maps to 502 BEFORE any
  settlement or debit (an unsettled error is honest; a settled
  stale answer is a defect);
- a SUBSCRIPTION cycle checks before evaluating; stale -> skip
  the cycle entirely, debit nothing, log the skip.

    guard = FreshnessGuard(max_age_s=SNAPSHOT_TTL_S)

    # paid route
    try:
        guard.require_fresh(snapshot.fetched_at)
    except StaleSnapshotError:
        return JSONResponse({"error": "snapshot stale"}, status_code=502)

    # subscription cycle
    if not guard.is_fresh(snapshot.fetched_at):
        log("skipping cycle: snapshot stale")
        return
"""

from __future__ import annotations

import time


class StaleSnapshotError(Exception):
    """The snapshot a product would serve from is too old."""


class FreshnessGuard:
    """Refuse to serve from a snapshot older than max_age_s."""

    def __init__(self, max_age_s: float):
        if max_age_s <= 0:
            raise ValueError("max_age_s must be positive")
        self.max_age_s = float(max_age_s)

    def age_s(self, fetched_at: float, now: float | None = None) -> float:
        """Age of a snapshot taken at `fetched_at` (epoch seconds)."""
        return (time.time() if now is None else now) - fetched_at

    def is_fresh(self, fetched_at: float, now: float | None = None) -> bool:
        return self.age_s(fetched_at, now) <= self.max_age_s

    def require_fresh(self, fetched_at: float, now: float | None = None) -> float:
        """Return the snapshot's age, or raise StaleSnapshotError."""
        age = self.age_s(fetched_at, now)
        if age > self.max_age_s:
            raise StaleSnapshotError(
                f"snapshot is {age:.0f}s old (limit {self.max_age_s:.0f}s)"
            )
        return age
