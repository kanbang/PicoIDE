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
from pathlib import Path
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

    async def on_compute(self, execution_id=None):
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
        self._fieldnames = None

    async def on_compute(self, execution_id: str = None):
        data = self.get_interface("data")
        if data is None:
            return

        filename = self.get_option("file_path")

        # 统一格式为字典
        if not isinstance(data, dict):
            row = {"value": data}
        else:
            row = data.copy()

        # 自动添加时间戳
        if self.get_option("auto_timestamp"):
            row["_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # 初始化表头（如果首次）
        if self._fieldnames is None:
            self._fieldnames = list(row.keys())

        # 定义写入函数（处理写或追加，包括header）
        def write_csv(full_path: Path, mode: str):
            if mode == "w":
                with open(full_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self._fieldnames)
                    writer.writeheader()
                    writer.writerow(row)
            else:  # "a"
                with open(full_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self._fieldnames)
                    writer.writerow(row)

        # 使用基类方法（非唯一，追加模式）
        self._write_file(
            filename=filename,
            write_func=write_csv,
            execution_id=execution_id,
            description="CSV数据文件",
            unique=False,
            mode="a",
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
