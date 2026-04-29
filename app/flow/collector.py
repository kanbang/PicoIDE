"""
File collector for execution outputs.
"""

from datetime import datetime
import asyncio
from typing import Any, Callable, Dict, List, Optional

from flow.setting import settings


class FileCollector:
    """Collect output files in memory and optionally persist them."""

    _instance = None
    _lock = asyncio.Lock()
    _temp_execution_id = "_temp_"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._files = {}
            cls._instance._event_callback: Optional[Callable] = None
        return cls._instance

    def set_event_callback(self, callback: Callable):
        """
        Set file event callback.

        Callback signature:
            callback(execution_id: str, node_type: str, file_info: Dict, action: str)
        """
        self._event_callback = callback

    async def add_file(self, execution_id: str, node_type: str, file_info: Dict[str, Any]):
        """Add a new file and notify listeners immediately."""
        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            if exe_id not in self._files:
                self._files[exe_id] = []

            file_type = file_info.get("file_type", "unknown")
            file_info["can_open"] = file_type in settings.BROWSER_OPENABLE
            file_info["can_download"] = True
            file_info["node_type"] = node_type

            if "created_at" not in file_info:
                file_info["created_at"] = datetime.now().isoformat()

            self._files[exe_id].append(file_info)
            event_file = dict(file_info)

        if self._event_callback:
            self._event_callback(execution_id, node_type, event_file, "create")

        if settings.ENABLE_DB_WRITE:
            asyncio.create_task(self._save_file_to_db(execution_id, event_file))

    async def _save_file_to_db(self, execution_id: str, file_info: Dict[str, Any]):
        """Persist one file record asynchronously."""
        try:
            from db import Output

            await Output.create(
                file_id=file_info.get("file_id"),
                execution_id=execution_id,
                filename=file_info.get("filename"),
                file_path=file_info.get("file_path"),
                file_type=file_info.get("file_type"),
                file_size=file_info.get("file_size"),
                block_name=file_info.get("block_name"),
                block_id=file_info.get("block_id"),
                description=file_info.get("description"),
                metadata=file_info.get("metadata"),
                is_deleted=False,
            )
        except Exception as e:
            print(f"Failed to save output file record: {e}")

    async def update_file(self, execution_id: str, file_id: str, file_size: int):
        """Update file size and notify listeners with the full file payload."""
        updated_file: Optional[Dict[str, Any]] = None

        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            files = self._files.get(exe_id, [])
            for f in files:
                if f.get("file_id") == file_id:
                    f["file_size"] = file_size
                    updated_file = dict(f)
                    break

        if updated_file is not None and self._event_callback:
            self._event_callback(
                execution_id,
                updated_file.get("node_type", ""),
                updated_file,
                "append",
            )

        if settings.ENABLE_DB_WRITE:
            asyncio.create_task(self._update_file_in_db(file_id, file_size))

    async def _update_file_in_db(self, file_id: str, file_size: int):
        """Persist file size updates asynchronously."""
        try:
            from db import Output

            output = await Output.filter(file_id=file_id).first()
            if output:
                output.file_size = file_size
                await output.save()
        except Exception as e:
            print(f"Failed to update output file record: {e}")

    async def get_files(self, execution_id: str) -> List[Dict[str, Any]]:
        """Get all files for one execution."""
        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            return self._files.get(exe_id, [])

    async def remove_file(self, execution_id: str, file_id: str) -> bool:
        """Remove one file from the in-memory collector."""
        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            files = self._files.get(exe_id)
            if not files:
                return False

            remaining_files = [f for f in files if f.get("file_id") != file_id]
            if len(remaining_files) == len(files):
                return False

            if remaining_files:
                self._files[exe_id] = remaining_files
            else:
                del self._files[exe_id]
            return True

    async def clear_execution(self, execution_id: str):
        """Clear one execution's in-memory files."""
        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            if exe_id in self._files:
                del self._files[exe_id]


file_collector = FileCollector()
