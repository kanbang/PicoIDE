import asyncio
from typing import Dict, List, Any, Optional, Union


class Option:
    def __init__(
        self,
        name: str,
        opt_type: str,
        value: Any = None,
        items: List = None,
        min_val: Union[int, float] = None,
        max_val: Union[int, float] = None,
    ):
        self.name = name
        self.type = opt_type
        self.value = value
        self.items = items
        self.min = min_val
        self.max = max_val

    def to_dict(self) -> Dict[str, Any]:
        """导出为符合前端渲染需求的字典格式"""
        d = {"name": self.name, "type": self.type}

        if self.type != "Button":
            d["value"] = self.value

        if self.type == "Select" and self.items is not None:
            d["items"] = self.items
            d["properties"] = {"items": self.items}

        if self.type in ["Integer", "Number", "Slider"]:
            if self.min is not None:
                d["min"] = self.min
            if self.max is not None:
                d["max"] = self.max

        return d


class Block:
    def __init__(self, name: str):
        self.name = name
        self._inputs: Dict[str, Any] = {}
        self._outputs: Dict[str, Any] = {}
        self._options: Dict[str, Option] = {}
        self._input_names: List[str] = []
        self._output_names: List[str] = []

    def set_interface(self, name: str, value: Any):
        self._outputs[name] = value

    def get_interface(self, name: str):
        return self._inputs.get(name)

    # --- 基础接口 ---
    def add_input(self, name: str):
        self._input_names.append(name)
        self._inputs[name] = None

    def add_output(self, name: str):
        self._output_names.append(name)
        self._outputs[name] = None

    # --- 专用 Option 添加函数 ---

    def add_button_option(self, name: str):
        """按钮类型：无需 value"""
        self._options[name] = Option(name, "Button")

    def add_checkbox_option(self, name: str, default: bool = True):
        """复选框类型"""
        self._options[name] = Option(name, "Checkbox", value=default)

    def add_integer_option(
        self, name: str, default: int = 0, min_val: int = None, max_val: int = None
    ):
        """整数类型：支持范围限制"""
        self._options[name] = Option(
            name, "Integer", value=int(default), min_val=min_val, max_val=max_val
        )

    def add_number_option(
        self,
        name: str,
        default: float = 0.0,
        min_val: float = None,
        max_val: float = None,
    ):
        """浮点数类型：支持范围限制"""
        self._options[name] = Option(
            name, "Number", value=float(default), min_val=min_val, max_val=max_val
        )

    def add_slider_option(
        self,
        name: str,
        default: float = 0.0,
        min_val: float = 0.0,
        max_val: float = 100.0,
    ):
        """滑块类型：通常必须有 min/max"""
        self._options[name] = Option(
            name, "Slider", value=default, min_val=min_val, max_val=max_val
        )

    def add_select_option(self, name: str, items: List[str], default: str = None):
        """下拉选择类型：必须提供选项列表"""
        val = default if default else (items[0] if items else None)
        self._options[name] = Option(name, "Select", value=val, items=items)

    def add_text_option(self, name: str, default: str = ""):
        """展示文本类型（通常不可编辑）"""
        self._options[name] = Option(name, "Text", value=str(default))

    def add_text_input_option(self, name: str, default: str = ""):
        """单行文本输入"""
        self._options[name] = Option(name, "TextInput", value=str(default))

    def add_textarea_input_option(self, name: str, default: str = ""):
        """多行文本输入"""
        self._options[name] = Option(name, "TextareaInput", value=str(default))

    # --- 数据访问与执行 (保持不变) ---
    def get_option(self, name: str) -> Any:
        return self._options[name].value if name in self._options else None

    def set_option(self, name: str, value: Any):
        if name in self._options:
            opt = self._options[name]
            # 数值校验
            if opt.type in ["Integer", "Number", "Slider"]:
                if opt.min is not None:
                    value = max(opt.min, value)
                if opt.max is not None:
                    value = min(opt.max, value)
            opt.value = value

    def on_compute(self):
        pass

    async def async_on_compute(self):
        await asyncio.to_thread(self.on_compute)

    def export_config(self):
        return {
            "name": self.name,
            "inputs": [{"name": n} for n in self._input_names],
            "outputs": [{"name": n} for n in self._output_names],
            "options": [opt.to_dict() for opt in self._options.values()],
        }
