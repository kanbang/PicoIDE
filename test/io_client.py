"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-22 11:06:11
LastEditors: zhai
LastEditTime: 2026-01-22 11:06:18
"""

import zmq
import zmq.asyncio
import msgpack
import platform
import asyncio

# 引入配置以确保端口/名称一致
# 实际项目中建议将 CONF 移至单独的 config.py
CONF = {
    "CAN": {"port": 5555, "ipc": "flow_can"},
    "MODBUS": {"port": 5556, "ipc": "flow_modbus"},
}


def get_connect_addr(svc_key):
    conf = CONF[svc_key]
    is_win = platform.system() == "Windows"

    if is_win:
        return f"tcp://127.0.0.1:{conf['port']}"
    else:
        return f"ipc:///tmp/{conf['ipc']}.ipc"


class IOClient:
    def __init__(self):
        self.ctx = zmq.asyncio.Context()
        self._sockets = {}

    async def init_can_subscriber(self):
        """初始化 CAN 订阅"""
        sock = self.ctx.socket(zmq.SUB)
        addr = get_connect_addr("CAN")
        sock.connect(addr)
        sock.setsockopt(zmq.SUBSCRIBE, b"")  # 订阅所有
        print(f"[Client] 订阅 CAN -> {addr}")
        self._sockets["CAN"] = sock
        return sock

    async def init_modbus_client(self):
        """初始化 Modbus 请求端"""
        sock = self.ctx.socket(zmq.REQ)
        addr = get_connect_addr("MODBUS")
        sock.connect(addr)
        # 关键：设置接收超时，防止服务端挂死导致客户端无限等待
        sock.setsockopt(zmq.RCVTIMEO, 2000)  # 2秒超时
        print(f"[Client] 连接 Modbus -> {addr}")
        self._sockets["MODBUS"] = sock
        return sock

    async def get_can_frame(self):
        if "CAN" not in self._sockets:
            await self.init_can_subscriber()
        raw = await self._sockets["CAN"].recv()
        return msgpack.unpackb(raw, raw=False)

    async def read_modbus(self, addr):
        if "MODBUS" not in self._sockets:
            await self.init_modbus_client()

        req = msgpack.packb({"op": "read", "addr": addr})
        await self._sockets["MODBUS"].send(req)

        try:
            raw = await self._sockets["MODBUS"].recv()
            return msgpack.unpackb(raw, raw=False)
        except zmq.Again:
            raise TimeoutError("Modbus 服务响应超时")


# --- 测试代码 ---
async def test_engine():
    client = IOClient()

    # 1. 测试 Modbus 写
    mb_sock = await client.init_modbus_client()
    await mb_sock.send(msgpack.packb({"op": "write", "addr": 10, "val": 999}))
    print("Modbus Write Ack:", msgpack.unpackb(await mb_sock.recv()))

    # 2. 测试 Modbus 读
    res = await client.read_modbus(10)
    print("Modbus Read Res:", res)

    # 3. 测试 CAN 流 (读取 5 帧)
    await client.init_can_subscriber()
    print("开始监听 CAN 流...")
    for _ in range(5):
        frame = await client.get_can_frame()
        print(f"CAN Frame: ID={hex(frame['id'])} Data={frame['data']}")


if __name__ == "__main__":
    asyncio.run(test_engine())
