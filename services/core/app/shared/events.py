"""Event publishing: transactional outbox → NATS JetStream.

Services never publish directly. They call `emit()` inside their DB transaction; the outbox
publisher sends committed rows to JetStream (with the message id as the dedupe key) and marks
them published. If NATS is down, rows wait and are retried.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ids import new_id

logger = logging.getLogger("scholarsetu.events")

STREAM_NAME = "SCHOLARSETU"
STREAM_SUBJECTS = ["application.>", "verification.>", "attestation.>", "payment.>", "deficiency.>",
                   "pathway.>", "sla.>", "notification.>", "consent.>", "adapter.>", "dbt.>"]


class BaseEvent(BaseModel):
    event_id: str
    type: str
    occurred_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


async def emit(db: AsyncSession, subject: str, event_type: str, payload: dict[str, Any],
               correlation_id: str = "", message_id: Optional[str] = None) -> str:
    """Queue an event in the outbox as part of the caller's transaction. Returns the message id."""
    from app.ledger.models import OutboxMessage
    message_id = message_id or new_id()
    event = BaseEvent(event_id=message_id, type=event_type, correlation_id=correlation_id, payload=payload)
    db.add(OutboxMessage(message_id=message_id, subject=subject, event_type=event_type,
                         payload=event.model_dump(mode="json")))
    return message_id


class EventBus:
    async def publish(self, subject: str, event: BaseEvent) -> None:
        raise NotImplementedError

    async def subscribe(self, subject: str, durable: str, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        raise NotImplementedError


class NATSEventBus(EventBus):
    def __init__(self, url: str):
        self.url = url
        self._nc = None
        self._js = None

    @property
    def connected(self) -> bool:
        return self._nc is not None and self._nc.is_connected

    async def connect(self) -> None:
        import nats
        from nats.js.api import StreamConfig
        self._nc = await nats.connect(self.url, connect_timeout=3, max_reconnect_attempts=-1)
        self._js = self._nc.jetstream()
        try:
            await self._js.add_stream(StreamConfig(name=STREAM_NAME, subjects=STREAM_SUBJECTS))
        except Exception:
            await self._js.update_stream(StreamConfig(name=STREAM_NAME, subjects=STREAM_SUBJECTS))

    async def close(self) -> None:
        if self._nc is not None:
            await self._nc.drain()
            self._nc = None

    async def publish(self, subject: str, event: BaseEvent) -> None:
        if not self.connected:
            raise ConnectionError("NATS is not connected")
        await self._js.publish(subject, json.dumps(event.model_dump(mode="json")).encode(),
                               headers={"Nats-Msg-Id": event.event_id})

    async def subscribe(self, subject: str, durable: str, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        async def _on_message(msg):
            try:
                await handler(BaseEvent(**json.loads(msg.data)))
                await msg.ack()
            except Exception:
                logger.exception("handler failed for %s; message will be redelivered", msg.subject)
                await msg.nak(delay=5)
        await self._js.subscribe(subject, durable=durable, cb=_on_message, manual_ack=True)


_bus: Optional[EventBus] = None


def get_event_bus() -> Optional[EventBus]:
    return _bus


def set_event_bus(bus: Optional[EventBus]) -> None:
    global _bus
    _bus = bus


async def publish_pending(session_factory, bus: EventBus, batch: int = 100) -> int:
    """Publish committed outbox rows in order. Returns how many were published."""
    from app.ledger.models import OutboxMessage
    published = 0
    async with session_factory() as db:
        rows = (await db.execute(
            select(OutboxMessage).where(OutboxMessage.published_at.is_(None))
            .order_by(OutboxMessage.id).limit(batch).with_for_update(skip_locked=True)
        )).scalars().all()
        for row in rows:
            try:
                await bus.publish(row.subject, BaseEvent(**row.payload))
            except Exception as exc:  # stop at the first failure to keep ordering
                row.attempts += 1
                row.last_error = f"{type(exc).__name__}: {exc}"[:500]
                break
            row.published_at = datetime.now(timezone.utc)
            published += 1
        await db.commit()
    return published


async def run_outbox_publisher(session_factory, bus: EventBus, interval: float = 0.5,
                               stop: Optional[asyncio.Event] = None) -> None:
    stop = stop or asyncio.Event()
    while not stop.is_set():
        try:
            if await publish_pending(session_factory, bus) == 0:
                await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
        except Exception:
            logger.exception("outbox publisher iteration failed")
            await asyncio.sleep(interval)
