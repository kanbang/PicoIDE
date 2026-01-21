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
from flow.engine_manager import EngineManager
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

engine_manager = EngineManager(pool_size=5)


def register_engine(business: str, scripts: List[str] = None):
    """
    注册业务对应的 Block 模板

    Args:
        business: 业务标识
        blocks: Block 模板列表（已废弃，建议直接使用 business 参数）
        scripts: 可选的脚本列表（动态定义 Block）
    """
    # 使用 BlocksRegistry 获取静态和动态 blocks
    all_blocks = blocks_registry.get_blocks_with_scripts(business, scripts)
    engine_manager.register_business(business, all_blocks)


def create_execution_id() -> str:
    """
    创建新的执行ID

    Returns:
        执行ID
    """
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    return execution_id


async def run_business(business: str, flow: dict, execution_id: str = None):
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

    async with await engine_manager.acquire(business, flow) as engine:
        await engine.start(execution_id)

    # 执行流程，传递 execution_id（使用异步执行）
    # async with await engine_manager.acquire(business, flow) as engine:
    #     await engine.async_run(execution_id)

    # 使用同步执行版本
    # with engine_manager.acquire_sync(business, flow) as engine:
    #     engine.run(execution_id)

    # 执行完成后，批量将文件信息写入数据库
    await _batch_save_outputs(execution_id)

    return execution_id


async def _batch_save_outputs(execution_id: str):
    """
    批量保存输出文件到数据库

    Args:
        execution_id: 执行ID
    """

    # 只在启用数据库时才执行批量入库
    if not settings.ENABLE_DB_WRITE:
        return

    # 获取该执行的所有文件信息
    files = file_collector.get_files(execution_id)

    if not files:
        return

    # 批量插入数据库（使用切片方式，每次插入配置的批次大小）
    batch_size = settings.BATCH_SIZE
    for i in range(0, len(files), batch_size):
        batch = files[i : i + batch_size]

        # 创建 Output 对象
        output_objects = [
            Output(
                file_id=f["file_id"],
                execution_id=f["execution_id"],
                filename=f["filename"],
                file_path=f["file_path"],
                file_type=f["file_type"],
                file_size=f["file_size"],
                block_name=f["block_name"],
                block_id=f["block_id"],
                description=f.get("description"),
                metadata=f.get("metadata"),
                is_deleted=False,
            )
            for f in batch
        ]

        # 批量插入
        await Output.bulk_create(output_objects)

    # 清除收集器中的数据
    file_collector.clear_execution(execution_id)


# 注册业务：Demo（包含所有内置节点）
# register_engine("DEMO", [])