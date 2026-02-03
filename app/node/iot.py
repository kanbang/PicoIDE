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
        

# IoT 业务类型的 Block 列表
IOT_BLOCKS = [
    DebugBlock,
    ConstantBlock,
    MqttPublishBlock,
    MqttSubscribeBlock,
    ModbusReadBlock,
    ModbusWriteBlock,
    ModbusSubscribeBlock,
]

__all__ = ["MqttPublishBlock", "MqttSubscribeBlock", "IOT_BLOCKS"]
