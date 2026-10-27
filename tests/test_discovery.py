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
