"""
节点全局配置 - 统一配置管理

功能：
- 统一管理所有节点相关的配置项
- 支持运行时动态修改
- 提供配置查询接口
"""

import logging
from typing import Dict, Any
from pathlib import Path


class NodeSettings:
    """节点全局配置"""

    # 日志
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ==================== 文件输出配置 ====================

    # 输出目录
    OUTPUT_DIR = Path("./output")

    # 临时目录
    TEMP_DIR = Path("./temp")

    # 文件类型映射
    FILE_TYPE_MAP = {
        ".html": "html",
        ".csv": "csv",
        ".json": "json",
        ".txt": "text",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".pdf": "pdf",
        ".xlsx": "excel",
        ".xls": "excel",
    }

    # 浏览器可打开的文件类型
    BROWSER_OPENABLE = {"html", "json", "txt"}

    # ==================== 数据库配置 ====================

    # 是否启用数据库写入
    # True: 所有生成的文件都会写入数据库
    # False: 只生成物理文件，不写入数据库（轻量化模式）
    ENABLE_DB_WRITE: bool = True

    # 批量入库的批次大小
    BATCH_SIZE: int = 100

    # ==================== 文件保留策略 ====================

    # 文件保留时间（小时）
    FILE_RETENTION_HOURS: int = 24

    # 最大文件数量（每次执行）
    MAX_FILES_PER_EXECUTION: int = 100

    # 软删除文件保留时间（天）
    SOFT_DELETE_RETENTION_DAYS: int = 7

    # 执行记录保留时间（天）
    EXECUTION_RETENTION_DAYS: int = 30

    # ==================== 清理任务配置 ====================

    # 清理任务执行间隔（小时）
    CLEANUP_INTERVAL_HOURS: int = 1

    # ==================== 类方法 ====================

    @classmethod
    def set_enable_db_write(cls, enable: bool):
        """
        设置是否启用数据库写入

        Args:
            enable: True 启用，False 禁用
        """
        cls.ENABLE_DB_WRITE = enable

    @classmethod
    def set_batch_size(cls, size: int):
        """
        设置批量入库的批次大小

        Args:
            size: 批次大小
        """
        cls.BATCH_SIZE = size

    @classmethod
    def set_file_retention_hours(cls, hours: int):
        """
        设置文件保留时间

        Args:
            hours: 保留小时数
        """
        cls.FILE_RETENTION_HOURS = hours

    @classmethod
    def set_cleanup_interval(cls, hours: int):
        """
        设置清理任务执行间隔

        Args:
            hours: 间隔小时数
        """
        cls.CLEANUP_INTERVAL_HOURS = hours

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        获取当前配置

        Returns:
            配置字典
        """
        return {
            "output_dir": str(cls.OUTPUT_DIR),
            "temp_dir": str(cls.TEMP_DIR),
            "enable_db_write": cls.ENABLE_DB_WRITE,
            "batch_size": cls.BATCH_SIZE,
            "file_retention_hours": cls.FILE_RETENTION_HOURS,
            "max_files_per_execution": cls.MAX_FILES_PER_EXECUTION,
            "soft_delete_retention_days": cls.SOFT_DELETE_RETENTION_DAYS,
            "execution_retention_days": cls.EXECUTION_RETENTION_DAYS,
            "cleanup_interval_hours": cls.CLEANUP_INTERVAL_HOURS,
        }

    @classmethod
    def init_directories(cls):
        """
        初始化必要的目录
        """
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)


# 全局配置实例
settings = NodeSettings()

# 初始化目录
settings.init_directories()
