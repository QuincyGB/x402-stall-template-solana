"""Discovery rules from checks/listsmith-ci.md, as tests."""

import json

from app.config import PRICE_UNITS
from app.discovery import ROUTES, manifest


def test_every_route_described_and_priced():
    assert set(ROUTES) == set(PRICE_UNITS)


def test_descriptions_under_catalog_limit_with_use_when():
    for path, r in ROUTES.items():
        assert len(r["description"]) < 500, path
        assert "Use this when" in r["description"], path


def test_output_examples_fit_the_sample_ceiling():
    for path, r in ROUTES.items():
        size = len(json.dumps(r["output_example"], separators=(",", ":")).encode())
        assert size <= 1450, f"{path}: {size}"


def test_manifest_accepts_match_prices():
    m = manifest("https://stall.example", "0xPayTo", "eip155:8453")
    assert m["x402Version"] == 2
    by_path = {r["resource"].replace("https://stall.example", ""): r for r in m["resources"]}
    for path, units in PRICE_UNITS.items():
        acc = by_path[path]["accepts"][0]
        assert acc["amount"] == str(units)
        assert acc["payTo"] == "0xPayTo"
        assert acc["network"] == "eip155:8453"


def test_descriptions_carry_the_payable_clause():
    from app.discovery import RAILS, payable_clause

    for path, r in ROUTES.items():
        assert r["description"].endswith(payable_clause(RAILS)), path


def test_payable_clause_wording_is_the_fleets():
    from app.discovery import payable_clause

    assert payable_clause("base") == "Payable in USDC on Base."
    assert payable_clause("solana") == "Payable in USDC on Solana."
    assert payable_clause("base+solana") == "Payable in USDC on Base or Solana."


def test_with_payable_clause_idempotent_and_limit_checked():
    import pytest

    from app.discovery import with_payable_clause

    once = with_payable_clause("Does a thing. Use this when testing.", "base+solana")
    assert once.endswith("Payable in USDC on Base or Solana.")
    assert with_payable_clause(once, "base+solana") == once
    with pytest.raises(ValueError):
        with_payable_clause("x" * 490 + " Use this when.", "base")
