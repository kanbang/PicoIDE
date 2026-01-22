'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-22 10:54:07
LastEditors: zhai
LastEditTime: 2026-01-22 10:54:21
'''
import os
import sys
import platform
import signal
import logging
import zmq
import zmq.asyncio
import msgpack
from abc import ABC, abstractmethod

# 配置常量
CONF = {
    "CAN": {"port": 5555, "ipc": "flow_can"},
    "MODBUS": {"port": 5556, "ipc": "flow_modbus"},
}

def setup_logger(name):
    """配置带时间戳和进程ID的日志"""
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s [%(levelname)s] [{name}:{os.getpid()}] %(message)s',
        datefmt='%H:%M:%S'
    )
    return logging.getLogger(name)

class BaseIOService(ABC):
    def __init__(self, service_key):
        self.service_key = service_key
        self.logger = setup_logger(service_key)
        self.ctx = zmq.asyncio.Context()
        self.running = True
        self.is_windows = platform.system() == "Windows"
        
        # 信号注册
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.logger.info(f"接收到终止信号 ({signum})，准备退出...")
        self.running = False

    def get_bind_address(self):
        """根据操作系统自动选择绑定地址"""
        conf = CONF[self.service_key]
        if self.is_windows:
            addr = f"tcp://*:{conf['port']}"
            self.logger.info(f"Platform: Windows -> Binding TCP: {addr}")
            return addr
        else:
            ipc_file = f"/tmp/{conf['ipc']}.ipc"
            # 鲁棒性：启动前清理残留文件
            if os.path.exists(ipc_file):
                try:
                    os.unlink(ipc_file)
                    self.logger.warning(f"清理了残留的 IPC 文件: {ipc_file}")
                except OSError as e:
                    self.logger.error(f"清理 IPC 文件失败: {e}")
            
            addr = f"ipc://{ipc_file}"
            self.logger.info(f"Platform: Linux -> Binding IPC: {addr}")
            return addr

    def pack(self, data):
        """使用 MessagePack 高效序列化"""
        return msgpack.packb(data, use_bin_type=True)

    def unpack(self, data):
        return msgpack.unpackb(data, raw=False)

    @abstractmethod
    async def main_loop(self):
        pass

    def start(self):
        """入口方法"""
        import asyncio
        if self.is_windows:
            # Windows 下 asyncio 策略调整
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        try:
            asyncio.run(self.main_loop())
        except KeyboardInterrupt:
            self.logger.info("服务已停止")
        except Exception as e:
            self.logger.exception(f"服务发生未捕获异常: {e}")
        finally:
            self.ctx.term()