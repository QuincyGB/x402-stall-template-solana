"""Example stall: word-count, paid per call or by prepaid pack.

Wiring order matters and mirrors the fleet:

1. The pack middleware runs FIRST: a call presenting a pack id is
   paid from the pack, so it skips the paywall and the handler
   debits/validates against the store.
2. Everything else goes through the x402 payment middleware built
   once in app/paywall.py.
3. Handlers never see unpaid calls (except pack calls, which they
   validate themselves) and never charge for failures: raised
   errors become 502s, and the middleware settles only on success.
"""

from __future__ import annotations

import hashlib
import math
import os
import re

# Scrub bracketed-IPv6 no_proxy entries before any x402 SDK client is
# constructed: the SDK's httpx-based facilitator client parses that
# env list as URLs and dies on "[::1]" entries ("Invalid port:
# ':1]'"), turning every unpaid call into a 500 instead of a 402.
# Learned in production by the Verdict Row fleet; keep this above
# every other import that could build a client.
for _var in ("no_proxy", "NO_PROXY"):
    _val = os.environ.get(_var)
    if _val:
        _kept = [e for e in _val.split(",") if "[" not in e and "]" not in e]
        os.environ[_var] = ",".join(_kept)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .config import PACK_CREDITS, PRICE_UNITS, settings
from .discovery import manifest
from .packs import PackError, PackStore
from .paywall import build_payment_middleware

app = FastAPI(title=settings.service_name, version="0.1.0")

_store = PackStore(settings.db_path)
_payment_middleware = build_payment_middleware(settings)

PACK_HEADER = "x-pack"


@app.middleware("http")
async def pack_then_paywall(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/v1/word-count":
        if (request.headers.get(PACK_HEADER) or "").strip():
            return await call_next(request)
    return await _payment_middleware(request, call_next)


def _payment_key(request: Request) -> str | None:
    """Idempotency identity for a settled payment (simplified from
    the fleet's: on Solana the payment header carries the buyer's
    partially-signed transaction; hash whichever payment header
    the middleware verified)."""
    for header in ("payment-signature", "x-payment"):
        raw = request.headers.get(header)
        if raw:
            return "payment-header:" + hashlib.sha256(raw.encode()).hexdigest()
    return None


class WordCountRequest(BaseModel):
    text: str = Field(description="The text to measure")


class PackBalanceRequest(BaseModel):
    pack_id: str = Field(description="Pack id returned by POST /v1/pack")


@app.post("/v1/word-count")
async def word_count(req: WordCountRequest, request: Request):
    pack_id = (request.headers.get(PACK_HEADER) or "").strip()
    if pack_id:
        try:
            _store.debit(pack_id, settings.service_name)
        except PackError as e:
            return JSONResponse(
                {"error": e.message, "code": e.code, "pack_id": pack_id},
                status_code=e.http_status,
            )
    words = re.findall(r"\S+", req.text)
    unique = {w.strip(".,!?;:\"'()[]").lower() for w in words}
    sentences = len(re.findall(r"[.!?]+", req.text))
    if words and sentences == 0:
        sentences = 1
    return {
        "words": len(words),
        "unique_words": len(unique),
        "sentences": sentences,
        "characters": len(req.text),
        "reading_seconds": math.ceil(len(words) / 2.5) if words else 0,
    }


@app.post("/v1/pack")
async def buy_pack(request: Request):
    """Runs only after the middleware verified the $1.00 payment.
    Minting is idempotent on the payment identity."""
    return _store.mint(settings.service_name, PACK_CREDITS, _payment_key(request))


@app.post("/v1/pack/balance")
async def pack_balance(req: PackBalanceRequest):
    try:
        return _store.balance(req.pack_id, settings.service_name)
    except PackError as e:
        return JSONResponse(
            {"error": e.message, "code": e.code, "pack_id": req.pack_id},
            status_code=e.http_status,
        )


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": settings.service_name,
        "routes": len(PRICE_UNITS),
        "storage": {"db_path": settings.db_path},
    }


@app.get("/.well-known/x402")
async def x402_manifest(request: Request):
    base = f"{request.url.scheme}://{request.url.netloc}"
    return manifest(base, settings.pay_to, settings.network)


@app.get("/", response_class=HTMLResponse)
async def landing():
    return (
        f"<h1>{settings.service_name}</h1>"
        "<p>An x402 stall built from the stall-in-a-box template. "
        "See /.well-known/x402 for the manifest and /health for status.</p>"
    )
