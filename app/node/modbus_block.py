import json
import logging
import asyncio
import threading
from typing import Dict, List, Any, Callable, Optional, Tuple
from collections import defaultdict
import uuid

from flow.block import BaseBlock
from utils.singleton import singleton
from utils.modbus_client import (
    ModbusClient,
    DataType,
    RegisterType,
    ModbusConfig,
    ReadRequest,
    SubscribeTask,
    WriteRequest,
)
from paho.mqtt import client as mqtt


class ModbusReadBlock(BaseBlock):
    NAME = "Modbus Read"
    CATEGORY = "Communication"
    STREAMING = False

    def __init__(self):
        super().__init__()
        self.add_output("result")

        self.add_text_option("Read Parameters", "- 读取参数")
        self.add_integer_option("addr", default=0)
        self.add_select_option(
            "dtype", items=[dt.value for dt in DataType], default="uint16"
        )
        self.add_select_option(
            "register_type", items=[rt.value for rt in RegisterType], default="holding"
        )
        self.add_checkbox_option("cache_it", default=True)

        self.add_text_option("Connection Settings", "- 连接设置")
        self.add_select_option("conn_type", items=["tcp", "serial"], default="tcp")
        self.add_text_input_option("host", default="127.0.0.1")
        self.add_integer_option("port", default=502, min_val=1, max_val=65535)
        self.add_integer_option("slave", default=1)
        self.add_integer_option("timeout", default=5)

        self.add_text_option("Serial Settings", "- 串口相关")
        self.add_integer_option("baudrate", default=9600)
        self.add_text_input_option("parity", default="N")
        self.add_integer_option("bytesize", default=8)
        self.add_integer_option("stopbits", default=1)

    async def on_compute(self, execution_id: str = None):
        config = ModbusConfig(
            type=self.get_option("conn_type"),
            host=self.get_option("host"),
            port=self.get_option("port"),
            baudrate=self.get_option("baudrate"),
            parity=self.get_option("parity"),
            bytesize=self.get_option("bytesize"),
            stopbits=self.get_option("stopbits"),
        )
        client = ModbusClient()
        try:
            req = ReadRequest(
                config=config,
                slave=self.get_option("slave"),
                addr=self.get_option("addr"),
                type=DataType[self.get_option("dtype").upper()],
                register_type=RegisterType[self.get_option("register_type").upper()],
                cache_it=self.get_option("cache_it"),
            )
            res = await asyncio.wait_for(
                client.send_request(req), timeout=self.get_option("timeout")
            )
            if res.get("status") == "ok":
                self.set_interface("result", res.get("val"))
            else:
                self.set_interface("result", {"error": res.get("error", "unknown")})
        except Exception as e:
            self.set_interface("result", {"error": str(e)})
        finally:
            client.req_sock.close()
            client.pub_sock.close()


class ModbusWriteBlock(BaseBlock):
    NAME = "Modbus Write"
    CATEGORY = "Communication"
    STREAMING = False

    def __init__(self):
        super().__init__()
        self.add_output("result")

        self.add_text_option("Write Parameters", "- 写入参数")
        self.add_integer_option("addr", default=0)
        self.add_text_input_option("val", default="0")
        self.add_select_option(
            "dtype", items=[dt.value for dt in DataType], default="uint16"
        )
        self.add_select_option(
            "register_type", items=[rt.value for rt in RegisterType], default="holding"
        )

        self.add_text_option("Connection Settings", "- 连接设置")
        self.add_select_option("conn_type", items=["tcp", "serial"], default="tcp")
        self.add_text_input_option("host", default="127.0.0.1")
        self.add_integer_option("port", default=502, min_val=1, max_val=65535)
        self.add_integer_option("slave", default=1)
        self.add_integer_option("timeout", default=5)

        self.add_text_option("Serial Settings", "- 串口相关")
        self.add_integer_option("baudrate", default=9600)
        self.add_text_input_option("parity", default="N")
        self.add_integer_option("bytesize", default=8)
        self.add_integer_option("stopbits", default=1)

    async def on_compute(self, execution_id: str = None):
        config = ModbusConfig(
            type=self.get_option("conn_type"),
            host=self.get_option("host"),
            port=self.get_option("port"),
            baudrate=self.get_option("baudrate"),
            parity=self.get_option("parity"),
            bytesize=self.get_option("bytesize"),
            stopbits=self.get_option("stopbits"),
        )
        client = ModbusClient()
        val_str = self.get_option("val")
        dtype = self.get_option("dtype")
        if "int" in dtype.lower():
            val = int(val_str)
        elif "float" in dtype.lower():
            val = float(val_str)
        elif dtype.lower() == "bool":
            val = bool(val_str.lower() == "true")
        else:
            val = val_str

        try:
            req = WriteRequest(
                config=config,
                slave=self.get_option("slave"),
                addr=self.get_option("addr"),
                val=val,
                type=DataType[dtype.upper()],
                register_type=RegisterType[self.get_option("register_type").upper()],
            )
            res = await asyncio.wait_for(
                client.send_request(req), timeout=self.get_option("timeout")
            )
            self.set_interface("result", res)
        except Exception as e:
            self.set_interface("result", {"error": str(e)})
        finally:
            client.req_sock.close()
            client.pub_sock.close()


class ModbusSubscribeBlock(BaseBlock):
    NAME = "Modbus Subscribe"
    CATEGORY = "Communication"
    STREAMING = True

    def __init__(self):
        super().__init__()
        self.add_output("update")

        self.add_text_option("Subscribe Parameters", "- 订阅参数")
        self.add_textarea_input_option(
            "tasks",
            default="addr:0,dtype:uint16,register_type:holding\naddr:1,dtype:int16",
        )

        self.add_text_option("Connection Settings", "- 连接设置")
        self.add_select_option("conn_type", items=["tcp", "serial"], default="tcp")
        self.add_text_input_option("host", default="127.0.0.1")
        self.add_integer_option("port", default=502, min_val=1, max_val=65535)
        self.add_integer_option("slave", default=1)
        self.add_integer_option("timeout", default=5)

        self.add_text_option("Serial Settings", "- 串口相关")
        self.add_integer_option("baudrate", default=9600)
        self.add_text_input_option("parity", default="N")
        self.add_integer_option("bytesize", default=8)
        self.add_integer_option("stopbits", default=1)

        self._update_queue = asyncio.Queue(maxsize=10)
        self._client = ModbusClient()
        self._registered = False

    async def _on_update(self, val, meta):
        await self._update_queue.put({"addr": meta["addr"], "val": val, "ts": meta["ts"]})

    async def on_compute(self, execution_id: str = None):
        config = ModbusConfig(
            type=self.get_option("conn_type"),
            host=self.get_option("host"),
            port=self.get_option("port"),
            baudrate=self.get_option("baudrate"),
            parity=self.get_option("parity"),
            bytesize=self.get_option("bytesize"),
            stopbits=self.get_option("stopbits"),
        )

        if not self._registered:
            await self._client.start_update_handler()
            tasks_str = self.get_option("tasks")
            tasks = []
            for line in tasks_str.splitlines():
                if line.strip():
                    task_dict = {}
                    for part in line.split(","):
                        k, v = part.split(":")
                        task_dict[k.strip()] = v.strip()
                    tasks.append(task_dict)

            sub_tasks = [
                SubscribeTask(
                    addr=int(t["addr"]),
                    type=DataType[t.get("dtype", "uint16").upper()],
                    register_type=RegisterType[t.get("register_type", "holding").upper()],
                )
                for t in tasks
            ]

            await self._client.subscribe_and_watch(config, self.get_option("slave"), sub_tasks, callback=self._on_update)
            self._registered = True

        update = await self._update_queue.get()
        self.set_interface("update", update)


__all__ = ["ModbusReadBlock", "ModbusWriteBlock", "ModbusSubscribeBlock"]