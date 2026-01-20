"""
Demo Blocks Collection
----------------------
内置示例 Block，用于：
- 教学 / 文档
- 前端可视化展示
- 新 Block 开发模板

依赖：
- BaseBlock（支持 NAME / CATEGORY 类属性）
"""

import asyncio
import json
from pathlib import Path

from flow.block import BaseBlock


# =========================================================
# Demo / Source
# =========================================================

class ConstantBlock(BaseBlock):
    """常量数据源"""

    NAME = "Constant"
    CATEGORY = "Demo/Source"

    def __init__(self):
        super().__init__()

        self.add_output("value")

        self.add_select_option(
            "type",
            items=["Number", "Integer", "Text"],
            default="Number"
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


# =========================================================
# Demo / Math
# =========================================================

class AddBlock(BaseBlock):
    """加法"""

    NAME = "Add"
    CATEGORY = "Demo/Math"

    def __init__(self):
        super().__init__()

        self.add_input("a")
        self.add_input("b")
        self.add_output("sum")

    def on_compute(self, execution_id=None):
        a = self.get_interface("a")
        b = self.get_interface("b")

        if a is None or b is None:
            return

        self.set_interface("sum", a + b)


class NormalizeBlock(BaseBlock):
    """归一化"""

    NAME = "Normalize"
    CATEGORY = "Demo/Math"

    def __init__(self):
        super().__init__()

        self.add_input("value")
        self.add_output("out")

        self.add_number_option("min", 0.0)
        self.add_number_option("max", 1.0)

    def on_compute(self, execution_id=None):
        v = self.get_interface("value")
        if v is None:
            return

        min_v = self.get_option("min")
        max_v = self.get_option("max")

        if max_v == min_v:
            self.set_interface("out", 0.0)
            return

        self.set_interface("out", (v - min_v) / (max_v - min_v))


# =========================================================
# Demo / Logic
# =========================================================

class CompareBlock(BaseBlock):
    """比较运算"""

    NAME = "Compare"
    CATEGORY = "Demo/Logic"

    def __init__(self):
        super().__init__()

        self.add_input("a")
        self.add_input("b")
        self.add_output("result")

        self.add_select_option(
            "op",
            ["==", "!=", ">", "<", ">=", "<="],
            ">"
        )

    def on_compute(self, execution_id=None):
        a = self.get_interface("a")
        b = self.get_interface("b")

        if a is None or b is None:
            return

        op = self.get_option("op")

        result = {
            "==": a == b,
            "!=": a != b,
            ">":  a > b,
            "<":  a < b,
            ">=": a >= b,
            "<=": a <= b,
        }[op]

        self.set_interface("result", result)


# =========================================================
# Demo / Flow
# =========================================================

class GateBlock(BaseBlock):
    """数据门（enable=True 才通过）"""

    NAME = "Gate"
    CATEGORY = "Demo/Flow"

    def __init__(self):
        super().__init__()

        self.add_input("data")
        self.add_input("enable")
        self.add_output("out")

    def on_compute(self, execution_id=None):
        data = self.get_interface("data")
        enable = self.get_interface("enable")

        if enable:
            self.set_interface("out", data)


# =========================================================
# Demo / IO
# =========================================================

class DelayBlock(BaseBlock):
    """异步延迟"""

    NAME = "Delay"
    CATEGORY = "Demo/IO"

    def __init__(self):
        super().__init__()

        self.add_input("data")
        self.add_output("out")

        self.add_integer_option("delay_ms", 1000, min_val=0)

    async def async_on_compute(self, execution_id=None):
        data = self.get_interface("data")
        if data is None:
            return

        delay = self.get_option("delay_ms") / 1000.0
        await asyncio.sleep(delay)

        self.set_interface("out", data)


class FileSinkBlock(BaseBlock):
    """文本文件输出"""

    NAME = "FileSink"
    CATEGORY = "Demo/IO"

    def __init__(self):
        super().__init__()

        self.add_input("data")
        self.add_text_input_option("filename", "output.txt")

    def on_compute(self, execution_id=None):
        data = self.get_interface("data")
        if data is None:
            return

        filename = self.get_option("filename")

        def write(path: Path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(str(data))

        self._write_file(
            filename=filename,
            write_func=write,
            execution_id=execution_id,
            description="Demo text output"
        )


class JsonExportBlock(BaseBlock):
    """JSON 文件输出"""

    NAME = "JSONExport"
    CATEGORY = "Demo/IO"

    def __init__(self):
        super().__init__()

        self.add_input("data")
        self.add_text_input_option("filename", "data.json")

    def on_compute(self, execution_id=None):
        data = self.get_interface("data")
        if data is None:
            return

        filename = self.get_option("filename")

        def write(path: Path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        self._write_file(
            filename=filename,
            write_func=write,
            execution_id=execution_id,
            description="Demo JSON export"
        )


# =========================================================
# Demo / Debug
# =========================================================

class LoggerBlock(BaseBlock):
    """日志输出"""

    NAME = "Logger"
    CATEGORY = "Demo/Debug"

    def __init__(self):
        super().__init__()

        self.add_input("data")
        self.add_checkbox_option("print", True)

    def on_compute(self, execution_id=None):
        data = self.get_interface("data")
        if data is None:
            return

        if self.get_option("print"):
            self._logger.info(f"[LoggerBlock] {data}")


class CounterBlock(BaseBlock):
    """状态计数器"""

    NAME = "Counter"
    CATEGORY = "Demo/Debug"

    def __init__(self):
        super().__init__()

        self.add_input("tick")
        self.add_output("count")
        self.add_button_option("reset")

        self._count = 0

    def on_compute(self, execution_id=None):
        if self.get_interface("tick") is not None:
            self._count += 1

        self.set_interface("count", self._count)


class InspectorBlock(BaseBlock):
    """数据探针"""

    NAME = "Inspector"
    CATEGORY = "Demo/Debug"

    def __init__(self):
        super().__init__()

        self.add_input("data")
        self.add_output("type")
        self.add_output("repr")

    def on_compute(self, execution_id=None):
        data = self.get_interface("data")
        if data is None:
            return

        self.set_interface("type", type(data).__name__)
        self.set_interface("repr", repr(data))


# =========================================================
# 统一导出（用于自动注册）
# =========================================================

DEMO_BLOCKS = [
    ConstantBlock,
    AddBlock,
    NormalizeBlock,
    CompareBlock,
    GateBlock,
    DelayBlock,
    FileSinkBlock,
    JsonExportBlock,
    LoggerBlock,
    CounterBlock,
    InspectorBlock,
]
