'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-19 21:04:47
LastEditors: zhai
LastEditTime: 2026-01-19 21:06:34
'''
"""
Node 模块 - 统一的节点管理

提供：
- settings: 全局配置
- output_file_manager: 输出文件管理器
- file_collector: 文件信息收集器
- config: 配置接口（兼容旧代码）
"""

from node.settings import settings
from node.output_manager import output_file_manager
from node.file_collector import file_collector

__all__ = [
    "settings",
    "output_file_manager",
    "file_collector",
]