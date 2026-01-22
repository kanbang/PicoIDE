import asyncio
import zmq
import zmq.asyncio
import time
from pymodbus.client import ModbusTcpClient, ModbusSerialClient
from common import BaseIOService
from config_loader import config

class ConnectionPool:
    """自动管理多台硬件设备的连接实例"""
    def __init__(self, logger):
        self.logger = logger
        self.clients = {}  # {(type, host, port): client}

    def get_client(self, cfg):
        ctype = cfg.get('type', 'tcp')
        host = cfg.get('host', '127.0.0.1')
        port = cfg.get('port', 502)
        key = (ctype, host, port)

        if key not in self.clients:
            if ctype == 'tcp':
                self.clients[key] = ModbusTcpClient(host, port=port, timeout=2)
            else:
                self.clients[key] = ModbusSerialClient(port=port, baudrate=cfg.get('baudrate', 9600))
            self.logger.info(f"建立物理连接池项: {key}")
        return self.clients[key]

class PriorityTask:
    """任务封装：支持优先级比较"""
    def __init__(self, priority, future, func, args):
        self.priority = priority
        self.future = future
        self.func = func
        self.args = args
    def __lt__(self, other): return self.priority < other.priority

class ModbusService(BaseIOService):
    def __init__(self):
        super().__init__("modbus")
        self.conn_pool = ConnectionPool(self.logger)
        self.task_queue = asyncio.PriorityQueue()
        self.subscriptions = {} # { (conn_key, slave, addr): {"type": dtype, "last_val": None} }
        self.cache = {}         # { (conn_key, slave, addr): value }

    def _get_conn_key(self, cfg):
        return f"{cfg.get('type','tcp')}://{cfg.get('host','127.0.0.1')}:{cfg.get('port',502)}"

    async def poll_worker(self):
        """背景轮询协程：执行周期性读取并检测变化推送"""
        pub_sock = self.ctx.socket(zmq.PUB)
        pub_sock.bind(self.get_addr(is_pub=True))
        self.logger.info(f"PUB 推送通道已就绪: {self.get_addr(is_pub=True)}")

        # 从配置获取轮询间隔
        poll_interval = config.modbus_config.get('poll_interval', 0.05)

        while self.running:
            # 1. 优先消耗写操作队列
            while not self.task_queue.empty():
                task = await self.task_queue.get()
                try:
                    res = await task.func(*task.args)
                    task.future.set_result(res)
                except Exception as e:
                    task.future.set_exception(e)
                finally: self.task_queue.task_done()

            # 2. 轮询已订阅的地址
            for (ckey, slave, addr), info in list(self.subscriptions.items()):
                try:
                    # 这里的 ckey 简化处理，实际应解析回 cfg
                    cfg = {"host": ckey.split('://')[1].split(':')[0], "port": int(ckey.split(':')[-1])}
                    client = self.conn_pool.get_client(cfg)
                    if not client.connected: client.connect()

                    count = 2 if "32" in info["type"] else 1
                    res = client.read_holding_registers(addr, count, slave=slave)

                    if not res.isError():
                        val = res.registers
                        # 变化检测 (COV)
                        if val != info["last_val"]:
                            info["last_val"] = val
                            self.cache[(ckey, slave, addr)] = val
                            # 推送消息
                            msg = {"ckey": ckey, "slave": slave, "addr": addr, "val": val, "ts": time.time()}
                            await pub_sock.send_multipart([b"modbus.update", self.pack(msg)])
                except Exception as e:
                    self.logger.error(f"轮询异常: {e}")

            await asyncio.sleep(poll_interval)

    async def do_write(self, cfg, slave, addr, val, dtype):
        """实际硬件写入动作"""
        client = self.conn_pool.get_client(cfg)
        if not client.connected: client.connect()
        # pymodbus v3.x API: write_register(address, value, slave=slave)
        res = client.write_register(address=addr, value=int(val), slave=slave)
        return {"status": "ok"} if not res.isError() else {"status": "error", "msg": str(res)}

    async def main_loop(self):
        asyncio.create_task(self.poll_worker())
        
        rep_sock = self.ctx.socket(zmq.REP)
        rep_sock.bind(self.get_addr())

        while self.running:
            raw = await rep_sock.recv()
            req = self.unpack(raw)
            op = req.get('op')

            if op == 'write':
                fut = asyncio.get_running_loop().create_future()
                # 优先级 0 最高
                await self.task_queue.put(PriorityTask(0, fut, self.do_write, 
                    (req['config'], req['slave'], req['addr'], req['val'], req.get('type','uint16'))))
                res = await asyncio.wait_for(fut, timeout=3.0)
                await rep_sock.send(self.pack(res))

            elif op == 'subscribe':
                ckey = self._get_conn_key(req['config'])
                for t in req['tasks']:
                    self.subscriptions[(ckey, req['slave'], t['addr'])] = {"type": t['type'], "last_val": None}
                await rep_sock.send(self.pack({"status": "ok", "msg": "Subscribed"}))
            
            elif op == 'read_cache':
                # 瞬间返回本地缓存镜像
                await rep_sock.send(self.pack({"status": "ok", "cache": str(self.cache)}))

if __name__ == "__main__":
    ModbusService().start()