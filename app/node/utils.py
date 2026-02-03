from typing import Optional
from flow.block import BaseBlock
from flow.runtime_bus import RuntimeEvent, RuntimeEventType


class SseLogger(BaseBlock):
    """Block for logging debug information."""

    NAME = "SSE Logger"
    CATEGORY = "工具"
    STREAMING = False

    def __init__(self):
        super().__init__()
        self.add_input("data")  # Input to trigger logging

    async def on_compute(self, execution_id: str = None):
        """Asynchronously logs input data and emits a debug event."""
        data = self.get_interface("data")
        log_msg = f"{data}"
        await self.event_bus.emit(
            RuntimeEvent(
                execution_id,
                RuntimeEventType.DEBUG,
                self.NAME,
                log_msg,
                payload=data,
            )
        )


class ConsoleLogger(BaseBlock):
    """
    控制台日志输出（调试用）

    功能：
    - 输出数据到控制台
    - 支持自定义前缀
    """

    NAME = "Console Logger"
    CATEGORY = "工具"

    def __init__(self):
        super().__init__()

        self.add_input("I-Any")
        self.add_text_input_option("前缀", default="LOG:")

    async def on_compute(self, execution_id: Optional[str] = None):
        """执行计算"""
        try:
            data = self.get_interface("I-Any")
            prefix = self.get_option("前缀")
            self._logger.info(f"{prefix} {data}")

        except Exception as e:
            self._log_error(e, "日志输出")
            raise
