'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-22 10:54:24
LastEditors: zhai
LastEditTime: 2026-01-22 10:55:45
'''
import asyncio
import random
import time
import zmq
from common import BaseIOService, CONF

class CanService(BaseIOService):
    def __init__(self):
        super().__init__("CAN")

    async def main_loop(self):
        # 使用 PUB 模式广播数据
        pub_sock = self.ctx.socket(zmq.PUB)
        bind_addr = self.get_bind_address()
        pub_sock.bind(bind_addr)

        self.logger.info("CAN 采集服务启动完成")
        
        # 模拟 CAN 总线初始化 (python-can)
        # bus = can.interface.Bus(channel='can0', bustype='socketcan')

        while self.running:
            try:
                # ----------------------------------------
                # 模拟硬件读取 (实际应替换为 bus.recv())
                # ----------------------------------------
                # 模拟 10ms 一帧数据
                await asyncio.sleep(0.01) 
                
                fake_frame = {
                    "id": 0x123,
                    "ts": time.time(),
                    "data": [random.randint(0, 255) for _ in range(8)],
                    "dlc": 8
                }
                
                # 序列化并发送
                # MessagePack 直接支持二进制，极其高效
                payload = self.pack(fake_frame)
                await pub_sock.send(payload)

            except Exception as e:
                self.logger.error(f"CAN 读取循环错误: {e}")
                await asyncio.sleep(1) # 出错后避让

if __name__ == "__main__":
    service = CanService()
    service.start()