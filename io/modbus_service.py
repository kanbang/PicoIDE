import asyncio
import zmq
import zmq.asyncio
import msgpack
import time
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from common import BaseIOService

class ConnectionManager:
    """自动管理 TCP 和 RTU 连接实例"""
    def __init__(self, logger):
        self.clients = {}  # {(type, target): client_instance}
        self.logger = logger

    def get_client(self, config):
        ctype = config.get("type", "tcp")
        target = config.get("host") or config.get("port") # IP 或 COM口
        key = (ctype, target)

        if key not in self.clients:
            if ctype == "tcp":
                self.clients[key] = ModbusTcpClient(config["host"], port=config.get("port", 502))
            else:
                self.clients[key] = ModbusSerialClient(
                    port=config["port"], baudrate=config.get("baudrate", 9600), timeout=1
                )
            self.logger.info(f"创建新连接: {key}")
        
        return self.clients[key]

class ModbusService(BaseIOService):
    def __init__(self):
        super().__init__("MODBUS")
        self.conn_mgr = ConnectionManager(self.logger)
        self.write_queue = asyncio.PriorityQueue() # (priority, task)
        self.cache = {}
        self.subscriptions = {} # {conn_key: {slave: {addr: type}}}

    async def poll_task(self):
        """背景轮询：低优先级执行，但会检查写队列"""
        pub_addr = self.get_addr(5557, "io_modbus_pub").replace("*", "127.0.0.1")
        pub_sock = self.ctx.socket(zmq.PUB)
        pub_sock.bind(pub_addr)

        while self.running:
            # 1. 优先处理写操作队列 (Priority: 0 为最高)
            while not self.write_queue.empty():
                _, (resp_event, config, req) = await self.write_queue.get()
                await self._execute_write(config, req, resp_event)
                self.write_queue.task_done()

            # 2. 处理订阅轮询
            for conn_key, slaves in self.subscriptions.items():
                client = self.conn_mgr.get_client(self._parse_key(conn_key))
                if not client.connected: client.connect()

                for slave, points in slaves.items():
                    # 此处可使用之前写的“批量读取优化算法”
                    for addr, dtype in points.items():
                        # 每次读取前再次检查写队列，实现“瞬时插队”
                        if not self.write_queue.empty(): break
                        
                        try:
                            count = 2 if "32" in dtype else 1
                            res = client.read_holding_registers(addr, count, slave=slave)
                            if not res.isError():
                                self.cache[(conn_key, slave, addr)] = res.registers
                                # 推送数据 (省略推送逻辑)
                        except Exception as e:
                            self.logger.error(f"轮询失败 {conn_key}: {e}")
            
            await asyncio.sleep(0.01) # 极短休眠，保持高响应

    async def _execute_write(self, config, req, resp_event):
        """执行实际的写操作并触发响应事件"""
        client = self.conn_mgr.get_client(config)
        try:
            if not client.connected: client.connect()
            slave, addr, val = req['slave'], req['addr'], req['val']
            # 根据数据类型转换 (此处简化)
            res = client.write_register(addr, val, slave=slave)
            
            # 将结果存入事件对象返回给 main_loop
            resp_event.result = {"status": "ok"} if not res.isError() else {"status": "err", "msg": str(res)}
        except Exception as e:
            resp_event.result = {"status": "err", "msg": str(e)}
        finally:
            resp_event.set()

    def _parse_key(self, key_str):
        # 辅助方法：将 key 还原为配置字典
        import json
        return json.loads(key_str)

    async def main_loop(self):
        asyncio.create_task(self.poll_task())
        rep_sock = self.ctx.socket(zmq.REP)
        rep_sock.bind(self.get_bind_address())

        while self.running:
            raw = await rep_sock.recv()
            req = self.unpack(raw)
            
            if req['op'] == 'write':
                # 写操作处理：入队并创建同步事件
                resp_event = asyncio.Event()
                resp_event.result = None
                # (优先级, (事件, 配置, 请求内容)) -> 0 表示最高优先级
                priority = req.get("priority", 0)
                await self.write_queue.put((priority, (resp_event, req['config'], req)))
                
                # 等待 poll_task 处理完成
                await resp_event.wait()
                await rep_sock.send(self.pack(resp_event.result))
            
            elif req['op'] == 'subscribe':
                # 更新订阅表 (使用 config 作为 key)
                import json
                ckey = json.dumps(req['config'], sort_keys=True)
                if ckey not in self.subscriptions: self.subscriptions[ckey] = {}
                # ... 更新逻辑 ...
                await rep_sock.send(self.pack({"status": "ok"}))

if __name__ == "__main__":
    service = ModbusService()
    service.start()