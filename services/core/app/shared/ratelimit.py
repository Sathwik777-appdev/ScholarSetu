"""Per-client limits on the unauthenticated login and registration endpoints, on top of the per-phone limits.

Per-phone limits stop guessing one account's code; these stop one client from spraying requests across many
phone numbers (SMS cost, enumeration). The client is the last X-Forwarded-For entry, the address Cloud Run's
front end saw (earlier entries are whatever the client claimed). Counts are kept in memory per API instance,
so the effective limit is per instance; that bounds abuse without a shared store. 429 with Retry-After."""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.config import settings

WINDOW_SECONDS = 600
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    if hops:
        return hops[-1]
    return request.client.host if request.client else "unknown"


def _check(bucket: str, limit: int, request: Request) -> None:
    now = time.monotonic()
    hits = _hits[(bucket, client_key(request))]
    while hits and now - hits[0] > WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= limit:
        retry = int(WINDOW_SECONDS - (now - hits[0])) + 1
        raise HTTPException(status_code=429, headers={"Retry-After": str(retry)},
                            detail="Too many requests from this connection. Try again in a few minutes.")
    hits.append(now)


async def limit_code_requests(request: Request) -> None:
    """Requests that send an SMS (login code, registration code)."""
    _check("send", settings.IP_CODE_REQUESTS_PER_10_MIN, request)


async def limit_code_checks(request: Request) -> None:
    """Requests that check a code."""
    _check("check", settings.IP_CODE_CHECKS_PER_10_MIN, request)


def reset() -> None:
    _hits.clear()
