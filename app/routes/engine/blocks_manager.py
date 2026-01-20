"""
Business 与 Blocks 映射管理模块

功能：
- 管理不同业务类型对应的 Block 模板
- 根据 business 名称获取对应的 blocks
- 支持动态注册新的业务类型
"""
from typing import Dict, List, Any, Callable, Optional
import logging

from node.daq import DAQ_BLOCKS
from flow.demo_blocks import DEMO_BLOCKS

logger = logging.getLogger(__name__)


# ==================== Business-Blocks 映射 ====================

# 业务类型到 Block 模块的映射
BUSINESS_BLOCKS_MAP: Dict[str, Any] = {
    "WAVE": DAQ_BLOCKS,
    "DEMO": DEMO_BLOCKS,
}

# 业务类型到模块路径的映射（用于动态加载）
BUSINESS_MODULE_MAP: Dict[str, str] = {
    "WAVE": "node.daq.DAQ_BLOCKS",
    "DEMO": "flow.demo_blocks.DEMO_BLOCKS",
}


# ==================== 业务管理器 ====================

class BlocksManager:
    """业务管理器 - 管理业务类型与 Block 模块的映射"""
    
    def __init__(self):
        self._blocks_map: Dict[str, Any] = BUSINESS_BLOCKS_MAP.copy()
        self._module_map: Dict[str, str] = BUSINESS_MODULE_MAP.copy()
        logger.info(f"业务管理器初始化完成，已注册 {len(self._blocks_map)} 个业务类型: {list(self._blocks_map.keys())}")
    
    def get_blocks(self, business: str) -> Any:
        """
        获取指定业务类型的 Block 模板
        
        Args:
            business: 业务类型名称
            
        Returns:
            Block 模板字典
            
        Raises:
            KeyError: 当业务类型未注册时
            
        Example:
            ```python
            manager = BusinessManager()
            blocks = manager.get_blocks("daq")
            ```
        """
        # 转换为小写，支持大小写不敏感
        business_key = business.lower()
        
        if business_key not in self._blocks_map:
            logger.warning(f"未注册的业务类型: {business}，可用类型: {list(self._blocks_map.keys())}")
            # 尝试动态加载
            return self._load_blocks_dynamic(business_key)
        
        return self._blocks_map[business_key]
    
    def register_blocks(self, business: str, blocks: Any, module_path: Optional[str] = None) -> None:
        """
        注册新的业务类型
        
        Args:
            business: 业务类型名称
            blocks: Block 模板
            module_path: 模块路径（可选，用于动态加载）
            
        Example:
            ```python
            manager = BusinessManager()
            manager.register_business("custom", custom_blocks, "my_module.blocks")
            ```
        """
        business_key = business.lower()
        self._blocks_map[business_key] = blocks
        if module_path:
            self._module_map[business_key] = module_path
        logger.info(f"已注册业务类型: {business}")
    
    def has_business(self, business: str) -> bool:
        """
        检查业务类型是否已注册
        
        Args:
            business: 业务类型名称
            
        Returns:
            bool: 是否已注册
        """
        return business.lower() in self._blocks_map
    
    def list_businesses(self) -> List[str]:
        """
        获取所有已注册的业务类型
        
        Returns:
            业务类型列表
        """
        return list(self._blocks_map.keys())
    
    def _load_blocks_dynamic(self, business: str) -> Any:
        """
        动态加载 Block 模块
        
        Args:
            business: 业务类型名称
            
        Returns:
            Block 模板字典
            
        Raises:
            KeyError: 当业务类型未注册且无法动态加载时
        """
        if business not in self._module_map:
            raise KeyError(f"未注册的业务类型: {business}")
        
        module_path = self._module_map[business]
        logger.info(f"动态加载业务模块: {module_path}")
        
        # 动态导入
        module_parts = module_path.split('.')
        module = __import__(module_path)
        for part in module_parts[1:]:
            module = getattr(module, part)
        
        blocks = getattr(module, module_parts[-1].upper())
        
        # 缓存到映射表
        self._blocks_map[business] = blocks
        
        return blocks


# ==================== 全局实例 ====================

blocks_manager = BlocksManager()


# ==================== 便捷函数 ====================

def get_blocks_for_business(business: str) -> Any:
    """
    获取指定业务类型的 Block 模板（便捷函数）
    
    Args:
        business: 业务类型名称
        
    Returns:
        Block 模板字典
        
    Example:
        ```python
        blocks = get_blocks_for_business("daq")
        ```
    """
    return blocks_manager.get_blocks(business)


def register_blocks_by_business(business: str, blocks: Any, module_path: Optional[str] = None) -> None:
    """
    注册新的业务类型（便捷函数）
    
    Args:
        business: 业务类型名称
        blocks: Block 模板
        module_path: 模块路径（可选）
        
    Example:
        ```python
        register_blocks("custom", custom_blocks, "my_module.blocks")
        ```
    """
    blocks_manager.register_blocks(business, blocks, module_path)


register_blocks_by_business("WAVE", DAQ_BLOCKS, "node.daq.DAQ_BLOCKS")
register_blocks_by_business("DEMO", DEMO_BLOCKS, "flow.demo_blocks.DEMO_BLOCKS")