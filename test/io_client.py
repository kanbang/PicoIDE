import zmq
import zmq.asyncio
import msgpack
import platform
import asyncio
import sys  

is_win = platform.system() == "Windows"

# ==================== 【关键修复开始】 ====================
# 必须在创建任何 asyncio loop 之前执行此策略切换
if is_win:
    # Windows 默认的 ProactorEventLoop 不支持 ZMQ 的 add_reader
    # 必须切换回 SelectorEventLoop
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
# ==================== 【关键修复结束】 ====================

# 引入配置以确保端口/名称一致
CONF = {
    "CAN": {"port": 5555, "ipc": "flow_can"},
    "MODBUS": {"port": 5556, "ipc": "flow_modbus"},
}

def get_connect_addr(svc_key):
    conf = CONF[svc_key]
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
        if "CAN" in self._sockets: return self._sockets["CAN"]
        
        sock = self.ctx.socket(zmq.SUB)
        addr = get_connect_addr("CAN")
        sock.connect(addr)
        sock.setsockopt(zmq.SUBSCRIBE, b"") 
        print(f"[Client] 订阅 CAN -> {addr}")
        self._sockets["CAN"] = sock
        return sock

    async def init_modbus_client(self):
        """初始化 Modbus 请求端"""
        if "MODBUS" in self._sockets: return self._sockets["MODBUS"]

        sock = self.ctx.socket(zmq.REQ)
        addr = get_connect_addr("MODBUS")
        sock.connect(addr)
        sock.setsockopt(zmq.RCVTIMEO, 2000) 
        print(f"[Client] 连接 Modbus -> {addr}")
        self._sockets["MODBUS"] = sock
        return sock

    async def get_can_frame(self):
        if "CAN" not in self._sockets: await self.init_can_subscriber()
        raw = await self._sockets["CAN"].recv()
        return msgpack.unpackb(raw, raw=False)

    async def read_modbus(self, addr):
        if "MODBUS" not in self._sockets: await self.init_modbus_client()
        
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
    print("正在连接 Modbus...")
    try:
        mb_sock = await client.init_modbus_client()
        await mb_sock.send(msgpack.packb({"op": "write", "addr": 10, "val": 999}))
        ack = await mb_sock.recv()
        print("Modbus Write Ack:", msgpack.unpackb(ack))
    except Exception as e:
        print(f"Modbus 测试失败: {e}")

    # 2. 测试 CAN 流
    print("正在连接 CAN...")
    await client.init_can_subscriber()
    print("开始监听 CAN 流 (接收 3 帧)...")
    for i in range(3):
        frame = await client.get_can_frame()
        print(f"[{i+1}] CAN Frame: {frame}")

if __name__ == "__main__":
    asyncio.run(test_engine())