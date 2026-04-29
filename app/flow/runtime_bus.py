"""
Flow runtime event bus.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from itertools import count
import asyncio
import time
from typing import Any, AsyncIterator, Dict, Optional

from utils.singleton import singleton


class RuntimeEventType(str, Enum):
    LOG = "log"
    DEBUG = "debug"
    INFO = "info"
    ERROR = "error"
    DATA = "data"
    FILE = "file"
    STATUS = "status"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_STOPPED = "execution_stopped"


TERMINAL_EVENT_TYPES = {
    RuntimeEventType.EXECUTION_COMPLETED,
    RuntimeEventType.EXECUTION_FAILED,
    RuntimeEventType.EXECUTION_STOPPED,
}


@dataclass(frozen=True)
class RuntimeEvent:
    execution_id: str
    type: RuntimeEventType
    source: str
    message: str
    data: Optional[Any] = None
    ts: float = field(default_factory=time.time)


@dataclass
class _ExecutionChannel:
    history: list[RuntimeEvent] = field(default_factory=list)
    subscribers: Dict[int, asyncio.Queue] = field(default_factory=dict)
    terminal: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


@singleton
class RuntimeEventBus:
    """Per-execution event log plus live fan-out for SSE subscribers."""

    MAX_HISTORY_PER_EXECUTION = 1000

    def __init__(self):
        self._channels: Dict[str, _ExecutionChannel] = defaultdict(_ExecutionChannel)
        self._subscriber_ids = count(1)
        self._close_signal = object()

    async def emit(self, event: RuntimeEvent):
        """Append to execution history and fan out to all live subscribers."""
        channel = self._channels[event.execution_id]

        async with channel.lock:
            channel.history.append(event)
            if len(channel.history) > self.MAX_HISTORY_PER_EXECUTION:
                channel.history = channel.history[-self.MAX_HISTORY_PER_EXECUTION :]

            if event.type in TERMINAL_EVENT_TYPES:
                channel.terminal = True

            subscribers = list(channel.subscribers.values())

        for queue in subscribers:
            await queue.put(event)

    async def subscribe(self, execution_id: str) -> AsyncIterator[RuntimeEvent]:
        """
        Subscribe to one execution stream.

        New subscribers first receive cached history in order. If the execution is
        already terminal, the replay ends immediately. Otherwise the subscriber is
        registered for subsequent live events.
        """
        channel = self._channels[execution_id]
        subscriber_id = next(self._subscriber_ids)
        queue: asyncio.Queue = asyncio.Queue()

        async with channel.lock:
            history = list(channel.history)
            terminal = channel.terminal
            if not terminal:
                channel.subscribers[subscriber_id] = queue

        try:
            for event in history:
                yield event

            if terminal:
                return

            while True:
                event = await queue.get()
                if event is self._close_signal:
                    break
                yield event
                if event.type in TERMINAL_EVENT_TYPES:
                    break
        finally:
            async with channel.lock:
                channel.subscribers.pop(subscriber_id, None)

    def cleanup(self, execution_id: str):
        """Drop cached history for one execution and close all live subscribers."""
        channel = self._channels.pop(execution_id, None)
        if channel is None:
            return

        for queue in channel.subscribers.values():
            queue.put_nowait(self._close_signal)
