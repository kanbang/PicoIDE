"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-20 18:11:17
LastEditors: zhai
LastEditTime: 2026-01-21 16:32:33
"""

from flow.block import BaseBlock, DebugBlock
from .mqtt_block import MqttPublishBlock, MqttSubscribeBlock
from .modbus_block import ModbusReadBlock, ModbusWriteBlock, ModbusSubscribeBlock

import os
import csv
import asyncio
from datetime import datetime
from flow.block import BaseBlock


class ConstantBlock(BaseBlock):
    """常量数据源"""

    NAME = "Constant"
    CATEGORY = "Demo/Source"

    def __init__(self):
        super().__init__()

        self.add_output("value")

        self.add_select_option(
            "type", items=["Number", "Integer", "Text"], default="Number"
        )
        self.add_number_option("number", default=1.0)
        self.add_integer_option("integer", default=1)
        self.add_text_input_option("text", "hello")

    def on_compute(self, execution_id=None):
        t = self.get_option("type")

        if t == "Number":
            value = self.get_option("number")
        elif t == "Integer":
            value = self.get_option("integer")
        else:
            value = self.get_option("text")

        self.set_interface("value", value)


class CsvRecorderBlock(BaseBlock):
    NAME = "CsvRecorder"
    CATEGORY = "Output"

    def __init__(self):
        super().__init__()
        # 定义配置项
        self.add_text_input_option("file_path", "data_log.csv")
        self.add_checkbox_option("auto_timestamp", True)

        # 定义输入接口
        self.add_input("data")  # 接收要保存的字典或字符串

        self._lock = asyncio.Lock()  # 确保写入顺序和文件安全
        self._initialized = False

    async def _init_file(self, fieldnames: list):
        """如果文件不存在，初始化并写入表头"""
        path = self.get_option("file_path")
        if not os.path.exists(path):
            # 使用 to_thread 避免同步 IO 阻塞 loop
            await asyncio.to_thread(self._write_header, path, fieldnames)
        self._initialized = True

    def _write_header(self, path, fieldnames):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    async def async_on_compute(self, execution_id: str = None):
        data = self.get_interface("data")
        if data is None:
            return

        path = self.get_option("file_path")

        # 统一格式为字典
        if not isinstance(data, dict):
            row = {"value": data}
        else:
            row = data.copy()

        # 自动添加时间戳
        if self.get_option("auto_timestamp"):
            row["_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        async with self._lock:
            # 延迟初始化表头（根据第一次收到的数据结构）
            if not self._initialized:
                await self._init_file(list(row.keys()))

            # 写入一行数据
            await asyncio.to_thread(self._append_row, path, row)

    def _append_row(self, path, row):
        """同步追加逻辑，跑在独立线程中"""
        with open(path, "a", newline="", encoding="utf-8") as f:
            # 注意：如果后续数据增加了新字段，DictWriter 会根据 extrasaction 处理
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writerow(row)


# IoT 业务类型的 Block 列表
IOT_BLOCKS = [
    DebugBlock,
    ConstantBlock,
    MqttPublishBlock,
    MqttSubscribeBlock,
    CsvRecorderBlock,
    ModbusReadBlock,
    ModbusWriteBlock,
    ModbusSubscribeBlock,
]

__all__ = ["MqttPublishBlock", "MqttSubscribeBlock", "IOT_BLOCKS"]
