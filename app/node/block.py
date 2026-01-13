"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-13 19:01:46
LastEditors: zhai
LastEditTime: 2026-01-13 19:01:52
"""

import asyncio
import inspect
from typing import Dict, List, Any, Optional


class Option:
    def __init__(self, name: str, opt_type: str, value: Any, items: List = None):
        self.name = name
        self.type = opt_type
        self.value = value
        self.items = items

    def to_dict(self):
        d = {"name": self.name, "type": self.type, "value": self.value}
        if self.items is not None:
            d["items"] = self.items
            d["properties"] = {"items": self.items}
        return d


class Block:
    def __init__(self, name: str):
        self.name = name
        self._inputs: Dict[str, Any] = {}  # 运行时的连线输入
        self._outputs: Dict[str, Any] = {}  # 运行时的连线输出
        self._options: Dict[str, Option] = {}  # 静态配置项
        self._input_names: List[str] = []  # 定义输入的 key
        self._output_names: List[str] = []  # 定义输出的 key

    def add_input(self, name: str):
        self._input_names.append(name)
        self._inputs[name] = None

    def add_output(self, name: str):
        self._output_names.append(name)
        self._outputs[name] = None

    def add_option(self, name: str, opt_type: str, value: Any, items: List = None):
        self._options[name] = Option(name, opt_type, value, items)

    def get_option(self, name: str):
        return self._options[name].value

    def set_option(self, name: str, value: Any):
        if name in self._options:
            self._options[name].value = value

    def get_interface(self, name: str):
        return self._inputs.get(name)

    def set_interface(self, name: str, value: Any):
        self._outputs[name] = value

    def is_async(self) -> bool:
        return inspect.iscoroutinefunction(self.on_compute)

    def on_compute(self):
        """同步模式下执行逻辑，子类覆盖"""
        pass

    async def async_on_compute(self):
        """异步模式下执行逻辑，默认回退到同步逻辑"""
        # 如果子类没写异步版本，默认在线程池跑同步版本，确保兼容性
        await asyncio.to_thread(self.on_compute)

    def export_config(self):
        """导出为要求的 JSON 格式"""
        return {
            "name": self.name,
            "inputs": [{"name": n} for n in self._input_names],
            "outputs": [{"name": n} for n in self._output_names],
            "options": [opt.to_dict() for opt in self._options.values()],
        }
