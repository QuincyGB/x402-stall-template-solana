"""Freshness-guard pattern: fresh serves, stale refuses, and the two
wiring rules (paid route -> error before debit; subscription cycle
-> skip with no debit)."""

import pytest

from app.freshness import FreshnessGuard, StaleSnapshotError

NOW = 1_800_000_000.0


def test_fresh_snapshot_passes():
    guard = FreshnessGuard(max_age_s=3600)
    assert guard.is_fresh(NOW - 600, now=NOW)
    assert guard.require_fresh(NOW - 600, now=NOW) == 600


def test_boundary_is_fresh():
    guard = FreshnessGuard(max_age_s=3600)
    assert guard.is_fresh(NOW - 3600, now=NOW)


def test_stale_snapshot_refused():
    guard = FreshnessGuard(max_age_s=3600)
    assert not guard.is_fresh(NOW - 3601, now=NOW)
    with pytest.raises(StaleSnapshotError):
        guard.require_fresh(NOW - 7200, now=NOW)


def test_subscription_skip_pattern_debits_nothing():
    # The subscription wiring rule, modelled: a stale cycle is
    # skipped before any evaluation or debit can happen.
    guard = FreshnessGuard(max_age_s=3600)
    debits = []

    def cycle(fetched_at):
        if not guard.is_fresh(fetched_at, now=NOW):
            return "skipped"
        debits.append(1)
        return "evaluated"

    assert cycle(NOW - 7200) == "skipped"
    assert debits == []
    assert cycle(NOW - 60) == "evaluated"
    assert debits == [1]


def test_nonpositive_limit_rejected():
    with pytest.raises(ValueError):
        FreshnessGuard(max_age_s=0)
