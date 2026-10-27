"""Discovery generator: one route table -> manifest + Bazaar entries.

Standing rules (test-pinned, straight from the fleet):
- every description is < 500 chars (the catalog limit) and carries a
  "Use this when" sentence;
- every route's output schema is a FULL typed object schema — never
  the hollow {"type": "object"} shape inspectors grade down;
- output examples stay well under the ~1.5 KB sample ceiling some
  indexers enforce by silently dropping larger samples.
"""

from __future__ import annotations

import json

from .config import PRICE_UNITS, USDC_ASSET

_S = {"type": "string"}
_I = {"type": "integer"}
_B = {"type": "boolean"}


def _obj(props: dict, required: list[str]) -> dict:
    return {"type": "object", "properties": props, "required": required}


ROUTES: dict[str, dict] = {
    "/v1/word-count": {
        "description": (
            "Word count and reading time for a text payload: totals, "
            "unique words, sentences, and estimated seconds to read "
            "aloud. Deterministic, no external calls. Use this when an "
            "agent needs cheap text metrics before summarizing, "
            "quoting, or chunking a document."
        ),
        "tags": ["text", "metrics", "x402"],
        "input_schema": _obj({"text": _S}, ["text"]),
        "input_example": {"text": "hello stall"},
        "output_schema": _obj(
            {
                "words": _I,
                "unique_words": _I,
                "sentences": _I,
                "characters": _I,
                "reading_seconds": _I,
            },
            ["words", "unique_words", "sentences", "characters", "reading_seconds"],
        ),
        "output_example": {
            "words": 2, "unique_words": 2, "sentences": 1,
            "characters": 11, "reading_seconds": 1,
        },
    },
    "/v1/pack": {
        "description": (
            "Buy a prepaid pack of 250 word-count credits ($1.00, 90 "
            "days) bound to this stall: calls presenting the pack id "
            "in the X-Pack header spend a credit instead of paying "
            "per call. Exhausted packs return 402, expired 410, and "
            "never fall back to per-call billing. Use this when a "
            "loop calls word-count on a schedule and wants one "
            "budget, not a payment per call."
        ),
        "tags": ["prepaid", "credits", "x402"],
        "input_schema": _obj({}, []),
        "input_example": {},
        "output_schema": _obj(
            {
                "pack_id": _S, "purpose": _S, "credits_total": _I,
                "credits_left": _I, "created_at": _S, "expires_at": _S,
                "expired": _B,
            },
            ["pack_id", "credits_left", "expires_at"],
        ),
        "output_example": {
            "pack_id": "pack_0123456789abcdef0123456789abcdef",
            "purpose": "my-stall", "credits_total": 250, "credits_left": 250,
            "created_at": "2026-01-01T00:00:00Z",
            "expires_at": "2026-04-01T00:00:00Z", "expired": False,
        },
    },
}

for _path, _r in ROUTES.items():
    assert len(_r["description"]) < 500, f"{_path} description too long"
    assert "Use this when" in _r["description"], _path
    _size = len(json.dumps(_r["output_example"], separators=(",", ":")).encode())
    assert _size <= 1450, f"{_path} output example too large: {_size}"


def route_extension(path: str) -> dict:
    """The Bazaar extension VALUE for one route (mounted under the
    "bazaar" key both in RouteConfig extensions — which puts it in
    the live 402 — and in the manifest)."""
    r = ROUTES[path]
    return {
        "info": {
            "input": {
                "type": "http", "method": "POST",
                "bodyType": "json",
                "body": r["input_example"],
            },
            "output": {"type": "json", "example": r["output_example"]},
        },
        "schema": {
            "type": "object",
            "properties": {
                "input": r["input_schema"],
                "output": r["output_schema"],
            },
            "required": ["input", "output"],
        },
    }


def manifest(base_url: str, pay_to: str, network: str) -> dict:
    resources = []
    for path, units in PRICE_UNITS.items():
        resources.append(
            {
                "resource": f"{base_url}{path}",
                "method": "POST",
                "accepts": [
                    {
                        "scheme": "exact",
                        "network": network,
                        "amount": str(units),
                        "asset": USDC_ASSET,
                        "payTo": pay_to,
                    }
                ],
                "extensions": {"bazaar": route_extension(path)},
            }
        )
    return {"x402Version": 2, "resources": resources}
