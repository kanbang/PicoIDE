import asyncio
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from flow.setting import settings
from flow.log import logger
from flow.collector import file_collector

# ==================== Option Optimization ====================
class Option:
    # 使用 __slots__ 减少内存占用
    __slots__ = ('name', 'type', 'value', 'items', 'min', 'max')

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
    def __init__(self, name: str, category: str = None):
        self.name = name
        self.category = category
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
        if name not in self._inputs: # 防止重复添加
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

    def add_integer_option(self, name: str, default: int = 0, min_val: int = None, max_val: int = None):
        self._options[name] = Option(name, "Integer", value=int(default), min_val=min_val, max_val=max_val)

    def add_number_option(self, name: str, default: float = 0.0, min_val: float = None, max_val: float = None):
        self._options[name] = Option(name, "Number", value=float(default), min_val=min_val, max_val=max_val)

    def add_slider_option(self, name: str, default: float = 0.0, min_val: float = 0.0, max_val: float = 100.0):
        self._options[name] = Option(name, "Slider", value=default, min_val=min_val, max_val=max_val)

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
            "name": self.name,
            "category": self.category,
            "inputs": [{"name": n} for n in self._input_names],
            "outputs": [{"name": n} for n in self._output_names],
            "options": [opt.to_dict() for opt in self._options.values()],
        }


# ==================== BaseBlock Optimization ====================
class BaseBlock(Block):
    def __init__(self, name: str, category: str = "General"):
        super().__init__(name, category)
        self._logger = logging.getLogger(f"{logger.name}.{name}")
        self._compute_count = 0
        self._error_count = 0
        self._last_compute_time = 0.0

    def _log_compute_start(self, execution_id: str = ""):
        self._last_compute_time = time.time()
        self._compute_count += 1
        self._logger.debug(f"[{execution_id}] 开始计算 (第 {self._compute_count} 次)")

    def _log_compute_end(self):
        elapsed = time.time() - self._last_compute_time
        self._logger.debug(f"计算完成，耗时: {elapsed:.3f}s")

    def _log_error(self, error: Exception, context: str = ""):
        self._error_count += 1
        self._logger.error(f"错误 (第 {self._error_count} 次): {context} - {error}", exc_info=True)


    def _validate_input_data(self, data: Optional[Dict[str, Any]]) -> bool:
        """验证输入数据"""
        if data is None:
            self._logger.warning("输入数据为空")
            return False
        if "data" not in data:
            self._logger.warning("输入数据缺少 'data' 字段")
            return False
        return True
    
    def safe_compute(self, execution_id: str = None) -> bool:
        """安全执行计算"""
        self._log_compute_start(execution_id)
        try:
            self.on_compute(execution_id=execution_id)
            self._log_compute_end()
            return True
        except Exception as e:
            self._log_error(e, "on_compute")
            return False

    def _register_output_file(
        self,
        execution_id: str,
        filename: str,
        file_path: Path, 
        file_size: int,   
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        注册文件核心逻辑 (纯数据操作，不进行IO写入)
        """
        if not execution_id:
            self._logger.warning("没有提供执行ID，无法注册文件")
            return ""

        # 使用更高效的 UUID 生成方式 (如果不需要极高的随机性，uuid4 足够，但 hex 切片操作没问题)
        file_id = f"{execution_id}_{uuid.uuid4().hex[:8]}"
        file_type = settings.FILE_TYPE_MAP.get(file_path.suffix.lower(), "unknown")
        file_info = {
            "file_id": file_id,
            "execution_id": execution_id,
            "filename": filename,
            "file_path": str(file_path),
            "file_type": file_type,
            "file_size": file_size,  
            "block_name": self.name,
            "block_id": str(id(self)),
            "description": description,
            "metadata": metadata or {},
        }

        # 仅一次调用收集器
        file_collector.add_file(execution_id, file_info)
        return file_id

    def _write_file(
        self,
        execution_id: str,
        filename: str,
        write_func: callable,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        优化后的文件写入方法：写入 -> 获取大小 -> 注册
        避免了 "注册后再去列表中查找并更新大小" 的低效操作
        """
        try:
            full_path = settings.OUTPUT_DIR / filename
            
            # 5. IO 操作优化：确保目录存在 (exist_ok=True 性能通常很好，但如果目录层级深可缓存检查)
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # 执行写入
            write_func(full_path)

            # 6. 立即获取文件大小
            # 如果 write_func 是异步的或者有缓冲，这里需确保 flush/close
            if full_path.exists():
                file_size = full_path.stat().st_size
            else:
                file_size = 0
                self._logger.warning(f"文件 {filename} 写入后未找到")

            # 注册文件信息（携带正确的大小）
            return self._register_output_file(
                execution_id=execution_id,
                filename=filename,
                file_path=full_path,
                file_size=file_size, # 关键优化：直接传入大小
                description=description,
                metadata=metadata,
            )

        except Exception as e:
            self._log_error(e, f"文件写入失败: {filename}")
            raise