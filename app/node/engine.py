from flow.compute import Block, ComputeEngine
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

    engine = ComputeEngine()
    engine.register_blocks(base_blocks  )

    blocks_def_json = engine.export_all_blocks()
    return blocks_def_json

    # return prepare_blocks_export(base_blocks)



async def run_schema(scripts: List[Any], schema: dict):
    base_blocks = daq_blocks.copy()

    script_blocks = _build_blocks(scripts)
    base_blocks.extend(script_blocks)

    engine = ComputeEngine()
    engine.register_blocks(base_blocks)
    engine.set_schema(schema)
    engine.run()
    await engine.async_run()



class BlockEngine:
    instance = None

    @classmethod
    def init_none(cls):
        cls.instance = None

    @classmethod
    def make_engine(cls, scripts: List[str]):
        cls.instance = make_dynamic_engine(scripts)

    @classmethod
    def init_schemas(cls, schemas):
        cls.instance.init_engine(schemas)

    @classmethod
    def execute(cls):
        ce = cls.instance.execute()
        return ce.get_result()
