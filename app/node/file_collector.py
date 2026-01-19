'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-19 16:15:36
LastEditors: zhai
LastEditTime: 2026-01-19 20:54:54
'''
"""
文件信息收集器 - 用于批量入库

在执行过程中收集文件信息，执行完成后批量写入数据库
"""

from typing import Dict, List, Any, Optional
from threading import Lock


class FileCollector:
    """文件信息收集器（线程安全）"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._files = {}
        return cls._instance

    def add_file(self, execution_id: str, file_info: Dict[str, Any]):
        """
        添加文件信息

        Args:
            execution_id: 执行ID
            file_info: 文件信息字典
        """
        with self._lock:
            if execution_id not in self._files:
                self._files[execution_id] = []
            self._files[execution_id].append(file_info)

    def get_files(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        获取指定执行的所有文件信息

        Args:
            execution_id: 执行ID

        Returns:
            文件信息列表
        """
        with self._lock:
            return self._files.get(execution_id, [])

    def clear_execution(self, execution_id: str):
        """
        清除指定执行的文件信息

        Args:
            execution_id: 执行ID
        """
        with self._lock:
            if execution_id in self._files:
                del self._files[execution_id]


# 全局实例
file_collector = FileCollector()
