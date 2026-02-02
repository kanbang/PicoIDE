import asyncio
import time
import uuid
import logging
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from pathlib import Path
from flow.setting import settings
from flow.log import logger
from flow.collector import file_collector
from flow.runtime_bus import RuntimeEventBus, RuntimeEvent, RuntimeEventType

# ==================== Option Class ====================
class Option:
    """Represents an option with type-specific attributes."""
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
        """Exports the option to a dictionary."""
        result = {"name": self.name, "type": self.type}
        if self.type != "Button":
            result["value"] = self.value

        if self.type == "Select" and self.items is not None:
            result["items"] = self.items
            result["properties"] = {"items": self.items}

        if self.type in ("Integer", "Number", "Slider"):
            if self.min is not None:
                result["min"] = self.min
            if self.max is not None:
                result["max"] = self.max

        return result

# ==================== Block Class ====================
class Block:
    """Base class for blocks in the flow system."""
    NAME = "Block"
    CATEGORY = "General"
    STREAMING = False

    def __init__(self):
        self._inputs: Dict[str, Any] = {}
        self._outputs: Dict[str, Any] = {}
        self._options: Dict[str, Option] = {}
        self._input_names: List[str] = []
        self._output_names: List[str] = []

    def set_interface(self, name: str, value: Any):
        """Sets an output interface value."""
        self._outputs[name] = value

    def get_interface(self, name: str) -> Any:
        """Gets an input interface value."""
        return self._inputs.get(name)

    def add_input(self, name: str):
        """Adds an input if it doesn't exist."""
        if name not in self._inputs:
            self._input_names.append(name)
            self._inputs[name] = None

    def add_output(self, name: str):
        """Adds an output if it doesn't exist."""
        if name not in self._outputs:
            self._output_names.append(name)
            self._outputs[name] = None

    # --- Option Helper Methods ---
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
        value = default if default else (items[0] if items else None)
        self._options[name] = Option(name, "Select", value=value, items=items)

    def add_text_option(self, name: str, default: str = ""):
        self._options[name] = Option(name, "Text", value=str(default))

    def add_text_input_option(self, name: str, default: str = ""):
        self._options[name] = Option(name, "TextInput", value=str(default))

    def add_textarea_input_option(self, name: str, default: str = ""):
        self._options[name] = Option(name, "TextareaInput", value=str(default))

    def get_option(self, name: str) -> Any:
        """Gets the value of an option."""
        opt = self._options.get(name)
        return opt.value if opt else None

    def set_option(self, name: str, value: Any):
        """Sets the value of an option with validation."""
        opt = self._options.get(name)
        if not opt:
            return

        if opt.type in ("Integer", "Number", "Slider"):
            if opt.min is not None:
                value = max(value, opt.min)
            if opt.max is not None:
                value = min(value, opt.max)

        opt.value = value

    def reset(self):
        """Resets inputs and outputs to None."""
        self._inputs = {key: None for key in self._inputs}
        self._outputs = {key: None for key in self._outputs}

    def on_compute(self, execution_id: str = None):
        """To be overridden by subclasses for computation logic."""
        pass

    async def async_on_compute(self, execution_id: str = None):
        """Asynchronous wrapper for on_compute."""
        await asyncio.to_thread(self.on_compute, execution_id)

    def export_config(self) -> Dict[str, Any]:
        """Exports the block configuration."""
        return {
            "name": self.NAME,
            "category": self.CATEGORY,
            "inputs": [{"name": n} for n in self._input_names],
            "outputs": [{"name": n} for n in self._output_names],
            "options": [opt.to_dict() for opt in self._options.values()],
        }

# ==================== BaseBlock Class ====================
class BaseBlock(Block):
    """Extended block with logging, metrics, and file handling."""

    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger(f"{logger.name}.{self.NAME}")
        self._compute_count = 0
        self._error_count = 0
        self._last_compute_time = 0.0
        self._execution_files: Dict[Tuple[str, str], str] = {}  # (filename, execution_id) -> unique_filename
        self._file_ids: Dict[Tuple[str, str], str] = {}  # (filename, execution_id) -> file_id
        self.event_bus = RuntimeEventBus()  # Singleton for emitting events

    def _log_compute_start(self, execution_id: str = ""):
        """Logs the start of computation."""
        self._last_compute_time = time.time()
        self._compute_count += 1
        self._logger.debug(f"[{execution_id}] Starting computation (#{self._compute_count})")

    def _log_compute_end(self):
        """Logs the end of computation with elapsed time."""
        elapsed = time.time() - self._last_compute_time
        self._logger.debug(f"Computation completed in {elapsed:.3f}s")

    def _log_error(self, error: Exception, context: str = ""):
        """Logs an error with context."""
        self._error_count += 1
        self._logger.error(
            f"Error (#{self._error_count}): {context} - {error}", exc_info=True
        )

    def _validate_input_data(self, data: Optional[Dict[str, Any]]) -> bool:
        """Validates input data structure."""
        if data is None:
            self._logger.warning("Input data is None")
            return False
        if "data" not in data:
            self._logger.warning("Input data missing 'data' field")
            return False
        return True

    def safe_compute(self, execution_id: str = None) -> bool:
        """Safely executes on_compute with logging."""
        self._log_compute_start(execution_id)
        try:
            self.on_compute(execution_id=execution_id)
            self._log_compute_end()
            return True
        except Exception as e:
            self._log_error(e, "in on_compute")
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
        Handles file writing/appending with unique naming, directory management,
        and event emission. Returns the file_id.
        """
        try:
            # Generate timestamps and unique suffix
            now = time.localtime()
            date_dir = time.strftime("%Y%m%d", now)
            timestamp = time.strftime("%H%M%S", now)
            unique_suffix = uuid.uuid4().hex[:8]

            # Parse filename
            path_obj = Path(filename)
            target_dir = settings.OUTPUT_DIR / date_dir

            # Determine unique filename and mode
            if unique:
                unique_filename = f"{path_obj.stem}_{timestamp}_{unique_suffix}{path_obj.suffix}"
                effective_mode = "w"
                file_key = None
            else:
                file_key = (filename, execution_id or "_temp_")
                exec_suffix = execution_id or unique_suffix
                if file_key not in self._execution_files:
                    unique_filename = f"{path_obj.stem}_{exec_suffix}_{timestamp}_{unique_suffix}{path_obj.suffix}"
                    self._execution_files[file_key] = unique_filename
                else:
                    unique_filename = self._execution_files[file_key]

                full_path = target_dir / unique_filename
                effective_mode = "a" if mode == "a" and full_path.exists() else "w"

            # Build full and relative paths
            full_path = target_dir / unique_filename
            relative_path = f"{date_dir}/{unique_filename}"

            # Ensure directory exists
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Execute write/append
            write_func(full_path, effective_mode)

            # Get file size
            file_size = full_path.stat().st_size if full_path.exists() else 0

            # Determine file type
            file_type = settings.FILE_TYPE_MAP.get(full_path.suffix.lower(), "unknown")

            # Handle new file or append
            if unique or (file_key and file_key not in self._file_ids):
                # New file: Generate ID, register, and add to collector
                file_id = f"{execution_id or 'temp'}_{unique_suffix}"
                file_info = {
                    "file_id": file_id,
                    "execution_id": execution_id,
                    "filename": unique_filename,
                    "relative_path": relative_path,
                    "file_path": str(full_path),
                    "file_type": file_type,
                    "file_size": file_size,
                    "block_name": self.NAME,
                    "block_id": str(id(self)),
                    "description": description or "Unique hierarchical output",
                    "metadata": metadata or {},
                    "original_name": filename,
                }
                # 使用 asyncio.create_task 异步调用 add_file
                asyncio.create_task(file_collector.add_file(execution_id, file_info))
                if not unique:
                    self._file_ids[file_key] = file_id
            else:
                # Append: Emit update event and update database
                file_id = self._file_ids[file_key]
                # 更新数据库中的文件大小
                asyncio.create_task(file_collector.update_file(execution_id, file_id, file_size))
                # 发出事件通知
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
                            },
                        )
                    )
                )

            return file_id
        except Exception as e:
            self._log_error(e, f"File processing failed: {filename}")
            raise

# ==================== DebugBlock Class ====================
class DebugBlock(BaseBlock):
    """Block for logging debug information."""
    NAME = "Debug Logger"
    CATEGORY = "Utilities"
    STREAMING = False

    def __init__(self):
        super().__init__()
        self.add_input("data")  # Input to trigger logging
        self.event_bus = RuntimeEventBus()  # Singleton

    async def async_on_compute(self, execution_id: str = None):
        """Asynchronously logs input data and emits a debug event."""
        data = self.get_interface("data")
        log_msg = f"{data}"
        await self.event_bus.emit(
            RuntimeEvent(
                execution_id,
                RuntimeEventType.DEBUG,
                self.NAME,  # Fixed: Use self.NAME instead of undefined instance_id
                log_msg,
                payload=data,
            )
        )