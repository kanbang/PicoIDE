'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-12 18:26:54
LastEditors: zhai
LastEditTime: 2026-01-19 19:14:03
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

async def run_flow(scripts: List[Any], flow: dict, execution_id: str = None):
    """
    执行 flow

    Args:
        scripts: 脚本列表
        flow: flow 配置
        execution_id: 执行ID（用于文件追踪）
    """
    # 导入 output_file_manager
    from node.output_manager import output_file_manager
    from node.file_collector import file_collector

    # 创建执行ID（如果未提供）
    if execution_id is None:
        execution_id = output_file_manager.create_execution_id()

    # 执行流程，传递 execution_id（使用异步执行）
    async with await engine_manager.acquire("daq", flow) as engine:
        await engine.async_run(execution_id)

    # 执行完成后，批量将文件信息写入数据库
    await _batch_save_outputs(execution_id)

    return execution_id


async def _batch_save_outputs(execution_id: str):
    """
    批量保存输出文件到数据库

    Args:
        execution_id: 执行ID
    """
    from node.file_collector import file_collector
    from db import Output

    # 获取该执行的所有文件信息
    files = file_collector.get_files(execution_id)

    if not files:
        return

    # 批量插入数据库（使用切片方式，每次插入100条）
    batch_size = 100
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]

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
    # engine = ComputeEngine()
    # engine.register_blocks(base_blocks)
    # engine.set_flow(flow)
    # engine.run()
    # await engine.async_run()