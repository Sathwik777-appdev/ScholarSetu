"""Event Bus abstractions with NATS JetStream implementation and in-memory fallback."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Callable, Awaitable, List
from pydantic import BaseModel, Field

logger = logging.getLogger("scholarsetu.events")


class BaseEvent(BaseModel):
    event_id: str
    type: str
    occurred_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)


class EventBus:
    """Base EventBus interface."""

    async def publish(self, subject: str, event: BaseEvent) -> None:
        raise NotImplementedError

    async def subscribe(self, subject: str, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        raise NotImplementedError


class InMemoryEventBus(EventBus):
    """In-memory event bus with subscriber list for local dev and testing."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[BaseEvent], Awaitable[None]]]] = {}
        self.published_events: List[Dict[str, Any]] = []

    async def publish(self, subject: str, event: BaseEvent) -> None:
        self.published_events.append({"subject": subject, "event": event})
        logger.info(f"[InMemoryEventBus] Published {event.type} to {subject}")
        handlers = self._subscribers.get(subject, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error handling event {event.type} on {subject}: {e}")

    async def subscribe(self, subject: str, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        if subject not in self._subscribers:
            self._subscribers[subject] = []
        self._subscribers[subject].append(handler)
        logger.info(f"[InMemoryEventBus] Subscribed to {subject}")


class NATSEventBus(EventBus):
    """NATS JetStream event bus with automatic fallback to InMemoryEventBus."""

    def __init__(self, nats_url: str = "nats://localhost:4222"):
        self.nats_url = nats_url
        self._nc = None
        self._js = None
        self._fallback = InMemoryEventBus()
        self._connected = False

    async def connect(self) -> bool:
        try:
            import nats
            self._nc = await nats.connect(self.nats_url, connect_timeout=2)
            self._js = self._nc.jetstream()
            self._connected = True
            logger.info(f"Connected to NATS JetStream at {self.nats_url}")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to NATS ({e}). Falling back to InMemoryEventBus.")
            self._connected = False
            return False

    async def publish(self, subject: str, event: BaseEvent) -> None:
        if self._connected and self._js:
            try:
                data = json.dumps(event.model_dump()).encode()
                await self._js.publish(subject, data)
                return
            except Exception as e:
                logger.warning(f"NATS publish failed: {e}. Using fallback.")
        await self._fallback.publish(subject, event)

    async def subscribe(self, subject: str, handler: Callable[[BaseEvent], Awaitable[None]]) -> None:
        if self._connected and self._js:
            try:
                async def message_wrapper(msg):
                    try:
                        data = json.loads(msg.data.decode())
                        event = BaseEvent(**data)
                        await handler(event)
                        await msg.ack()
                    except Exception as err:
                        logger.error(f"Failed handling NATS message: {err}")
                await self._js.subscribe(subject, cb=message_wrapper)
                return
            except Exception as e:
                logger.warning(f"NATS subscribe failed: {e}. Using fallback.")
        await self._fallback.subscribe(subject, handler)


# Global singleton instance
global_event_bus = InMemoryEventBus()


def get_event_bus() -> EventBus:
    return global_event_bus
