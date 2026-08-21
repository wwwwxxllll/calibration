"""In-process pub/sub broker feeding the WebUI Server-Sent Events stream."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator


class Broker:
    """Fan out small "something changed" signals to every SSE subscriber.

    Each subscriber holds a bounded queue; a slow client that stops draining is
    dropped rather than allowed to block the event loop or grow unboundedly.
    ``None`` is yielded periodically as a keep-alive sentinel so the SSE stream
    can emit a comment frame and keep intermediary proxies from timing out.
    """

    def __init__(self, *, heartbeat_seconds: float = 15.0, maxsize: int = 100) -> None:
        self._heartbeat = heartbeat_seconds
        self._maxsize = maxsize
        self._subscribers: set[asyncio.Queue] = set()

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    async def publish(self, event: dict[str, Any]) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop the slow subscriber; its EventSource reconnects and
                # re-syncs from the REST endpoints.
                self._subscribers.discard(queue)

    async def subscribe(self) -> AsyncIterator[dict[str, Any] | None]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._maxsize)
        self._subscribers.add(queue)
        try:
            while True:
                try:
                    yield await asyncio.wait_for(queue.get(), timeout=self._heartbeat)
                except asyncio.TimeoutError:
                    yield None
        finally:
            self._subscribers.discard(queue)


__all__ = ["Broker"]
