"""
工具函数模块
"""
import hashlib
from typing import List


def calculate_scripts_hash(scripts: List[str]) -> str:
    """
    计算脚本列表的哈希值

    Args:
        scripts: 脚本内容列表

    Returns:
        MD5 哈希值
    """
    # 排序以确保顺序不影响哈希
    sorted_scripts = sorted(scripts)

    # 拼接所有脚本内容
    combined = "\n".join(sorted_scripts)

    # 计算 MD5
    return hashlib.md5(combined.encode()).hexdigest()