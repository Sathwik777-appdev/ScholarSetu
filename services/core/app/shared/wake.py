"""Wake-on-request for a hosted demo whose database and backend VM sleep when idle (deploy/gcp/power-manager).

When the database cannot be reached, the API answers 503 with code WAKING and asks the power manager to start
everything. The power manager is private: the call carries this service's Google identity token. At most one
wake request is sent per minute per API instance. Without POWER_MANAGER_URL nothing is called."""

import asyncio
import logging
import time
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger("scholarsetu.wake")

_METADATA_TOKEN = ("http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
                   "?audience={audience}")
_MIN_INTERVAL_SECONDS = 60
_last_sent = 0.0
_task: Optional[asyncio.Task] = None


def _is_db_unreachable(exc: BaseException) -> bool:
    """A failure to reach the database (connection refused, socket missing, timeout), not a bad query."""
    from sqlalchemy.exc import DBAPIError, IntegrityError
    if isinstance(exc, (ConnectionRefusedError, ConnectionResetError)):  # raised by asyncpg before SQLAlchemy wraps
        return True
    # A stopped Cloud SQL instance has no socket: asyncpg raises FileNotFoundError for /cloudsql/.../.s.PGSQL.5432.
    # Only that socket counts; any other missing file is a real bug and stays a 500.
    if isinstance(exc, FileNotFoundError):
        path = str(getattr(exc, "filename", "") or "")
        if "/cloudsql/" in path or ".s.PGSQL" in path:
            return True
        import traceback
        frames = {(f.name, f.filename) for f in traceback.extract_tb(exc.__traceback__)}
        return any(name == "create_unix_connection" or "asyncpg" in filename for name, filename in frames)
    if isinstance(exc, DBAPIError) and not isinstance(exc, IntegrityError):
        if exc.connection_invalidated or isinstance(exc.orig, (ConnectionError, TimeoutError, OSError)):
            return True
        text = str(exc.orig or exc).lower()
        return any(s in text for s in ("connect", "connection", "no such file", "timeout", "the database system"))
    return False


async def _send() -> None:
    url = settings.POWER_MANAGER_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token = (await client.get(_METADATA_TOKEN.format(audience=url),
                                      headers={"Metadata-Flavor": "Google"})).text
            res = await client.post(f"{url}/wake", headers={"Authorization": f"Bearer {token}"})
        logger.warning("database unreachable: wake requested (power manager answered HTTP %s)", res.status_code)
    except Exception as exc:  # noqa: BLE001 - best effort; the next request tries again after the interval
        logger.warning("database unreachable: wake request failed (%s)", type(exc).__name__)


def request_wake() -> bool:
    """Ask the power manager to wake the backend, at most once a minute. Returns whether a request was sent."""
    global _last_sent, _task
    if not settings.POWER_MANAGER_URL:
        return False
    now = time.monotonic()
    if now - _last_sent < _MIN_INTERVAL_SECONDS:
        return False
    _last_sent = now
    _task = asyncio.get_running_loop().create_task(_send())
    return True
