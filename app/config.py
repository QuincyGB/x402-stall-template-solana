"""Template configuration: env-driven, Solana mainnet, one payTo.

Prices are integer USDC base units (1 USDC = 1_000_000), the same
convention the x402 challenges carry — never floats near money.
"""

from __future__ import annotations

import os

USDC_ASSET = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC mint, Solana mainnet

# Route prices in USDC base units.
PRICE_UNITS: dict[str, int] = {
    "/v1/word-count": 10_000,       # $0.01
    "/v1/pack": 1_000_000,          # $1.00 — 250 prepaid credits
}

PACK_CREDITS = 250
PACK_EXPIRY_DAYS = 90


class Settings:
    def __init__(self) -> None:
        self.service_name = os.environ.get("STALL_NAME", "my-stall")
        self.pay_to = os.environ.get("X402_PAY_TO", "")
        self.network = os.environ.get(
            "X402_NETWORK", "solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp"
        )
        self.facilitator_url = os.environ.get(
            "X402_FACILITATOR_URL", "https://facilitator.ultravioletadao.xyz/"
        )
        self.db_path = os.environ.get("STALL_DB_PATH", "stall.db")


settings = Settings()


def units_to_price(units: int) -> str:
    return f"${units / 1_000_000:.6f}".rstrip("0").rstrip(".")
