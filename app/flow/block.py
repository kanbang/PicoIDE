import asyncio
import time
from typing import Dict, List, Any, Optional, Union
import logging
from flow.setting import settings
from flow.log import logger
from flow.collector import file_collector


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
    def __init__(self, name: str, category: str = None):
        self.name = name
        self.category = category
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

    def reset(self):
        """重置运行时状态，保持配置不变"""
        # 清除输入
        for key in self._inputs:
            self._inputs[key] = None
        # 清除输出
        for key in self._outputs:
            self._outputs[key] = None
        # 如果有缓存的中间计算状态（如累计和、历史 buffer），也在这里清除

    def on_compute(self, execution_id: str = None):
        pass

    async def async_on_compute(self, execution_id: str = None):
        """异步执行接口：在线程池中执行同步的 on_compute"""
        await asyncio.to_thread(self.on_compute, execution_id)

    def export_config(self):
        return {
            "name": self.name,
            "category": self.category,
            "inputs": [{"name": n} for n in self._input_names],
            "outputs": [{"name": n} for n in self._output_names],
            "options": [opt.to_dict() for opt in self._options.values()],
        }




# ==================== BaseBlock - 基础Block类 ====================


class BaseBlock(Block):
    """
    所有Block的基类，提供通用功能

    功能：
    - 统一的错误处理
    - 日志记录
    - 数据验证
    - 性能监控
    """

    def __init__(self, name: str, category: str = "General"):
        super().__init__(name, category)
        self._logger = logging.getLogger(f"{logger.name}.{name}")
        self._compute_count = 0
        self._error_count = 0
        self._last_compute_time = 0.0

    def _log_compute_start(self) -> None:
        """记录计算开始"""
        self._last_compute_time = time.time()
        self._compute_count += 1
        self._logger.debug(f"开始计算 (第 {self._compute_count} 次)")

    def _log_compute_end(self) -> None:
        """记录计算结束"""
        elapsed = time.time() - self._last_compute_time
        self._logger.debug(f"计算完成，耗时: {elapsed:.3f}s")

    def _log_error(self, error: Exception, context: str = "") -> None:
        """记录错误"""
        self._error_count += 1
        self._logger.error(f"错误 (第 {self._error_count} 次): {context} - {error}")

    def _validate_input_data(self, data: Optional[Dict[str, Any]]) -> bool:
        """验证输入数据"""
        if data is None:
            self._logger.warning("输入数据为空")
            return False
        if "data" not in data:
            self._logger.warning("输入数据缺少 'data' 字段")
            return False
        return True

    def safe_compute(self) -> bool:
        """安全执行计算（带错误处理）"""
        self._log_compute_start()
        try:
            self.on_compute()
            self._log_compute_end()
            return True
        except Exception as e:
            self._log_error(e, "on_compute")
            return False

    def _register_output_file(
            self,
            execution_id: str,
            filename: str,
            description: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None,
            enable_db: Optional[bool] = None
        ) -> str:
            """
            注册输出文件到文件管理器
    
            Args:
                execution_id: 执行ID
                filename: 文件名
                description: 描述
                metadata: 元数据
                enable_db: 是否写入数据库（None表示使用全局配置）
    
            Returns:
                文件ID
            """
            if execution_id is None:
                self._logger.warning("没有提供执行ID，无法注册文件")
                return ""
    
            # 生成文件ID
            import uuid
            file_id = f"{execution_id}_{uuid.uuid4().hex[:8]}"
    
            # 构建完整文件路径
            full_path = settings.OUTPUT_DIR / filename
    
            # 确保目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)
    
            # 获取文件类型
            file_type = settings.FILE_TYPE_MAP.get(  full_path.suffix.lower(), "unknown"   )
    
            # 确定是否启用数据库写入
            if enable_db is None:
                enable_db = settings.ENABLE_DB_WRITE    
            # 创建文件信息字典（用于后续批量入库）
            file_info = {
                "file_id": file_id,
                "execution_id": execution_id,
                "filename": filename,
                "file_path": str(full_path),
                "file_type": file_type,
                "file_size": 0,  # 文件大小在文件写入后更新
                "block_name": self.name,
                "block_id": str(id(self)),
                "description": description,
                "metadata": metadata or {},
            }
    
            # 始终将文件信息添加到收集器（无论是否启用数据库）
            file_collector.add_file(execution_id, file_info)
    
            return file_id
    def _write_file(
        self,
        execution_id: str,
        filename: str,
        write_func: callable,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        enable_db: Optional[bool] = None
    ) -> str:
        """
        通用文件写入方法

        Args:
            execution_id: 执行ID
            filename: 文件名
            write_func: 写入函数，接受文件路径作为参数
            description: 描述
            metadata: 元数据
            enable_db: 是否写入数据库（None表示使用全局配置）

        Returns:
            文件ID
        """
        try:
            # 使用统一的输出目录
            full_path = settings.OUTPUT_DIR / filename
            # 确保输出目录存在
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # 调用写入函数
            write_func(full_path)

            # 确定是否启用数据库写入
            if enable_db is None:
                enable_db = settings.ENABLE_DB_WRITE

            # 注册到文件管理器
            file_id = self._register_output_file(
                execution_id=execution_id,
                filename=filename,
                description=description,
                metadata=metadata,
                enable_db=enable_db
            )

            # 更新文件大小
            if file_id and full_path.exists():
                file_size = full_path.stat().st_size
                # 更新收集器中的文件信息
                files = file_collector.get_files(execution_id)
                for f in files:
                    if f["file_id"] == file_id:
                        f["file_size"] = file_size
                        break

            return file_id
        except Exception as e:
            self._log_error(e, "文件写入")
            raise

