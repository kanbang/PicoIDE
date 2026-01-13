# from .component import st_barfi as st_barfi, barfi_schemas as barfi_schemas
from .block_builder import Block as Block
from .compute_engine import ComputeEngine as ComputeEngine
from .manage_schema import (
    load_schema_name as load_schema_name,
    load_schemas as load_schemas,
    save_schema as save_schema,
)
from .manage_schema import editor_preset as editor_preset
from typing import List, Dict, Union


class NodeEngine():
    def __init__(self, base_blocks: Union[List[Block], Dict]):
        self.ce = None
        if isinstance(base_blocks, List):
            self.base_blocks_data = [block._export() for block in base_blocks]
            self.base_blocks_list = base_blocks
        elif isinstance(base_blocks, Dict):
            self.base_blocks_data = []
            self.base_blocks_list = []
            for category, block_list in base_blocks.items():
                if isinstance(block_list, List):
                    for block in block_list:
                        self.base_blocks_list.append(block)
                        block_data = block._export()
                        block_data['category'] = category
                        self.base_blocks_data.append(block_data)
                else:
                    raise TypeError(
                        'Invalid type for base_blocks passed to the st_barfi component.')
        else:
            raise TypeError(
                'Invalid type for base_blocks passed to the st_barfi component.')
        

    def base_blocks(self):
        return self.base_blocks_data
    
    def execute_engine(self, schemas)->ComputeEngine:
        ce = ComputeEngine(blocks=self.base_blocks_list)
        ce.add_editor_state(schemas)
        ce._map_block_link()
        ce.execute()
        return ce

    def init_engine(self, schemas)->ComputeEngine:
        self.ce = ComputeEngine(blocks=self.base_blocks_list)
        self.ce.add_editor_state(schemas)
        self.ce._map_block_link()
        return self.ce
    
    def execute(self)->ComputeEngine:
        if self.ce:
            self.ce._execute_compute()
        return self.ce

