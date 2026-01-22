"""
客户端 API 模块
提供类型安全的辅助类，避免手动拼接字典
"""
import asyncio
import platform
import zmq
import zmq.asyncio
from typing import Optional, Dict, Any, List
from config_loader import config
from serializer import serializer


class ModbusConfig:
    """Modbus 连接配置"""

    def __init__(self, host: str = '127.0.0.1', port: int = 502,
                 conn_type: str = 'tcp', baudrate: int = 9600):
        self.host = host
        self.port = port
        self.type = conn_type
        self.baudrate = baudrate

    def to_dict(self) -> Dict[str, Any]:
        return {
            'host': self.host,
            'port': self.port,
            'type': self.type,
            'baudrate': self.baudrate
        }


class ModbusWriteRequest:
    """Modbus 写请求"""

    def __init__(self, config: ModbusConfig, slave: int,
                 addr: int, val: Any, dtype: str = 'uint16'):
        self.config = config
        self.slave = slave
        self.addr = addr
        self.val = val
        self.type = dtype

    def to_dict(self) -> Dict[str, Any]:
        return {
            'op': 'write',
            'config': self.config.to_dict(),
            'slave': self.slave,
            'addr': self.addr,
            'val': self.val,
            'type': self.type
        }


class ModbusSubscribeTask:
    """Modbus 订阅任务"""

    def __init__(self, addr: int, dtype: str = 'uint16'):
        self.addr = addr
        self.type = dtype

    def to_dict(self) -> Dict[str, Any]:
        return {
            'addr': self.addr,
            'type': self.type
        }


class ModbusSubscribeRequest:
    """Modbus 订阅请求"""

    def __init__(self, config: ModbusConfig, slave: int,
                 tasks: List[ModbusSubscribeTask]):
        self.config = config
        self.slave = slave
        self.tasks = tasks

    def to_dict(self) -> Dict[str, Any]:
        return {
            'op': 'subscribe',
            'config': self.config.to_dict(),
            'slave': self.slave,
            'tasks': [task.to_dict() for task in self.tasks]
        }


class ModbusReadCacheRequest:
    """Modbus 读取缓存请求"""

    def to_dict(self) -> Dict[str, Any]:
        return {'op': 'read_cache'}


class IOClient:
    """IO 客户端 - 提供类型安全的 API"""

    def __init__(self):
        self.ctx = zmq.asyncio.Context()
        self._sockets: Dict[str, zmq.Socket] = {}
        self.is_windows = platform.system() == "Windows"

        # Windows 下必须使用 SelectorEventLoop
        if self.is_windows:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def _get_connect_addr(self, service_key: str, is_pub: bool = False) -> str:
        """获取连接地址"""
        svc_config = config.get_service_config(service_key)
        port_key = 'pub_port' if is_pub else 'req_port'

        if self.is_windows:
            return f"tcp://127.0.0.1:{svc_config[port_key]}"
        else:
            ipc_suffix = "_pub" if is_pub else ""
            return f"ipc:///tmp/{svc_config['ipc']}{ipc_suffix}.ipc"

    async def _get_modbus_socket(self) -> zmq.Socket:
        """获取或创建 Modbus REQ socket"""
        if "MODBUS" not in self._sockets:
            sock = self.ctx.socket(zmq.REQ)
            addr = self._get_connect_addr("MODBUS")
            sock.connect(addr)
            sock.setsockopt(zmq.RCVTIMEO, 2000)
            self._sockets["MODBUS"] = sock
        return self._sockets["MODBUS"]

    async def _get_can_socket(self) -> zmq.Socket:
        """获取或创建 CAN SUB socket"""
        if "CAN" not in self._sockets:
            sock = self.ctx.socket(zmq.SUB)
            addr = self._get_connect_addr("CAN", is_pub=True)
            sock.connect(addr)
            sock.setsockopt(zmq.SUBSCRIBE, b"")
            self._sockets["CAN"] = sock
        return self._sockets["CAN"]

    # ========== Modbus API ==========

    async def modbus_write(self, request: ModbusWriteRequest) -> Dict[str, Any]:
        """执行 Modbus 写操作"""
        sock = await self._get_modbus_socket()
        await sock.send(serializer.pack(request.to_dict()))
        raw = await sock.recv()
        return serializer.unpack(raw)

    async def modbus_subscribe(self, request: ModbusSubscribeRequest) -> Dict[str, Any]:
        """订阅 Modbus 寄存器"""
        sock = await self._get_modbus_socket()
        await sock.send(serializer.pack(request.to_dict()))
        raw = await sock.recv()
        return serializer.unpack(raw)

    async def modbus_read_cache(self) -> Dict[str, Any]:
        """读取 Modbus 缓存"""
        sock = await self._get_modbus_socket()
        await sock.send(serializer.pack(ModbusReadCacheRequest().to_dict()))
        raw = await sock.recv()
        return serializer.unpack(raw)

    # ========== CAN API ==========

    async def can_receive(self) -> Dict[str, Any]:
        """接收 CAN 帧"""
        sock = await self._get_can_socket()
        raw = await sock.recv()
        return serializer.unpack(raw)

    # ========== 便捷方法 ==========

    async def write_register(self, config: ModbusConfig, slave: int,
                             addr: int, val: int, dtype: str = 'uint16') -> Dict[str, Any]:
        """便捷方法：写单个寄存器"""
        request = ModbusWriteRequest(config, slave, addr, val, dtype)
        return await self.modbus_write(request)

    async def subscribe_registers(self, config: ModbusConfig, slave: int,
                                   addresses: List[int],
                                   dtype: str = 'uint16') -> Dict[str, Any]:
        """便捷方法：订阅多个寄存器"""
        tasks = [ModbusSubscribeTask(addr, dtype) for addr in addresses]
        request = ModbusSubscribeRequest(config, slave, tasks)
        return await self.modbus_subscribe(request)

    # ========== 清理 ==========

    def close(self):
        """关闭所有连接"""
        for sock in self._sockets.values():
            sock.close()
        self.ctx.term()


# 便捷函数
def create_modbus_config(host: str = '127.0.0.1', port: int = 502,
                         conn_type: str = 'tcp', baudrate: int = 9600) -> ModbusConfig:
    """创建 Modbus 配置"""
    return ModbusConfig(host, port, conn_type, baudrate)