import asyncio
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from pathlib import Path
from flow.setting import settings
from flow.log import logger
from flow.collector import file_collector
from flow.runtime_bus import RuntimeEventBus, RuntimeEvent, RuntimeEventType


# ==================== Option Optimization ====================
class Option:
    # 使用 __slots__ 减少内存占用
    __slots__ = ("name", "type", "value", "items", "min", "max")

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
        """优化后的字典导出逻辑"""
        d = {"name": self.name, "type": self.type}

        if self.type != "Button":
            d["value"] = self.value

        # 2. 逻辑简化：直接根据类型映射属性
        if self.type == "Select" and self.items is not None:
            d["items"] = self.items
            d["properties"] = {"items": self.items}

        # 统一处理数值范围
        if self.type in ("Integer", "Number", "Slider"):
            if self.min is not None:
                d["min"] = self.min
            if self.max is not None:
                d["max"] = self.max

        return d


# ==================== Block Optimization ====================
class Block:
    NAME = "Block"
    CATEGORY = "General"
    STREAMING = False

    def __init__(self):
        # 使用 slots 的话 inputs/outputs 也需要调整，这里为了扩展性暂保留 dict
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
        if name not in self._inputs:  # 防止重复添加
            self._input_names.append(name)
            self._inputs[name] = None

    def add_output(self, name: str):
        if name not in self._outputs:
            self._output_names.append(name)
            self._outputs[name] = None

    # --- Option Helper Methods (保持原有API，内部逻辑微调) ---
    def add_button_option(self, name: str):
        self._options[name] = Option(name, "Button")

    def add_checkbox_option(self, name: str, default: bool = True):
        self._options[name] = Option(name, "Checkbox", value=default)

    def add_integer_option(
        self, name: str, default: int = 0, min_val: int = None, max_val: int = None
    ):
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
        self._options[name] = Option(
            name, "Slider", value=default, min_val=min_val, max_val=max_val
        )

    def add_select_option(self, name: str, items: List[str], default: str = None):
        val = default if default else (items[0] if items else None)
        self._options[name] = Option(name, "Select", value=val, items=items)

    def add_text_option(self, name: str, default: str = ""):
        self._options[name] = Option(name, "Text", value=str(default))

    def add_text_input_option(self, name: str, default: str = ""):
        self._options[name] = Option(name, "TextInput", value=str(default))

    def add_textarea_input_option(self, name: str, default: str = ""):
        self._options[name] = Option(name, "TextareaInput", value=str(default))

    def get_option(self, name: str) -> Any:
        opt = self._options.get(name)
        return opt.value if opt else None

    def set_option(self, name: str, value: Any):
        opt = self._options.get(name)
        if not opt:
            return

        # 3. 优化数值校验逻辑：使用 min/max 函数前先判断 None，避免 TypeError
        if opt.type in ("Integer", "Number", "Slider"):
            if opt.min is not None and value < opt.min:
                value = opt.min
            if opt.max is not None and value > opt.max:
                value = opt.max
        opt.value = value

    def reset(self):
        """重置运行时状态"""
        # 使用 fromkeys 快速重置字典值
        self._inputs = dict.fromkeys(self._inputs, None)
        self._outputs = dict.fromkeys(self._outputs, None)

    def on_compute(self, execution_id: str = None):
        """子类覆盖此方法"""
        pass

    async def async_on_compute(self, execution_id: str = None):
        """异步执行接口"""
        await asyncio.to_thread(self.on_compute, execution_id)

    def export_config(self):
        return {
            "name": self.NAME,
            "category": self.CATEGORY,
            "inputs": [{"name": n} for n in self._input_names],
            "outputs": [{"name": n} for n in self._output_names],
            "options": [opt.to_dict() for opt in self._options.values()],
        }


# ==================== BaseBlock Optimization ====================


class BaseBlock(Block):
    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(f"{logger.name}.{self.NAME}")
        self._compute_count = 0
        self._error_count = 0
        self._last_compute_time = 0.0
        self._file_ids: Dict[str, str] = {}  # filename -> file_id for appendable files
        self.event_bus = RuntimeEventBus()  # 使用单例 for emitting events

    def _log_compute_start(self, execution_id: str = ""):
        self._last_compute_time = time.time()
        self._compute_count += 1
        self._logger.debug(f"[{execution_id}] 开始计算 (第 {self._compute_count} 次)")

    def _log_compute_end(self):
        elapsed = time.time() - self._last_compute_time
        self._logger.debug(f"计算完成，耗时: {elapsed:.3f}s")

    def _log_error(self, error: Exception, context: str = ""):
        self._error_count += 1
        self._logger.error(
            f"错误 (第 {self._error_count} 次): {context} - {error}", exc_info=True
        )

    def _validate_input_data(self, data: Optional[Dict[str, Any]]) -> bool:
        if data is None:
            self._logger.warning("输入数据为空")
            return False
        if "data" not in data:
            self._logger.warning("输入数据缺少 'data' 字段")
            return False
        return True

    def safe_compute(self, execution_id: str = None) -> bool:
        self._log_compute_start(execution_id)
        try:
            self.on_compute(execution_id=execution_id)
            self._log_compute_end()
            return True
        except Exception as e:
            self._log_error(e, "on_compute")
            return False

    def _write_file(
        self,
        filename: str,
        write_func: Callable[[Path, str], None],  # write_func(full_path, mode)
        execution_id: Optional[str],
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        unique: bool = True,
        mode: str = "w",  # 'w' or 'a'
    ) -> str:
        """
        原子化执行：自动分目录 -> 路径唯一化/固定 -> 写入/追加 -> 系统注册/事件推送
        """
        try:
            # 1. 生成时间标记
            now = time.localtime()
            date_dir = time.strftime("%Y%m%d", now)  # 文件夹名：20240520
            timestamp = time.strftime("%H%M%S", now)  # 文件名时间戳：143005
            unique_suffix = uuid.uuid4().hex[:8]  # 随机后缀

            # 2. 构建路径
            path_obj = Path(filename)
            if unique:
                # 唯一模式：生成新文件名
                unique_filename = (
                    f"{path_obj.stem}_{timestamp}_{unique_suffix}{path_obj.suffix}"
                )
                target_dir = settings.OUTPUT_DIR / date_dir
                full_path = target_dir / unique_filename
                relative_path = f"{date_dir}/{unique_filename}"
                # 强制写模式
                effective_mode = "w"
            else:
                # 固定模式：使用原文件名
                unique_filename = filename
                target_dir = settings.OUTPUT_DIR / date_dir
                full_path = target_dir / unique_filename
                relative_path = f"{date_dir}/{unique_filename}"
                # 检查是否存在来决定是否创建新记录
                file_exists = full_path.exists()
                if mode == "a" and file_exists:
                    effective_mode = "a"
                else:
                    effective_mode = "w"

            # 确保父级目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # 3. 执行写入/追加回调
            write_func(full_path, effective_mode)

            # 4. 获取文件状态 (Size)
            file_size = full_path.stat().st_size if full_path.exists() else 0

            # 5. 处理注册或事件
            file_type = settings.FILE_TYPE_MAP.get(full_path.suffix.lower(), "unknown")
            file_id = self._file_ids.get(filename)  # 对于非唯一，尝试获取现有ID

            if unique or file_id is None:
                # 新文件：生成ID并注册
                file_id = f"{execution_id or 'temp'}_{unique_suffix}"
                file_info = {
                    "file_id": file_id,
                    "execution_id": execution_id,
                    "filename": unique_filename,
                    "relative_path": relative_path,  # 记录相对路径，方便迁移
                    "file_path": str(full_path),
                    "file_type": file_type,
                    "file_size": file_size,
                    "block_name": self.NAME,
                    "block_id": str(id(self)),
                    "description": description or "Unique hierarchical output",
                    "metadata": metadata or {},
                    "original_name": filename,
                }

                # 推送至收集器（触发生成事件）
                file_collector.add_file(execution_id, file_info)

                if not unique:
                    # 对于固定文件，存储ID以便后续追加
                    self._file_ids[filename] = file_id
            else:
                # 追加：发送更新事件
                asyncio.create_task(
                    self.event_bus.emit(
                        RuntimeEvent(
                            execution_id,
                            RuntimeEventType.DATA,
                            self.NAME,
                            f"Appended to file: {unique_filename}",
                            payload={
                                "file_id": file_id,
                                "action": "append",
                                # 可以添加更多payload，如追加的内容摘要
                            },
                        )
                    )
                )

            return file_id

        except Exception as e:
            self._log_error(e, f"文件处理失败: {filename}")
            raise
        

# ==================== DebugBlock (用于流程中收集特定节点信息) ====================
class DebugBlock(BaseBlock):
    NAME = "Debug Logger"
    CATEGORY = "Utilities"
    STREAMING = False

    def __init__(self):
        super().__init__()
        self.add_input("data")  # 任意输入数据，用于触发
        self.event_bus = RuntimeEventBus()  # 使用单例

    async def async_on_compute(self, execution_id: str = None):
        data = self.get_interface("data")
        log_msg = f"{data}"

        # 推送事件到队列
        await self.event_bus.emit(
            RuntimeEvent(
                execution_id,
                RuntimeEventType.DEBUG,
                self.instance_id,
                log_msg,
                payload=data,
            )
        )
