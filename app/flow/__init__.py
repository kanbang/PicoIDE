'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-12 18:16:30
LastEditors: zhai
LastEditTime: 2026-02-03 11:31:50
'''
from flow.block import Block as Block
from flow.engine import ComputeEngine as ComputeEngine
from flow.engine_manager import EngineManager as EngineManager
from flow.collector import FileCollector as FileCollector
from flow.setting import settings as settings
from flow.blocks_manager import blocks_registry, register_static_blocks
from typing import Dict, List, Type, Optional, Callable, Awaitable, Any
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

async def register_business_engine(business: str, scripts: Optional[List[str]] = None):
    """
    注册业务对应的块模板到引擎管理器。

    Args:
        business: 业务标识。
        scripts: 可选脚本列表，用于动态构建块。
    """
    all_blocks = blocks_registry.get_blocks_with_scripts(business, scripts or [])
    manager = get_engine_manager()
    await manager.register_business(business, all_blocks)


def create_execution_id() -> str:
    """
    创建新的执行ID

    Returns:
        执行ID
    """
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    return execution_id


# 全局辅助函数，便于使用（仅异步版本）
def get_engine_manager() -> EngineManager:
    """获取引擎管理器单例实例。"""
    return EngineManager()


async def async_acquire_flow_engine(business_id: str, flow: Dict) -> ComputeEngine:
    """异步获取预编译的流引擎。"""
    manager = get_engine_manager()
    return await manager.acquire(business_id, flow)


async def async_run_existing_flow(
    engine: ComputeEngine,
    business_id: str,
    execution_id: str,
    user_id: str,
    on_done: Optional[Callable[[Any], Awaitable[None]]] = None,
):
    """异步在现有引擎上运行执行。"""
    manager = get_engine_manager()
    await manager.run_existing(engine, business_id, execution_id, user_id, on_done)


async def async_start_flow(
    business_id: str,
    flow: Dict,
    execution_id: str,
    user_id: str,
    on_done: Optional[Callable[[Any], Awaitable[None]]] = None,
):
    """异步启动流执行。"""
    manager = get_engine_manager()
    await manager.start_execution(business_id, flow, execution_id, user_id, on_done)


async def async_stop_flow(execution_id: str, business: Optional[str] = None) -> bool:
    """异步停止流执行。"""
    manager = get_engine_manager()
    return await manager.stop_execution(execution_id, business)


async def get_running_flows(business: Optional[str] = None) -> List[str]:
    """获取运行中的流ID列表。"""
    manager = get_engine_manager()
    return await manager.get_running_executions(business)