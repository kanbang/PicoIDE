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
- 从脚本动态构建 Block
- 提供 Block 的 JSON 配置
"""
from typing import Dict, List, Any
import logging
import inspect
import numpy as np

from flow.block import Block, BaseBlock
from node.daq import DAQ_BLOCKS
from flow.demo_blocks import DEMO_BLOCKS
from utils.singleton import singleton

logger = logging.getLogger(__name__)


# ==================== Block 模板注册表 ====================

STATIC_BLOCKS_MAP: Dict[str, list[type[BaseBlock]]] = {
    "DEMO": DEMO_BLOCKS,
}



def build_blocks_from_scripts(scripts: List[str] = None) -> List[type[Block]]:
    """
    从脚本动态构建 Block

    Args:
        scripts: Python 脚本列表

    Returns:
        动态构建的 Block 类列表
    """
    blocks = []
    if not scripts:
        return blocks

    for script in scripts:
        if not script or not script.strip():
            continue

        try:
            # 1. 准备命名空间，注入必要的依赖
            namespace = {"Block": Block, "BaseBlock": BaseBlock, "np": np}

            # 2. 执行脚本
            exec(script, namespace)

            # 3. 智能发现：遍历命名空间，找到所有 BaseBlock 的子类
            for name, obj in namespace.items():
                # 排除 BaseBlock 基类本身，只找子类
                if inspect.isclass(obj) and issubclass(obj, Block) and obj is not Block and obj is not BaseBlock:
                    blocks.append(obj)
                    logger.info(f"成功动态加载节点: {obj.NAME}")

        except Exception as e:
            logger.error(f"执行脚本失败: {str(e)}")

    return blocks
# ==================== BlocksRegistry 类 ====================

@singleton
class BlocksRegistry:
    """
    Block 模板注册表（单例模式）

    职责：
    - 管理静态预定义的 Block 模板
    - 从脚本动态构建 Block
    - 提供按业务类型查询 Block 的接口
    - 提供合并静态和动态 Block 的接口
    """

    def __init__(self):
        self._blocks_map: Dict[str, list[type[BaseBlock]]] = STATIC_BLOCKS_MAP.copy()
        logger.info(
            f"Block 注册表初始化完成，已注册 {len(self._blocks_map)} 个业务类型: {list(self._blocks_map.keys())}"
        )

    def get_blocks(self, business: str) -> list[type[BaseBlock]]:
        """
        获取指定业务类型的静态 Block 模板

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

    def get_blocks_with_scripts(
        self, business: str, scripts: List[str] = None
    ) -> List[type[Block]]:
        """
        获取指定业务类型的 Block 模板（包含静态和动态）

        Args:
            business: 业务类型名称
            scripts: 可选的脚本列表

        Returns:
            合并后的 Block 列表（静态 + 动态）

        Example:
            ```python
            registry = BlocksRegistry()
            all_blocks = registry.get_blocks_with_scripts("WAVE", scripts)
            ```
        """
        # 获取静态 blocks
        static_blocks = self.get_blocks(business)

        # 构建动态 blocks
        dynamic_blocks = build_blocks_from_scripts(scripts)

        # 合并（动态 blocks 优先）
        return dynamic_blocks + static_blocks


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

