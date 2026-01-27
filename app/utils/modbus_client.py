import asyncio
import platform
import zmq
import zmq.asyncio
import msgpack
from dataclasses import dataclass, asdict, field
from enum import Enum


# Windows 下必须使用 SelectorEventLoop
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class DataType(Enum):
    """数据类型枚举，防止拼写错误"""
    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    FLOAT32 = "float32"
    FLOAT64 = "float64"
    UINT64 = "uint64"
    INT64 = "int64"
    STRING = "string"
    BITS = "bits"
    BOOL = "bool"
    COIL = "coil"  # 兼容 coil/bool

class RegisterType(Enum):
    """寄存器类型枚举，防止拼写错误"""
    HOLDING = "holding"
    INPUT = "input"
    COIL = "coil"
    DISCRETE = "discrete"

@dataclass
class ModbusConfig:
    type: str = "tcp"
    host: str = "127.0.0.1"
    port: int = 502
    baudrate: int = 9600
    parity: str = "N"
    bytesize: int = 8
    stopbits: int = 1

@dataclass
class SubscribeTask:
    addr: int
    type: DataType = DataType.UINT16
    register_type: RegisterType = RegisterType.HOLDING

@dataclass
class SubscribeRequest:
    op: str = "subscribe"
    config: ModbusConfig = ModbusConfig()
    slave: int = 1
    tasks: list[SubscribeTask] = field(default_factory=list)  # 使用 field 以支持 mutable default

@dataclass
class WriteTask:
    addr: int
    val: any
    type: DataType = DataType.UINT16
    register_type: RegisterType = RegisterType.HOLDING

@dataclass
class WriteRequest:
    op: str = "write"
    priority: int = 1
    config: ModbusConfig = ModbusConfig()
    slave: int = 1
    addr: int = 0
    val: any = 0
    type: DataType = DataType.UINT16
    register_type: RegisterType = RegisterType.HOLDING

@dataclass
class BatchWriteRequest:
    op: str = "batch_write"
    priority: int = 1
    config: ModbusConfig = ModbusConfig()
    slave: int = 1
    tasks: list[WriteTask] = field(default_factory=list)

@dataclass
class ReadTask:
    addr: int
    type: DataType = DataType.UINT16
    register_type: RegisterType = RegisterType.HOLDING

@dataclass
class ReadRequest:
    op: str = "read"
    config: ModbusConfig = ModbusConfig()
    slave: int = 1
    addr: int = 0
    type: DataType = DataType.UINT16
    register_type: RegisterType = RegisterType.HOLDING
    cache_it: bool = True

@dataclass
class BatchReadRequest:
    op: str = "batch_read"
    config: ModbusConfig = ModbusConfig()
    slave: int = 1
    tasks: list[ReadTask] = field(default_factory=list)
    cache_it: bool = True

@dataclass
class ReadCacheRequest:
    op: str = "read_cache"

@dataclass
class SetHeartbeatRequest:
    op: str = "set_heartbeat"
    config: ModbusConfig = ModbusConfig()
    heartbeat_slave: int = 0
    heartbeat_addr: int = 0

class ModbusClient:
    """
    Modbus client supporting both REQ/REP (synchronous) and DEALER/ROUTER (asynchronous concurrent) modes.
    """
    def __init__(self, req_addr="tcp://127.0.0.1:5556", pub_addr="tcp://127.0.0.1:5558", zmq_mode='router'):
        self.ctx = zmq.asyncio.Context()
        self.req_addr = req_addr
        self.pub_addr = pub_addr
        self.zmq_mode = zmq_mode.lower()
        self._create_req_socket()
        self.pub_sock = self.ctx.socket(zmq.SUB)
        self.pub_sock.connect(pub_addr)
        self.pub_sock.setsockopt(zmq.SUBSCRIBE, b"modbus.update")
        self.pub_sock.setsockopt(zmq.RCVTIMEO, -1)  # Infinite timeout to avoid periodic EAGAIN
        self._callbacks = {}  # (ckey, slave, addr) → list[callable]
        self._update_queue = asyncio.Queue()  # 用于测试中收集更新
        print(f"ModbusClient initialized ({self.zmq_mode.upper()} mode) and connected to {req_addr}")

    def _create_req_socket(self):
        if hasattr(self, 'req_sock') and self.req_sock:
            self.req_sock.close()
        if self.zmq_mode == 'router':
            self.req_sock = self.ctx.socket(zmq.DEALER)
        elif self.zmq_mode == 'rep':
            self.req_sock = self.ctx.socket(zmq.REQ)
        else:
            raise ValueError(f"Unsupported zmq_mode: {self.zmq_mode}")
        self.req_sock.connect(self.req_addr)
        self.req_sock.setsockopt(zmq.RCVTIMEO, 5000)
        self.req_sock.setsockopt(zmq.SNDTIMEO, 5000)

    def _enum_to_str(self, d):
        """递归地将 Enum 转换为 str 值，以便序列化"""
        if isinstance(d, dict):
            return {k: self._enum_to_str(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self._enum_to_str(item) for item in d]
        elif isinstance(d, Enum):
            return d.value
        else:
            return d

    async def send_request(self, req_obj):
        req_dict = asdict(req_obj)
        req_dict = self._enum_to_str(req_dict)
        packed = msgpack.packb(req_dict)
        retries = 3  # Increased retries
        for attempt in range(retries):
            try:
                if self.zmq_mode == 'router':
                    # DEALER sends: [b'', packed_data]
                    await self.req_sock.send_multipart([b'', packed])
                    # DEALER receives: [b'', response_data] from ROUTER
                    _, raw = await self.req_sock.recv_multipart()
                else:  # REQ mode
                    await self.req_sock.send(packed)
                    raw = await self.req_sock.recv()
                return msgpack.unpackb(raw, strict_map_key=False)
            except zmq.error.ZMQError as e:
                print(f"Network error (attempt {attempt+1}/{retries}): {e}. Resetting socket...")
                self._create_req_socket()
                # Optional: Poll for readiness
                poller = zmq.asyncio.Poller()
                poller.register(self.req_sock, zmq.POLLOUT)
                events = await poller.poll(1000)  # Wait up to 1s for writable
                if not events:
                    continue
                await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff

        raise zmq.error.ZMQError("Max retries exceeded")

    def on_update(self, ckey: str, slave: int, addr: int, callback):
        """注册变化回调"""
        key = (ckey, slave, addr)
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    async def _handle_updates(self):
        while True:
            try:
                topic, packed = await self.pub_sock.recv_multipart()
                if topic != b"modbus.update":
                    continue
                msg = msgpack.unpackb(packed, strict_map_key=False)
                ckey = msg.get("ckey")
                slave = msg.get("slave")
                addr = msg.get("addr")
                val = msg.get("val")
                ts = msg.get("ts")
                key = (ckey, slave, addr)
                await self._update_queue.put(msg)  # 用于测试收集
                if key in self._callbacks:
                    for cb in self._callbacks[key]:
                        try:
                            await cb(val, {"ts": ts, "ckey": ckey, "slave": slave, "addr": addr})
                        except Exception as e:
                            print(f"Callback error for {key}: {e}")
            except zmq.Again:
                continue  # Explicitly handle timeout (if timeout enabled)
            except zmq.error.ZMQError as e:
                print(f"Update receiver network error: {e}. Waiting to reconnect...")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Update receiver error: {e}")
                await asyncio.sleep(1)

    async def subscribe_and_watch(self, config: ModbusConfig, slave: int,
                                  tasks: list[SubscribeTask],
                                  callback=None):
        req = SubscribeRequest(config=config, slave=slave, tasks=tasks)
        resp = await self.send_request(req)
        if resp.get("status") != "ok":
            raise RuntimeError(f"Subscribe failed: {resp}")
        if config.type == "tcp":
            ckey = f"{config.type}://{config.host}:{config.port}"
        else:
            ckey = f"{config.type}://{config.port}:{config.baudrate}"
        for task in tasks:
            if callback:
                self.on_update(ckey, slave, task.addr, callback)
        return resp

    async def start_update_handler(self):
        asyncio.create_task(self._handle_updates())