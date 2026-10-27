"""Paywall contract: unpaid calls get a 402 at the exact price.

NOTE: booting the app builds the payment middleware, which fetches
the facilitator's /supported document — this test needs network,
like the fleet's own suites. Set X402_PAY_TO to any Solana address.
"""

import base64
import json
import os

# X402_PAY_TO / STALL_DB_PATH are set in tests/conftest.py, before
# any app import can read settings.
from fastapi.testclient import TestClient  # noqa: E402

import app.main as main  # noqa: E402


def test_health_is_free():
    with TestClient(main.app) as client:
        r = client.get("/health")
        assert r.status_code == 200 and r.json()["ok"] is True


def test_unpaid_word_count_is_402_at_exact_price():
    with TestClient(main.app) as client:
        r = client.post("/v1/word-count", json={"text": "hello stall"})
        assert r.status_code == 402
        challenge = json.loads(base64.b64decode(r.headers["payment-required"]))
        acc = challenge["accepts"][0]
        assert acc["amount"] == "10000"
        assert acc["network"] == "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
        assert acc["asset"] == "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC mint
        assert acc["payTo"] == os.environ["X402_PAY_TO"]
        # The live 402 must carry the Bazaar discovery extension —
        # without it the catalog indexes a hollow listing.
        bazaar = challenge["extensions"]["bazaar"]
        assert bazaar["info"]["input"]["body"] == {"text": "hello stall"}
        assert "output" in bazaar["schema"]["properties"]


def test_manifest_lists_routes():
    with TestClient(main.app) as client:
        body = client.get("/.well-known/x402").json()
        urls = [r["resource"] for r in body["resources"]]
        assert any(u.endswith("/v1/word-count") for u in urls)
        assert any(u.endswith("/v1/pack") for u in urls)
