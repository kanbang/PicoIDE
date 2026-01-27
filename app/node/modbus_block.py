import json
import logging
import asyncio
import threading
from typing import Dict, List, Any, Callable, Optional, Tuple
from collections import defaultdict
import uuid

from flow.block import BaseBlock
from utils.singleton import singleton
from utils.modbus_client import ModbusClient, DataType, RegisterType
from paho.mqtt import client as mqtt



# ModbusReadBlock: 专注于Modbus读取操作
class ModbusReadBlock(BaseBlock):
    NAME = "Modbus Read"
    CATEGORY = "Communication"
    STREAMING = False

    def __init__(self):
        super().__init__()
        # 输出
        self.add_output("result")  # 读取值或{"error": str}

        self.add_text_option("Read Parameters", "- 读取参数")  # 组名，作为label
        self.add_integer_option("addr", default=0)
        self.add_select_option("dtype", items=[dt.value for dt in DataType], default="uint16")
        self.add_select_option("register_type", items=[rt.value for rt in RegisterType], default="holding")
        self.add_checkbox_option("cache_it", default=True)

        self.add_text_option("Connection Settings", "- 连接设置")  # 组名，作为label
        self.add_select_option("conn_type", items=["tcp", "serial"], default="tcp")
        self.add_text_input_option("host", default="127.0.0.1")
        self.add_integer_option("port", default=502, min_val=1, max_val=65535)
        self.add_integer_option("slave", default=1)
        self.add_integer_option("timeout", default=5)  # 操作超时秒
       
        self.add_text_option("Serial Settings", "- 串口相关")  # 组名，作为label
        self.add_integer_option("baudrate", default=9600)  # serial only
        self.add_text_input_option("parity", default="N")  # serial only
        self.add_integer_option("bytesize", default=8)  # serial only
        self.add_integer_option("stopbits", default=1)  # serial only


        self.client = None

    async def _init_client(self):
        config = ModbusConfig(
            type=self.get_option("conn_type"),
            host=self.get_option("host"),
            port=self.get_option("port"),
            baudrate=self.get_option("baudrate"),
            parity=self.get_option("parity"),
            bytesize=self.get_option("bytesize"),
            stopbits=self.get_option("stopbits")
        )
        self.client = ModbusClient()  # 假设支持async
        await self.client.start_update_handler()

    async def async_on_compute(self, execution_id: str = None):
        if not self.client:
            await self._init_client()

        try:
            req = ReadRequest(
                config=ModbusConfig(),  # 使用选项填充，略
                slave=self.get_option("slave"),
                addr=self.get_option("addr"),
                type=DataType[self.get_option("dtype").upper()],
                register_type=RegisterType[self.get_option("register_type").upper()],
                cache_it=self.get_option("cache_it")
            )
            res = await asyncio.wait_for(self.client.send_request(req), timeout=self.get_option("timeout"))
            self.set_interface("result", res.get("val"))
        except Exception as e:
            self.set_interface("result", {"error": str(e)})

# ModbusWriteBlock: 专注于Modbus写入操作
class ModbusWriteBlock(BaseBlock):
    NAME = "Modbus Write"
    CATEGORY = "Communication"
    STREAMING = False

    def __init__(self):
        super().__init__()
        # 输出
        self.add_output("result")  # {"status": "ok"} 或 {"error": str}

        self.add_text_option("Write Parameters", "- 写入参数")  # 组名，作为label
        self.add_integer_option("addr", default=0)
        self.add_text_input_option("val", default="0")  # val as string, parse based on dtype
        self.add_select_option("dtype", items=[dt.value for dt in DataType], default="uint16")
        self.add_select_option("register_type", items=[rt.value for rt in RegisterType], default="holding")

        self.add_text_option("Connection Settings", "- 连接设置")  # 组名，作为label
        self.add_select_option("conn_type", items=["tcp", "serial"], default="tcp")
        self.add_text_input_option("host", default="127.0.0.1")
        self.add_integer_option("port", default=502, min_val=1, max_val=65535)
        self.add_integer_option("slave", default=1)
        self.add_integer_option("timeout", default=5)  # 操作超时秒
       
        self.add_text_option("Serial Settings", "- 串口相关")  # 组名，作为label
        self.add_integer_option("baudrate", default=9600)  # serial only
        self.add_text_input_option("parity", default="N")  # serial only
        self.add_integer_option("bytesize", default=8)  # serial only
        self.add_integer_option("stopbits", default=1)  # serial only

        self.client = None

    async def _init_client(self):
        config = ModbusConfig(
            type=self.get_option("conn_type"),
            host=self.get_option("host"),
            port=self.get_option("port"),
            baudrate=self.get_option("baudrate"),
            parity=self.get_option("parity"),
            bytesize=self.get_option("bytesize"),
            stopbits=self.get_option("stopbits")
        )
        self.client = ModbusClient()  # 假设支持async
        await self.client.start_update_handler()

    async def async_on_compute(self, execution_id: str = None):
        if not self.client:
            await self._init_client()

        val_str = self.get_option("val")
        dtype = self.get_option("dtype")
        # Parse val based on dtype (simple parsing)
        if "int" in dtype.lower():
            val = int(val_str)
        elif "float" in dtype.lower():
            val = float(val_str)
        elif dtype.lower() == "bool":
            val = bool(val_str.lower() == "true")
        else:
            val = val_str  # string or others

        try:
            req = WriteRequest(
                config=ModbusConfig(),  # 填充
                slave=self.get_option("slave"),
                addr=self.get_option("addr"),
                val=val,
                type=DataType[dtype.upper()],
                register_type=RegisterType[self.get_option("register_type").upper()]
            )
            res = await asyncio.wait_for(self.client.send_request(req), timeout=self.get_option("timeout"))
            self.set_interface("result", res)
        except Exception as e:
            self.set_interface("result", {"error": str(e)})

# ModbusSubscribeBlock: 专注于Modbus订阅操作，支持流式输出
class ModbusSubscribeBlock(BaseBlock):
    NAME = "Modbus Subscribe"
    CATEGORY = "Communication"
    STREAMING = True  # 启用流式，持续输出更新

    def __init__(self):
        super().__init__()
        # 输出
        self.add_output("update")  # 每个更新: {"addr": int, "val": any, "ts": float}

        self.add_text_option("Subscribe Parameters", "- 订阅参数")  # 组名，作为label
        self.add_textarea_input_option("tasks", default="addr:0,dtype:uint16,register_type:holding\naddr:1,dtype:int16")  # 多行输入，每行一个task

        self.add_text_option("Connection Settings", "- 连接设置")  # 组名，作为label
        self.add_select_option("conn_type", items=["tcp", "serial"], default="tcp")
        self.add_text_input_option("host", default="127.0.0.1")
        self.add_integer_option("port", default=502, min_val=1, max_val=65535)
        self.add_integer_option("slave", default=1)
        self.add_integer_option("timeout", default=5)  # 操作超时秒
       
        self.add_text_option("Serial Settings", "- 串口相关")  # 组名，作为label
        self.add_integer_option("baudrate", default=9600)  # serial only
        self.add_text_input_option("parity", default="N")  # serial only
        self.add_integer_option("bytesize", default=8)  # serial only
        self.add_integer_option("stopbits", default=1)  # serial only

        self.client = None
        self.update_queue = asyncio.Queue()  # 内部队列缓存更新

    async def _init_client(self):
        config = ModbusConfig(
            type=self.get_option("conn_type"),
            host=self.get_option("host"),
            port=self.get_option("port"),
            baudrate=self.get_option("baudrate"),
            parity=self.get_option("parity"),
            bytesize=self.get_option("bytesize"),
            stopbits=self.get_option("stopbits")
        )
        self.client = ModbusClient()  # 假设支持async
        await self.client.start_update_handler()

    async def async_on_compute(self, execution_id: str = None):
        if not self.client:
            await self._init_client()

        tasks_str = self.get_option("tasks")
        tasks = []
        for line in tasks_str.splitlines():
            if line.strip():
                task_dict = {}
                for part in line.split(','):
                    k, v = part.split(':')
                    task_dict[k.strip()] = v.strip()
                tasks.append(task_dict)

        sub_tasks = [SubscribeTask(addr=int(t['addr']), type=DataType[t.get('dtype', 'UINT16').upper()], register_type=RegisterType[t.get('register_type', 'HOLDING').upper()]) for t in tasks]

        async def callback(val, meta):
            update = {"addr": meta["addr"], "val": val, "ts": meta["ts"]}
            await self.update_queue.put(update)

        try:
            await self.client.subscribe_and_watch(ModbusConfig(), self.get_option("slave"), sub_tasks, callback=callback)
            # 流式输出循环
            while self.STREAMING:
                try:
                    update = await asyncio.wait_for(self.update_queue.get(), timeout=self.get_option("timeout"))
                    self.set_interface("update", update)  # 输出到下游
                except asyncio.TimeoutError:
                    break  # 超时退出流式
        except Exception as e:
            self.set_interface("update", {"error": str(e)})