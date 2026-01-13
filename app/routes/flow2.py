"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-12 19:36:16
LastEditors: zhai
LastEditTime: 2026-01-13 08:26:48
"""

"""
Blocks 路由
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from node.engine import make_dynamic_engine, get_json_blocks
from services import read_file, normalize_path
from flow2.schema import build_flow_schema_from_dict

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
        "viewport": {"x": 0, "y": 0, "zoom": 1.0},
    }

    nodes_list = data["nodes"]
    type_counter = defaultdict(int)

    # 映射：原 node_id -> prefixed "node__" + 原id
    node_id_map = {}
    # 用于端口映射：port_id -> (原 node_id, interface_name, direction)
    port_map = {}

    # 已知支持选项的输入名（只有这些才会生成 -option，避免无效选项报错）
    known_control_inputs = {
        "slider",
        "select",
        "checkbox",
        "number",
        "integer",
        "input",
        "test",
        "test2",
    }

    for node in nodes_list:
        original_id = node["id"]
        prefixed_id = f"node__{original_id}"
        node_id_map[original_id] = prefixed_id

        node_type = node["type"]
        type_counter[node_type] += 1
        label = f"{node_type}-{type_counter[node_type]}"
        name = node_type

        # inputs
        inputs = []
        for in_key in node.get("inputs", {}):
            inputs.append({"name": in_key, "itype": "typing.Any"})
            port_id = node["inputs"][in_key]["id"]
            port_map[port_id] = (original_id, in_key, "input")

        # outputs
        outputs = []
        for out_key in node.get("outputs", {}):
            outputs.append({"name": out_key, "itype": "typing.Any"})
            port_id = node["outputs"][out_key]["id"]
            port_map[port_id] = (original_id, out_key, "output")

        # options - 只为已知控制输入添加 -option
        options = []
        for in_key, in_dict in node.get("inputs", {}).items():
            val = in_dict.get("value")
            if val is not None and val != "" and in_key.lower() in known_control_inputs:
                options.append({"name": f"{in_key}-option", "value": val})

        # position
        position = node["position"]

        # measured
        if node_type == "Result":
            width = 160
            height = 90
        else:
            width = node.get("width", 200)
            num_ports = len(inputs) + len(outputs)
            height = 160 + 20 * max(0, num_ports - 3)

        measured = {"width": width, "height": height}

        new_node = {
            "id": prefixed_id,
            "type": node_type,
            "name": name,
            "label": label,
            "inputs": inputs,
            "outputs": outputs,
            "options": options,
            "position": position,
            "measured": measured,
        }
        editor_schema["nodes"].append(new_node)

    # connections
    for conn in data.get("connections", []):
        original_conn_id = conn["id"]
        prefixed_conn_id = f"edge__{original_conn_id}"

        from_port = conn["from"]
        to_port = conn["to"]

        if from_port in port_map and to_port in port_map:
            original_out_node, out_interface, out_dir = port_map[from_port]
            original_in_node, in_interface, in_dir = port_map[to_port]

            if out_dir == "output" and in_dir == "input":
                prefixed_out_node = node_id_map[original_out_node]
                prefixed_in_node = node_id_map[original_in_node]

                new_conn = {
                    "id": prefixed_conn_id,
                    "outputNode": prefixed_out_node,
                    "outputNodeInterface": out_interface,
                    "inputNode": prefixed_in_node,
                    "inputNodeInterface": in_interface,
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
        data = request.data["graph"] or {}

        # 转换为 editor_schema
        print(data)
        data = convert_schema(data)["editor_schema"]
        print(data)

        # 创建动态引擎
        engine = make_dynamic_engine(scripts)

        # 执行计算
        schema = build_flow_schema_from_dict(data)
        result = engine.execute(schema)

        return {"ok": True, "result": result}
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")
