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
        self._initialized = False

    async def _init_file(self, file_path: str, fieldnames: list):
        """如果文件不存在，初始化并写入表头"""
        if not os.path.exists(file_path):
            # 使用 to_thread 避免同步 IO 阻塞 loop
            await asyncio.to_thread(self._write_header, file_path, fieldnames)
        self._initialized = True

    def _write_header(self, file_path, fieldnames):
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    async def async_on_compute(self, execution_id: str = None):
        data = self.get_interface("data")
        if data is None:
            return

        file_path = self.get_option("file_path")

        # 统一格式为字典
        if not isinstance(data,  dict):
            row = {"value": data}
        else:
            row = data.copy()

        # 自动添加时间戳
        if self.get_option("auto_timestamp"):
            row["_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        if not self._initialized:
            await self._init_file(file_path, list(row.keys()))

        # 使用通用文件写入方法
        def write_csv(full_path):
            with open(full_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                writer.writerow(row)

        self._write_file(
            filename=file_path,
            write_func=write_csv,
            execution_id=execution_id,
            description="CSV数据文件",
        )



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
