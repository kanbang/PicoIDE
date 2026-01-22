import asyncio
import threading
import queue
import time
import zmq
import can
from common import BaseIOService

class CanChannelHandler:
    """单个 CAN 通道处理器：管理物理硬件的读、写和队列"""
    def __init__(self, channel, bustype, bitrate, logger, pack_func):
        self.channel = channel
        self.logger = logger
        self.pack = pack_func
        self.write_queue = queue.Queue()
        self.bus = None
        self.running = True
        
        # 初始化物理总线
        try:
            self.bus = can.interface.Bus(channel=channel, bustype=bustype, bitrate=bitrate)
            self.logger.info(f"CAN 通道 {channel} 初始化成功 ({bustype})")
        except Exception as e:
            self.logger.error(f"CAN 通道 {channel} 初始化失败: {e}")

    def run_hardware_loop(self, pub_sock, service_key):
        """[独立线程] 混合读写循环"""
        while self.running and self.bus:
            try:
                # 1. 处理写操作 (优先)
                while not self.write_queue.empty():
                    msg_cfg = self.write_queue.get_nowait()
                    msg = can.Message(
                        arbitration_id=msg_cfg['id'],
                        data=msg_cfg['data'],
                        is_extended_id=msg_cfg.get('is_ext', False)
                    )
                    self.bus.send(msg)

                # 2. 处理读操作 (设置短超时以便循环检查)
                rx_msg = self.bus.recv(timeout=0.01)
                if rx_msg:
                    frame = {
                        "ch": self.channel,
                        "id": rx_msg.arbitration_id,
                        "data": list(rx_msg.data),
                        "dlc": rx_msg.dlc,
                        "ts": rx_msg.timestamp
                    }
                    # Topic 格式: CAN.{channel}.{id} 例如: CAN.can0.0x123
                    topic = f"{service_key}.{self.channel}.{hex(rx_msg.arbitration_id)}".encode()
                    # 注意：ZMQ 发送在异步环境中需小心，此处通过 loop.call_soon_threadsafe 
                    # 或直接使用线程安全的 pub 绑定。为严谨起见，建议在独立线程使用专用 socket。
                    pub_sock.send_multipart([topic, self.pack(frame)])

            except Exception as e:
                self.logger.error(f"通道 {self.channel} 运行时异常: {e}")
                time.sleep(0.1)

class CanService(BaseIOService):
    def __init__(self):
        super().__init__("CAN")
        self.handlers = {} # {channel_name: CanChannelHandler}
        
    async def main_loop(self):
        # 1. 准备发布和响应套接字
        pub_sock = self.ctx.socket(zmq.PUB)
        pub_sock.bind(self.get_addr(is_pub=True))
        
        rep_sock = self.ctx.socket(zmq.REP)
        rep_sock.bind(self.get_addr())

        # 2. 配置并启动多通道 (实际应从配置文件读取)
        # 示例：启动一个虚拟口和一个实际口
        ch_configs = [
            {"channel": "vcan0", "bustype": "virtual", "bitrate": 500000},
            # {"channel": "PCAN_USBBUS1", "bustype": "pcan", "bitrate": 500000}
        ]

        for cfg in ch_configs:
            handler = CanChannelHandler(
                cfg['channel'], cfg['bustype'], cfg['bitrate'], 
                self.logger, self.pack
            )
            self.handlers[cfg['channel']] = handler
            # 为每个通道启动独立的硬件隔离线程
            threading.Thread(target=handler.run_hardware_loop, args=(pub_sock, self.service_key), daemon=True).start()

        self.logger.info("CAN 多通道服务已就绪")

        # 3. 响应指令循环 (写操作、订阅管理)
        while self.running:
            raw = await rep_sock.recv()
            req = self.unpack(raw)
            op = req.get('op')

            if op == 'write':
                ch = req.get('ch')
                if ch in self.handlers:
                    self.handlers[ch].write_queue.put(req)
                    await rep_sock.send(self.pack({"status": "ok"}))
                else:
                    await rep_sock.send(self.pack({"status": "error", "msg": "Channel not found"}))
            
            elif op == 'info':
                await rep_sock.send(self.pack({"channels": list(self.handlers.keys())}))

if __name__ == "__main__":
    CanService().start()