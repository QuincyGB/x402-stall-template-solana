"""The paywall pattern: x402 SDK middleware, built ONCE.

Two production lessons are encoded here:

1. Build the middleware once at import time. Constructing it runs
   the SDK's initialize(), which synchronously fetches the
   facilitator's /supported document — per-request construction
   adds a full external round-trip to EVERY call, /health included.
2. RouteConfig descriptions feed the Bazaar discovery extension;
   the catalog enforces <500 chars (checks/listsmith-ci.md).
"""

from __future__ import annotations

from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption, RouteConfig
from x402.http.middleware import fastapi_payment_middleware
from x402.mechanisms.svm.exact.server import ExactSvmScheme
from x402.server import x402ResourceServer

from .config import PRICE_UNITS, Settings, units_to_price
from .discovery import ROUTES, route_extension


def build_payment_middleware(settings: Settings):
    facilitator = HTTPFacilitatorClient(
        FacilitatorConfig(url=settings.facilitator_url)
    )
    resource_server = x402ResourceServer(facilitator)
    resource_server.register(settings.network, ExactSvmScheme())

    routes: dict[str, RouteConfig] = {}
    for path, units in PRICE_UNITS.items():
        routes[f"POST {path}"] = RouteConfig(
            accepts=PaymentOption(
                scheme="exact",
                pay_to=settings.pay_to,
                # The SDK wants a "$x.xx" string here: an int is read
                # as whole dollars and your $0.01 route silently
                # becomes a $10,000 route. (Fleet lesson, pinned by
                # tests/test_paywall.py's exact-amount assertion.)
                price=units_to_price(units),
                network=settings.network,
            ),
            description=ROUTES[path]["description"],
            mime_type="application/json",
            service_name=settings.service_name,  # <=32 chars, forwarded to Bazaar
            tags=ROUTES[path]["tags"],
            # Without this, the 402 carries no discovery extension
            # and the catalog indexes a hollow listing.
            extensions={"bazaar": route_extension(path)},
        )
    return fastapi_payment_middleware(routes, resource_server)
