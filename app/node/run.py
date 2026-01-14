'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-12 18:26:54
LastEditors: zhai
LastEditTime: 2026-01-14 14:43:13
'''
from flow.engine import Block, ComputeEngine
from flow.manager import EngineManager
from node.daq import daq_blocks
from typing import Any, List


def _build_blocks(scripts: List[str]):
    blocks = []
    for script in scripts:
        if script is None or script.strip() == "":
            continue
        try:
            # 创建独立的局部命名空间，并将需要的类和函数传递进去
            namespace = {"Block": Block}

            # 在局部命名空间中执行脚本
            exec(script, namespace)

            # 从命名空间中获取创建的对象
            block = namespace.get("block")
            if block:
                blocks.append(block)
        except Exception as e:
            print(f"Error executing block script: {str(e)}")

    return blocks


def get_blocks(scripts: List[str]):
    script_blocks = _build_blocks(scripts)
    script_blocks.extend(daq_blocks)
    return script_blocks

def make_dynamic_engine(scripts: List[str]):
    script_blocks = get_blocks(scripts)
    engine_instance = ComputeEngine(script_blocks)
    return engine_instance


def get_json_blocks(scripts: List[str]):
    script_blocks = get_blocks(scripts)
    return [b.export_config() for b in script_blocks]


engine_manager = EngineManager(pool_size=5)

# 注册业务：振动分析业务
engine_manager.register_business("daq" , daq_blocks)


async def run_schema(scripts: List[Any], schema: dict):
    base_blocks = daq_blocks.copy()

    script_blocks = _build_blocks(scripts)
    base_blocks.extend(script_blocks)


    async with await engine_manager.acquire("daq", schema) as engine:
        await engine.async_run()

    with engine_manager.acquire_sync("daq", schema) as engine:
        engine.run()

    # engine = ComputeEngine()
    # engine.register_blocks(base_blocks)
    # engine.set_schema(schema)
    # engine.run()
    # await engine.async_run()

