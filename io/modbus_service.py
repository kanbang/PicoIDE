import asyncio
import zmq
import zmq.asyncio
import time
import random
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
        # 重试配置
        self.max_retries = config.modbus_config.get('max_retries', 3)
        self.retry_delay_base = config.modbus_config.get('retry_delay_base', 0.5)  # 指数退避基础延迟 (s)

    def _get_conn_key(self, cfg):
        return f"{cfg.get('type','tcp')}://{cfg.get('host','127.0.0.1')}:{cfg.get('port',502)}"

    async def reconnect(self, client):
        """重连逻辑：指数退避重试"""
        for attempt in range(self.max_retries):
            try:
                if client.connected:
                    client.close()
                if client.connect():
                    self.logger.info("Modbus 连接重置成功")
                    return True
                else:
                    delay = self.retry_delay_base * (2 ** attempt) + random.uniform(0, 0.1)  # 抖动避免同步风暴
                    self.logger.warning(f"连接重试 {attempt+1}/{self.max_retries} 失败，等待 {delay:.2f}s")
                    await asyncio.sleep(delay)
            except Exception as e:
                self.logger.error(f"重连异常: {e}")
        self.logger.error("达到最大重试次数，连接失败")
        return False

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
                success = False
                for attempt in range(self.max_retries):
                    try:
                        # 解析 ckey 回 cfg
                        parts = ckey.split('://')
                        if len(parts) != 2:
                            raise ValueError(f"Invalid connection key: {ckey}")
                        ctype = parts[0]
                        host_port = parts[1].split(':')
                        if len(host_port) != 2:
                            raise ValueError(f"Invalid host:port in key: {ckey}")
                        host, port_str = host_port
                        try:
                            port = int(port_str)
                        except ValueError:
                            raise ValueError(f"Invalid port in key: {ckey}")
                        cfg = {'type': ctype, 'host': host, 'port': port}

                        client = self.conn_pool.get_client(cfg)
                        if not client.connected:
                            if not await self.reconnect(client):
                                break  # 跳过此订阅项

                        count = 2 if "32" in info["type"] else 1
                        res = client.read_holding_registers(address=addr, count=count, slave=slave)

                        if res.isError():
                            raise RuntimeError(f"Modbus read error: {res}")

                        val = res.registers
                        # 变化检测 (COV)
                        if val != info["last_val"]:
                            info["last_val"] = val
                            self.cache[(ckey, slave, addr)] = val
                            # 推送消息
                            msg = {"ckey": ckey, "slave": slave, "addr": addr, "val": val, "ts": time.time()}
                            await pub_sock.send_multipart([b"modbus.update", self.pack(msg)])
                        success = True
                        break  # 成功后退出重试
                    except Exception as e:
                        self.logger.warning(f"轮询重试 {attempt+1}/{self.max_retries}: {e}")
                        delay = self.retry_delay_base * (2 ** attempt) + random.uniform(0, 0.1)
                        await asyncio.sleep(delay)
                if not success:
                    self.logger.error(f"轮询失败，已达到最大重试: {ckey}, slave={slave}, addr={addr}")

            await asyncio.sleep(poll_interval)

    async def do_write(self, cfg, slave, addr, val, dtype):
        """实际硬件写入动作"""
        client = self.conn_pool.get_client(cfg)
        success = False
        for attempt in range(self.max_retries):
            try:
                if not client.connected:
                    if not await self.reconnect(client):
                        break

                # pymodbus API: write_register(address, value, slave=slave)
                res = client.write_register(address=addr, value=int(val), slave=slave)
                if res.isError():
                    raise RuntimeError(f"Modbus write error: {res}")
                success = True
                return {"status": "ok"}
            except ValueError as e:
                self.logger.error(f"Value conversion error: {e}")
                return {"status": "error", "msg": str(e)}
            except Exception as e:
                self.logger.warning(f"写重试 {attempt+1}/{self.max_retries}: {e}")
                delay = self.retry_delay_base * (2 ** attempt) + random.uniform(0, 0.1)
                await asyncio.sleep(delay)
        if not success:
            self.logger.error("写操作失败，已达到最大重试")
            return {"status": "error", "msg": "Max retries reached"}

    async def main_loop(self):
        asyncio.create_task(self.poll_worker())
        
        rep_sock = self.ctx.socket(zmq.REP)
        rep_sock.bind(self.get_addr())

        while self.running:
            try:
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
                    await rep_sock.send(self.pack({"status": "ok", "cache": self.cache}))

                else:
                    await rep_sock.send(self.pack({"status": "error", "msg": "Unknown operation"}))
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                await rep_sock.send(self.pack({"status": "error", "msg": str(e)}))

if __name__ == "__main__":
    ModbusService().start()