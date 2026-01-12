'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-12 19:36:16
LastEditors: zhai
LastEditTime: 2026-01-12 23:19:42
'''
"""
Blocks 路由
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from node.engine import make_dynamic_engine, get_json_blocks
from services import read_file, normalize_path
from flow.schema import build_flow_schema_from_dict

USER_ID = "default"

router = APIRouter(prefix="/api/flow", tags=["blocks"])


class ExecuteRequest(BaseModel):
    scripts: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None


@router.get("/blocks")
async def get_blocks():
    """
    获取所有可用的 blocks 定义
    """
    try:
        # 从文件系统读取所有 .py 脚本文件
        blocks = get_json_blocks([])
        return {"blocks": blocks}
    except Exception as e:
        raise HTTPException(500, f"Failed to get blocks: {str(e)}")



from collections import defaultdict

def convert_schema(data):
    editor_schema = {
        "version": "1.0",
        "nodes": [],
        "connections": [],
        "viewport": {
            "x": 0,
            "y": 0,
            "zoom": 1.0
        }
    }

    nodes_list = data["nodes"]
    type_counter = defaultdict(int)

    # 用于映射 port_id -> (node_id, interface_name, direction)
    port_map = {}

    for node in nodes_list:
        node_id = node["id"]
        node_type = node["type"]
        type_counter[node_type] += 1
        label = f"{node_type}-{type_counter[node_type]}"
        name = node_type  # source 中 title 和 type 相同，可改为 node.get("title", node_type)

        # inputs
        inputs = []
        for in_key in node.get("inputs", {}):
            inputs.append({"name": in_key, "itype": "typing.Any"})
            port_id = node["inputs"][in_key]["id"]
            port_map[port_id] = (node_id, in_key, "input")

        # outputs
        outputs = []
        for out_key in node.get("outputs", {}):
            outputs.append({"name": out_key, "itype": "typing.Any"})
            port_id = node["outputs"][out_key]["id"]
            port_map[port_id] = (node_id, out_key, "output")

        # options
        options = [
            {"name": "display-option", "value": f"This is a Block with {node_type} option."}
        ]
        for in_key, in_dict in node.get("inputs", {}).items():
            val = in_dict.get("value")
            if val is not None and val != "":
                options.append({"name": f"{in_key}-option", "value": val})

        # position
        position = node["position"]

        # measured (width/height 估算，与之前手动结果接近)
        num_ports = len(inputs) + len(outputs)
        if node_type == "Result":
            width = 160
            height = 90
        else:
            width = node.get("width", 200)
            height = 160 + 20 * max(0, num_ports - 3)  # 基础160，额外端口每+20

        measured = {"width": width, "height": height}

        new_node = {
            "id": node_id,
            "type": node_type,
            "name": name,
            "label": label,
            "inputs": inputs,
            "outputs": outputs,
            "options": options,
            "position": position,
            "measured": measured
        }
        editor_schema["nodes"].append(new_node)

    # connections
    for conn in data.get("connections", []):
        conn_id = conn["id"]
        from_port = conn["from"]
        to_port = conn["to"]

        if from_port in port_map and to_port in port_map:
            out_node, out_interface, out_dir = port_map[from_port]
            in_node, in_interface, in_dir = port_map[to_port]

            if out_dir == "output" and in_dir == "input":
                new_conn = {
                    "id": conn_id,
                    "outputNode": out_node,
                    "outputNodeInterface": out_interface,
                    "inputNode": in_node,
                    "inputNodeInterface": in_interface
                }
                editor_schema["connections"].append(new_conn)

    return {"editor_schema": editor_schema}

@router.post("/execute")
async def execute(request: ExecuteRequest):
    """
    执行 block 计算
    """
    try:
        scripts = request.scripts or []
        data = request.data['graph'] or {}

        # 转换为 editor_schema
        data = convert_schema(data)['editor_schema']

        # 创建动态引擎
        engine = make_dynamic_engine(scripts)

        # 执行计算
        schema = build_flow_schema_from_dict(data)
        result = engine.execute(schema)

        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")