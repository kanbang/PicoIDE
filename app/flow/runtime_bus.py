from enum import Enum
from dataclasses import dataclass, field
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
    DATA = "data"  # 节点输出数据
    FILE = "file"  # 节点生成文件
    STATUS = "status"  # 引擎/节点状态
    # 引擎状态
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_STOPPED = "execution_stopped"  # 用户手动停止

@dataclass(frozen=True)  # 添加 frozen=True 使事件不可变，增强安全性
class RuntimeEvent:
    execution_id: str
    type: RuntimeEventType
    source: str  # engine / block type
    message: str
    payload: Optional[Any] = None
    ts: float = field(default_factory=time.time)  # 使用 default_factory 确保每次实例化时生成新时间戳

@singleton
class RuntimeEventBus:
    def __init__(self):
        # execution_id → 共享队列（所有订阅者共享同一个队列）
        self._queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    async def emit(self, event: RuntimeEvent):
        """发送事件到指定execution_id的队列"""
        await self._queues[event.execution_id].put(event)

    async def subscribe(self, execution_id: str) -> AsyncIterator[RuntimeEvent]:
        """订阅指定execution_id的事件（支持多个订阅者）"""
        queue = self._queues[execution_id]

        while True:
            event = await queue.get()
            yield event

    def cleanup(self, execution_id: str):
        """清理指定execution_id的队列（当所有订阅者断开时调用）"""
        if execution_id in self._queues:
            # 标记队列为已清理
            queue = self._queues[execution_id]
            # 创建一个新队列，后续的事件不会被旧订阅者接收
            self._queues[execution_id] = asyncio.Queue()
            # 发送结束事件给旧订阅者
            asyncio.create_task(self._send_end_event(queue))

    async def _send_end_event(self, old_queue: asyncio.Queue):
        """发送结束事件给旧队列的等待者"""
        try:
            await asyncio.wait_for(old_queue.put(RuntimeEvent(
                execution_id="",
                type=RuntimeEventType.STATUS,
                source="event_bus",
                message="Connection closed"
            )), timeout=1.0)
        except asyncio.TimeoutError:
            pass