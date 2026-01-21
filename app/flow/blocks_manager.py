"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-20 21:07:02
LastEditors: zhai
LastEditTime: 2026-01-21 14:10:07
"""

"""
Block 模板注册表

功能：
- 管理不同业务类型对应的静态 Block 模板
- 根据 business 名称获取对应的 Block 定义
- 提供 Block 的 JSON 配置
"""
from typing import Dict, List, Any
import logging

from flow.block import BaseBlock
from node.daq import DAQ_BLOCKS
from flow.demo_blocks import DEMO_BLOCKS

logger = logging.getLogger(__name__)


# ==================== Block 模板注册表 ====================

STATIC_BLOCKS_MAP: Dict[str, list[type[BaseBlock]]] = {
    "DEMO": DEMO_BLOCKS,
}


# ==================== BlocksRegistry 类 ====================

class BlocksRegistry:
    """
    Block 模板注册表

    职责：
    - 管理静态预定义的 Block 模板
    - 提供按业务类型查询 Block 的接口
    - 不负责动态加载，不负责执行引擎注册
    """

    def __init__(self):
        self._blocks_map: Dict[str, list[type[BaseBlock]]] = STATIC_BLOCKS_MAP.copy()
        logger.info(
            f"Block 注册表初始化完成，已注册 {len(self._blocks_map)} 个业务类型: {list(self._blocks_map.keys())}"
        )

    def get_blocks(self, business: str) -> list[type[BaseBlock]]:
        """
        获取指定业务类型的 Block 模板

        Args:
            business: 业务类型名称（不区分大小写）

        Returns:
            Block 模板列表

        Raises:
            KeyError: 当业务类型未注册时

        Example:
            ```python
            registry = BlocksRegistry()
            blocks = registry.get_blocks("WAVE")
            ```
        """
        business_key = business.upper()

        if business_key not in self._blocks_map:
            available = list(self._blocks_map.keys())
            logger.warning(f"未注册的业务类型: {business}，可用类型: {available}")
            raise KeyError(f"业务类型 '{business}' 未注册，可用类型: {available}")

        return self._blocks_map[business_key]

    def register(self, business: str, blocks: list[type[BaseBlock]]) -> None:
        """
        注册新的业务类型及其 Block 模板

        Args:
            business: 业务类型名称
            blocks: Block 模板列表

        Example:
            ```python
            registry = BlocksRegistry()
            registry.register("CUSTOM", custom_blocks)
            ```
        """
        business_key = business.upper()
        self._blocks_map[business_key] = blocks
        logger.info(f"已注册业务类型: {business}")

    def has_business(self, business: str) -> bool:
        """
        检查业务类型是否已注册

        Args:
            business: 业务类型名称

        Returns:
            bool: 是否已注册
        """
        return business.upper() in self._blocks_map

    def list_businesses(self) -> List[str]:
        """
        获取所有已注册的业务类型

        Returns:
            业务类型列表
        """
        return list(self._blocks_map.keys())


# ==================== 全局实例 ====================

blocks_registry = BlocksRegistry()


# ==================== 便捷函数 ====================


def get_static_blocks(business: str) -> Any:
    """
    获取指定业务类型的静态 Block 模板（便捷函数）

    Args:
        business: 业务类型名称

    Returns:
        Block 模板列表

    Example:
        ```python
        blocks = get_static_blocks("WAVE")
        ```
    """
    return blocks_registry.get_blocks(business)


def register_static_blocks(business: str, blocks: Any) -> None:
    """
    注册新的业务类型（便捷函数）

    Args:
        business: 业务类型名称
        blocks: Block 模板列表

    Example:
        ```python
        register_static_blocks("CUSTOM", custom_blocks)
        ```
    """
    blocks_registry.register(business, blocks)

