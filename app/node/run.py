'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-12 18:26:54
LastEditors: zhai
LastEditTime: 2026-01-14 16:35:22
'''
from flow.engine import Block, ComputeEngine
from flow.manager import EngineManager
from node.daq import daq_blocks
from typing import Any, List
import inspect
import numpy as np

def _build_blocks(scripts: List[str] = None) -> List[Block]:
    blocks = []
    if not scripts:
        return blocks
    
    for script in scripts:
        if not script or not script.strip():
            continue
            
        try:
            # 1. 准备命名空间，注入必要的依赖
            # 注意：如果脚本里用了 np，这里必须注入，或者让脚本自己 import
            namespace = {"Block": Block, "np": np} 

            # 2. 执行脚本
            exec(script, namespace)

            # 3. 智能发现：遍历命名空间，找到所有 Block 的子类并实例化
            for name, obj in namespace.items():
                # 排除 Block 基类本身，只找子类
                if inspect.isclass(obj) and issubclass(obj, Block) and obj is not Block:
                    instance = obj() # 实例化
                    blocks.append(instance)
                    print(f"成功动态加载节点: {instance.name}")

        except Exception as e:
            print(f"❌ 执行脚本失败: {str(e)}")

    return blocks


def get_blocks(scripts: List[str] = None):
    """获取所有 blocks，包括从数据库动态加载的"""
    # 构建所有 blocks
    script_blocks = _build_blocks(scripts)
    script_blocks.extend(daq_blocks)
    return script_blocks


def make_dynamic_engine(scripts: List[str]):
    script_blocks = _build_blocks(scripts)
    script_blocks.extend(daq_blocks)
    engine_instance = ComputeEngine()
    engine_instance.register_blocks(script_blocks)
    return engine_instance


def get_json_blocks(scripts: List[str] = None):
    """获取所有 blocks 的 JSON 配置"""
    script_blocks = get_blocks(scripts)
    return [b.export_config() for b in script_blocks]



engine_manager = EngineManager(pool_size=5)

# 注册业务：振动分析业务
engine_manager.register_business("daq", daq_blocks)

async def run_schema(scripts: List[Any], schema: dict, execution_id: str = None):
    """
    执行 schema
    
    Args:
        scripts: 脚本列表
        schema: schema 配置
        execution_id: 执行ID（用于文件追踪）
    """
    # 导入 output_file_manager
    from node.output_manager import output_file_manager
    from node.daq import BaseBlock
    
    # 创建执行ID（如果未提供）
    if execution_id is None:
        execution_id = output_file_manager.create_execution_id()
    
    # 设置所有 Block 的 execution_id
    async with await engine_manager.acquire("daq", schema) as engine:
        # 为所有 Block 设置 execution_id
        for block in engine.blocks:
            if isinstance(block, BaseBlock):
                block.set_execution_id(execution_id)
        await engine.async_run()

    with engine_manager.acquire_sync("daq", schema) as engine:
        # 为所有 Block 设置 execution_id
        for block in engine.blocks:
            if isinstance(block, BaseBlock):
                block.set_execution_id(execution_id)
        engine.run()
    
    return execution_id
    # engine = ComputeEngine()
    # engine.register_blocks(base_blocks)
    # engine.set_schema(schema)
    # engine.run()
    # await engine.async_run()