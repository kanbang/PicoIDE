import os
import sys
import platform
import signal
import logging
import zmq
import zmq.asyncio
import msgpack
import struct
from abc import ABC, abstractmethod

# 配置常量增加 PUB 端口定义
CONF = {
    "CAN": {"port": 5555, "pub_port": 5557, "ipc": "flow_can"},
    "MODBUS": {"port": 5556, "pub_port": 5558, "ipc": "flow_modbus"},
}

def setup_logger(name):
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
        if not self.is_windows:
            signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.logger.info(f"接收到终止信号 ({signum})，准备安全退出...")
        self.running = False

    def get_addr(self, is_pub=False):
        """
        根据操作系统自动选择绑定地址
        :param is_pub: 是否获取发布通道(PUB)的地址
        """
        conf = CONF[self.service_key]
        port_key = "pub_port" if is_pub else "port"
        ipc_suffix = "_pub" if is_pub else ""
        
        if self.is_windows:
            # Windows 下绑定所有网卡，但在调试信息中显示 127.0.0.1
            addr = f"tcp://*:{conf[port_key]}"
            return addr
        else:
            ipc_file = f"/tmp/{conf['ipc']}{ipc_suffix}.ipc"
            if os.path.exists(ipc_file):
                try: os.unlink(ipc_file)
                except: pass
            return f"ipc://{ipc_file}"

    def pack(self, data):
        return msgpack.packb(data, use_bin_type=True)

    def unpack(self, data):
        return msgpack.unpackb(data, raw=False)

    @abstractmethod
    async def main_loop(self):
        pass

    def start(self):
        import asyncio
        if self.is_windows:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        try:
            asyncio.run(self.main_loop())
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.logger.exception(f"服务运行崩溃: {e}")
        finally:
            self.ctx.term()
            self.logger.info("ZMQ 上下文已释放，进程退出。")