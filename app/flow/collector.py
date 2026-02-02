'''
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-19 16:15:36
LastEditors: zhai
LastEditTime: 2026-02-02 12:49:15
'''
"""
文件信息收集器 - 用于实时入库和推送

在执行过程中收集文件信息，并即时通过事件总线推送给前端
如果启用了数据库写入，会在文件产生时立即入库
"""

from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from flow.setting import settings
import asyncio


class FileCollector:
    """文件信息收集器（异步安全）"""

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
        设置事件回调函数，当添加文件时即时触发

        Args:
            callback: 回调函数，签名为 callback(execution_id: str, node_type: str, file_info: Dict)
        """
        self._event_callback = callback

    async def add_file(self, execution_id: str, node_type: str, file_info: Dict[str, Any]):
        """
        添加文件信息（添加时即时触发事件推送和数据库入库）

        Args:
            execution_id: 执行ID
            node_type: 节点类型（block.NAME）
            file_info: 文件信息字典
        """
        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            if exe_id not in self._files:
                self._files[exe_id] = []

            # 添加缺失的字段，保持与数据库查询格式一致
            file_type = file_info.get("file_type", "unknown")
            file_info["can_open"] = file_type in settings.BROWSER_OPENABLE
            file_info["can_download"] = True
            file_info["node_type"] = node_type  # 添加节点类型

            if "created_at" not in file_info:
                file_info["created_at"] = datetime.now().isoformat()

            self._files[exe_id].append(file_info)

        # 即时触发事件推送
        if self._event_callback:
            self._event_callback(execution_id, node_type, file_info)

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

    async def update_file(self, execution_id: str, file_id: str, file_size: int):
        """
        更新文件信息（追加内容时调用）

        Args:
            execution_id: 执行ID
            file_id: 文件ID
            file_size: 更新后的文件大小
        """
        # 更新 self._files 里的文件信息
        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            files = self._files.get(exe_id, [])
            for f in files:
                if f.get("file_id") == file_id:
                    f["file_size"] = file_size
                    break

        # 如果启用了数据库写入，立即更新（异步）
        if settings.ENABLE_DB_WRITE:
            asyncio.create_task(self._update_file_in_db(file_id, file_size))

    async def _update_file_in_db(self, file_id: str, file_size: int):
        """异步更新数据库中的文件信息"""
        try:
            from db import Output
            # 根据file_id查找并更新
            output = await Output.filter(file_id=file_id).first()
            if output:
                output.file_size = file_size
                await output.save()
        except Exception as e:
            # 更新失败不影响主流程，仅记录日志
            print(f"更新文件到数据库失败: {e}")

    async def get_files(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        获取指定执行的所有文件信息

        Args:
            execution_id: 执行ID

        Returns:
            文件信息列表（格式与数据库查询一致）
        """
        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            return self._files.get(exe_id, [])

    async def clear_execution(self, execution_id: str):
        """
        清除指定执行的文件信息

        Args:
            execution_id: 执行ID
        """
        async with self._lock:
            exe_id = execution_id or self._temp_execution_id
            if exe_id in self._files:
                del self._files[exe_id]


# 全局实例
file_collector = FileCollector()