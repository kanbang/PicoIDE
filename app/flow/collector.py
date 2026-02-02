'''
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-19 16:15:36
LastEditors: zhai
LastEditTime: 2026-01-30 10:33:50
'''
"""
文件信息收集器 - 用于实时入库和推送

在执行过程中收集文件信息，并即时通过事件总线推送给前端
如果启用了数据库写入，会在文件产生时立即入库
"""

from typing import Dict, List, Any, Optional, Callable
from threading import Lock
from datetime import datetime
from flow.setting import settings
import asyncio


class FileCollector:
    """文件信息收集器（线程安全）"""

    _instance = None
    _lock = Lock()

    _temp_execution_id = "_temp_"

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._files = {}
                    cls._instance._event_callback: Optional[Callable] = None
        return cls._instance

    def set_event_callback(self, callback: Callable):
        """
        设置事件回调函数，当添加文件时即时触发

        Args:
            callback: 回调函数，签名为 callback(execution_id: str, file_info: Dict)
        """
        with self._lock:
            self._event_callback = callback

    def add_file(self, execution_id: str, file_info: Dict[str, Any]):
        """
        添加文件信息（添加时即时触发事件推送和数据库入库）

        Args:
            execution_id: 执行ID
            file_info: 文件信息字典
        """
        with self._lock:
            exe_id = execution_id or self._temp_execution_id
            if exe_id not in self._files:
                self._files[exe_id] = []

            # 添加缺失的字段，保持与数据库查询格式一致
            file_type = file_info.get("file_type", "unknown")
            file_info["can_open"] = file_type in settings.BROWSER_OPENABLE
            file_info["can_download"] = True

            if "created_at" not in file_info:
                file_info["created_at"] = datetime.now().isoformat()

            self._files[exe_id].append(file_info)

            # 即时触发事件推送（在锁外执行，避免死锁）
        if self._event_callback:
            self._event_callback(execution_id, file_info)

        # 如果启用了数据库写入，立即入库（异步）
        if settings.ENABLE_DB_WRITE:
            asyncio.create_task(self._save_file_to_db(execution_id, file_info))

    async def _save_file_to_db(self, execution_id: str, file_info: Dict[str, Any]):
        """异步保存单个文件到数据库"""
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
            # 入库失败不影响主流程，仅记录日志
            print(f"保存文件到数据库失败: {e}")

    def get_files(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        获取指定执行的所有文件信息

        Args:
            execution_id: 执行ID

        Returns:
            文件信息列表（格式与数据库查询一致）
        """
        with self._lock:
            exe_id = execution_id or self._temp_execution_id
            return self._files.get(exe_id, [])

    def clear_execution(self, execution_id: str):
        """
        清除指定执行的文件信息

        Args:
            execution_id: 执行ID
        """
        with self._lock:
            exe_id = execution_id or self._temp_execution_id
            if exe_id in self._files:
                del self._files[exe_id]


# 全局实例
file_collector = FileCollector()