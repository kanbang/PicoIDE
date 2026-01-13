'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-13 16:08:06
LastEditors: zhai
LastEditTime: 2026-01-13 16:19:20
'''
from typing import Union, List, Dict
from flow.block import Block


def prepare_blocks_export(
    base_blocks: Union[List[Block], Dict[str, List[Block]]],
):
    if isinstance(base_blocks, List):
        names = [block.name for block in base_blocks]
        duplicate_names = {name for name in names if names.count(name) > 1}
        if duplicate_names:
            raise ValueError(f"Duplicate blocks found: {duplicate_names}")

        base_blocks_data = [block._export() for block in base_blocks]
    elif isinstance(base_blocks, Dict):
        for category, blocks in base_blocks.items():
            names = [block.name for block in blocks]
            duplicate_names = {name for name in names if names.count(name) > 1}
            if duplicate_names:
                raise ValueError(
                    f"Duplicate blocks found in category '{category}': {duplicate_names}"
                )

        base_blocks_data = {
            category: [block._export() for block in blocks]
            for category, blocks in base_blocks.items()
        }

    return base_blocks_data
