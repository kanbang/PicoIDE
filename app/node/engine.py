from flow import Block, ComputeEngine, prepare_blocks_export
from node.blocks_daq import daq_blocks
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

    return prepare_blocks_export(base_blocks)



async def run_schema(scripts: List[Any], schema: dict):
    base_blocks = daq_blocks.copy()

    script_blocks = _build_blocks(scripts)
    base_blocks.extend(script_blocks)

    engine = ComputeEngine()
    engine.register_blocks(base_blocks)
    engine.set_schema(schema)
    engine.run()
    await engine.async_run()



# -------------------------------------------------------------------------
# Mock 外部依赖 (确保代码可运行)
# -------------------------------------------------------------------------
class MockAdlinkBridge:
    def get_channel_data(self, channel_id):
        # 模拟耗时操作，以便观察并行效果
        return [float(i + channel_id) for i in range(100)]

    def add_data_t(self, data):
        print(f"💾 [Storage] 保存时域: {data['name']}")

    def add_data_p(self, data):
        print(f"💾 [Storage] 保存频域: {data['name']}")

    def add_data_xy(self, data):
        print(f"💾 [Storage] 保存XY: {data['name']}")


adlink_bridge_instance = MockAdlinkBridge()


def fourier_transform(data):
    return [x * 0.1 for x in data]


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
