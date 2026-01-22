import os
import sys
import platform
import signal
import logging
import zmq
import zmq.asyncio
from abc import ABC, abstractmethod
from config_loader import config
from serializer import serializer


def setup_logger(name):
    """配置日志记录器"""
    log_config = config.logging_config
    level = getattr(logging, log_config.get('level', 'INFO'))
    logging.basicConfig(
        level=level,
        format=log_config.get('format', '%(asctime)s [%(levelname)s] %(message)s'),
        datefmt=log_config.get('datefmt', '%H:%M:%S')
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
        if self.is_windows:
            port = self._get_port(is_pub)
            return f"tcp://*:{port}"
        else:
            ipc_file = self._get_ipc_file(is_pub)
            if os.path.exists(ipc_file):
                try:
                    os.unlink(ipc_file)
                except:
                    pass
            return f"ipc://{ipc_file}"

    def _get_port(self, is_pub=False):
        """获取端口号"""
        services = config._config.get('services', {})
        svc_config = services.get(self.service_key, {})
        port_key = "pub_port" if is_pub else "req_port"
        return svc_config.get(port_key)

    def _get_ipc_file(self, is_pub=False):
        """获取 IPC 文件路径"""
        services = config._config.get('services', {})
        svc_config = services.get(self.service_key, {})
        ipc_suffix = "_pub" if is_pub else ""
        return f"/tmp/{svc_config.get('ipc', 'flow')}{ipc_suffix}.ipc"

    def pack(self, data):
        """使用配置的序列化器"""
        return serializer.pack(data)

    def unpack(self, data):
        """使用配置的序列化器"""
        return serializer.unpack(data)

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
            # 清理资源
            self._cleanup()

    def _cleanup(self):
        """清理资源"""
        # 终止 ZMQ 上下文（会自动关闭所有 socket）
        self.ctx.term()

        # 清理 IPC 文件（仅 Linux）
        if not self.is_windows:
            self._cleanup_ipc_files()

        self.logger.info("资源清理完成，进程退出。")

    def _cleanup_ipc_files(self):
        """清理 IPC 文件"""
        for is_pub in [False, True]:
            ipc_file = self._get_ipc_file(is_pub)
            if ipc_file and os.path.exists(ipc_file):
                try:
                    os.unlink(ipc_file)
                    self.logger.info(f"清理 IPC 文件: {ipc_file}")
                except Exception as e:
                    self.logger.warning(f"清理 IPC 文件失败: {e}")