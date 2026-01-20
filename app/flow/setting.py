"""
节点全局配置 - 使用 pydantic-settings 实现

优势：
- 自动支持环境变量加载（字段名自动映射为大写环境变量）
- 支持 .env 文件加载
- 支持类型校验和默认值
- 配置不可变（工业级推荐，避免运行时随意修改导致状态不一致）
- 自动 Path 类型转换
"""

import logging
from pathlib import Path
from typing import Dict, Set

from pydantic_settings import BaseSettings, SettingsConfigDict


class NodeSettings(BaseSettings):
    """
    全局配置类（基于 pydantic-settings）

    环境变量加载规则：
    - 字段名会自动转换为大写作为环境变量名（例如 ENABLE_DB_WRITE）
    - 可选前缀：如果需要避免冲突，可在 model_config 中设置 env_prefix='FLOW_'
    - 支持 .env 文件（放在项目根目录）
    - 复杂类型（如 dict/set）不从环境变量加载，仅使用默认值（避免解析复杂性）
    """

    model_config = SettingsConfigDict(
        env_file=".env",          # 自动加载项目根目录的 .env 文件（可选）
        env_prefix="",            # 如需前缀可改为 "FLOW_"，则环境变量为 FLOW_OUTPUT_DIR
        case_sensitive=False,     # 环境变量不区分大小写
        extra="ignore",           # 忽略未知环境变量
    )

    # ==================== 日志配置 ====================
    LOG_LEVEL: int = logging.INFO
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ==================== 文件输出配置 ====================
    OUTPUT_DIR: Path = Path("./output")
    TEMP_DIR: Path = Path("./temp")

    FILE_TYPE_MAP: Dict[str, str] = {
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

    BROWSER_OPENABLE: Set[str] = {"html", "json", "txt"}

    # ==================== 数据库与清理配置 ====================
    ENABLE_DB_WRITE: bool = True
    BATCH_SIZE: int = 100

    FILE_RETENTION_HOURS: int = 24
    MAX_FILES_PER_EXECUTION: int = 100
    SOFT_DELETE_RETENTION_DAYS: int = 7
    EXECUTION_RETENTION_DAYS: int = 30

    CLEANUP_INTERVAL_HOURS: int = 1

# ==================== 全局单例实例 ====================
settings = NodeSettings()

# ==================== 初始化目录（实例化后立即执行） ====================
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)