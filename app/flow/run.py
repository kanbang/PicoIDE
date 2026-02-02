"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-12 18:26:54
LastEditors: zhai
LastEditTime: 2026-01-20 17:54:25
"""

from flow.demo_blocks import DEMO_BLOCKS
from db import Output
from flow.engine import ComputeEngine
from flow.block import Block, BaseBlock
from flow.engine_manager import EngineManager, async_start_flow, register_business_blocks
from flow.blocks_manager import blocks_registry
from typing import Any, List
from flow.output import output_file_manager
from flow.collector import file_collector
from flow.setting import settings
import uuid

def make_dynamic_engine(blocks: List[Block], scripts: List[str]):
    """创建动态引擎（已废弃，建议直接使用 register_business）"""
    script_blocks = blocks_registry._build_blocks_from_scripts(scripts)
    script_blocks.extend(blocks)
    engine_instance = ComputeEngine()
    engine_instance.set_blocks(script_blocks)
    return engine_instance


def get_dynamic_blocks_json(blocks: List[Block], scripts: List[str] = None):
    """获取所有 blocks 的 JSON 配置"""
    script_blocks = blocks_registry._build_blocks_from_scripts(scripts)
    script_blocks.extend(blocks)
    return [b().export_config() for b in script_blocks]


def get_business_blocks_json(business: str, scripts: List[str] = None):
    """获取业务对应的所有 blocks 的 JSON 配置"""
    all_blocks = blocks_registry.get_blocks_with_scripts(business, scripts)
    return [b().export_config() for b in all_blocks]


async def register_engine(business: str, scripts: List[str] = None):
    """
    注册业务对应的 Block 模板

    Args:
        business: 业务标识
        blocks: Block 模板列表（已废弃，建议直接使用 business 参数）
        scripts: 可选的脚本列表（动态定义 Block）
    """
    # 使用 BlocksRegistry 获取静态和动态 blocks
    all_blocks = blocks_registry.get_blocks_with_scripts(business, scripts)
    await register_business_blocks(business, all_blocks)


def create_execution_id() -> str:
    """
    创建新的执行ID

    Returns:
        执行ID
    """
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    return execution_id


async def run_business(business: str, flow: dict, execution_id: str = None, user_id: str = "default"):
    """
    执行 flow

    Args:
        business: 业务标识
        scripts: 脚本列表
        flow: flow 配置
        execution_id: 执行ID（用于文件追踪）
    """

    # 创建执行ID（如果未提供）
    if execution_id is None:
        execution_id = create_execution_id()

    await async_start_flow(business, flow, execution_id, user_id)

    # 文件入库已移至 flow 执行完成时的回调中自动处理（engine_manager._on_execution_done）
    # 这样确保在文件产生后才入库，避免在 flow 执行期间就尝试入库

    return execution_id




# 注册业务：Demo（包含所有内置节点）
# register_engine("DEMO", [])  # 示例调用需在异步上下文中使用 await register_engine("DEMO", [])