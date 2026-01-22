'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-22 10:54:38
LastEditors: zhai
LastEditTime: 2026-01-22 10:54:48
'''
import asyncio
import zmq
from common import BaseIOService

class ModbusService(BaseIOService):
    def __init__(self):
        super().__init__("MODBUS")
        # 模拟 Modbus 寄存器存储
        self._registers = {i: 0 for i in range(100)}

    async def main_loop(self):
        # 使用 REP 模式响应请求
        rep_sock = self.ctx.socket(zmq.REP)
        bind_addr = self.get_bind_address()
        rep_sock.bind(bind_addr)

        self.logger.info("Modbus 读写服务启动完成")

        while self.running:
            try:
                # 1. 接收请求
                raw_msg = await rep_sock.recv()
                req = self.unpack(raw_msg)
                
                # 2. 处理业务逻辑
                op = req.get("op")
                addr = req.get("addr", 0)
                
                resp = {"status": "err", "msg": "unknown op"}

                if op == "read":
                    val = self._registers.get(addr, 0)
                    resp = {"status": "ok", "val": val}
                    # self.logger.debug(f"Read Addr {addr} -> {val}")
                
                elif op == "write":
                    val = req.get("val", 0)
                    self._registers[addr] = val
                    resp = {"status": "ok"}
                    self.logger.info(f"Write Addr {addr} <- {val}")

                # 3. 发送响应
                await rep_sock.send(self.pack(resp))

            except zmq.ZMQError as e:
                if self.running: self.logger.error(f"ZMQ 错误: {e}")
            except Exception as e:
                self.logger.error(f"Modbus 处理错误: {e}")
                # REP 模式必须一问一答，出错也要尝试回包，否则客户端会卡死
                try:
                    await rep_sock.send(self.pack({"status": "fatal", "msg": str(e)}))
                except:
                    pass

if __name__ == "__main__":
    service = ModbusService()
    service.start()