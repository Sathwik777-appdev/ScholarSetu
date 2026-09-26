"""HTTP access to government data sources (the mock cluster in the prototype)."""

import hashlib
import json
from typing import Any, Optional

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings


class SourceUnavailable(Exception):
    """The source could not be reached or answered with a server error."""


class SourceClient:
    """Thin JSON client with a short timeout and bounded retries on transport errors and 5xx."""

    def __init__(self, base_url: str, transport: Optional[httpx.AsyncBaseTransport] = None,
                 timeout_seconds: float = 3.0, attempts: int = 2):
        self._client = httpx.AsyncClient(base_url=base_url, transport=transport, timeout=timeout_seconds)
        self._attempts = attempts

    async def aclose(self) -> None:
        await self._client.aclose()

    async def request_bytes(self, method: str, path: str, **kwargs) -> Optional[bytes]:
        """Like request(), for binary downloads."""
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TransportError as exc:
            raise SourceUnavailable(f"{method} {path}: {type(exc).__name__}") from exc
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise SourceUnavailable(f"{method} {path}: HTTP {response.status_code}")
        return response.content

    async def request(self, method: str, path: str, **kwargs) -> Optional[dict[str, Any]]:
        """Return the JSON body, None for 404 (no record), or raise SourceUnavailable."""
        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(self._attempts),
                wait=wait_exponential(multiplier=0.1, max=0.5),
                retry=retry_if_exception_type((httpx.TransportError, _ServerError)),
                reraise=True,
            ):
                with attempt:
                    response = await self._client.request(method, path, **kwargs)
                    if response.status_code >= 500:
                        raise _ServerError(response.status_code)
        except (httpx.TransportError, _ServerError) as exc:
            raise SourceUnavailable(f"{method} {path}: {type(exc).__name__}") from exc
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise SourceUnavailable(f"{method} {path}: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise SourceUnavailable(f"{method} {path}: invalid JSON") from exc


class _ServerError(Exception):
    pass


def evidence_hash(body: dict[str, Any]) -> str:
    """Hash of the source's response, so an attestation can point at exactly what was seen."""
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


async def get_source_client():
    """FastAPI dependency; tests override it with a client on an httpx.MockTransport."""
    client = SourceClient(settings.MOCK_SERVICE_URL)
    try:
        yield client
    finally:
        await client.aclose()
