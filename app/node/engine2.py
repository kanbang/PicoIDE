from flow import Block, ComputeEngine
from flow2.block.prepare import prepare_blocks_export
from node.blocks_daq import daq_blocks
from typing import List


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


def make_dynamic_engine(scripts: List[str]):
    base_blocks = daq_blocks.copy()

    script_blocks = _build_blocks(scripts)
    base_blocks.extend(script_blocks)

    engine_instance = ComputeEngine(base_blocks)
    return engine_instance


def get_json_blocks(scripts: List[str]):
    base_blocks = daq_blocks.copy()
    script_blocks = _build_blocks(scripts)
    base_blocks.extend(script_blocks)
    blocks = prepare_blocks_export(base_blocks)
    return blocks
