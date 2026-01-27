from enum import Enum
from dataclasses import dataclass
import time
from typing import Any, Optional

import asyncio
from collections import defaultdict
from typing import Dict, AsyncIterator
from utils.singleton import singleton

class RuntimeEventType(str, Enum):
    LOG = "log"
    DEBUG = "debug"
    INFO = "info"
    ERROR = "error"
    DATA = "data" # 节点输出数据
    STATUS = "status" # 引擎/节点状态
 
@dataclass
class RuntimeEvent:
    execution_id: str
    type: RuntimeEventType
    source: str # engine / block_id
    message: str
    payload: Optional[Any] = None
    ts: float = time.time()

@singleton
class RuntimeEventBus:
    def __init__(self):
        # execution_id → Queue
        self._queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def emit(self, event: RuntimeEvent):
        await self._queues[event.execution_id].put(event)

    async def subscribe(self, execution_id: str) -> AsyncIterator[RuntimeEvent]:
        queue = self._queues[execution_id]
        while True:
            event = await queue.get()
            yield event
