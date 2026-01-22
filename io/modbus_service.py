import asyncio
import zmq
import json
from pymodbus.client import ModbusTcpClient, ModbusSerialClient

class ConnectionPool:
    """自动管理不同 host/port 的 Modbus 实例"""
    def __init__(self, logger):
        self.logger = logger
        self.pool = {} # {(type, host, port): client}

    def get_client(self, cfg):
        key = (cfg.get('type', 'tcp'), cfg.get('host'), cfg.get('port'))
        if key not in self.pool:
            if key[0] == 'tcp':
                self.pool[key] = ModbusTcpClient(key[1], port=key[2] or 502, timeout=2)
            else:
                self.pool[key] = ModbusSerialClient(port=key[2], baudrate=cfg.get('baudrate', 9600))
            self.logger.info(f"已建立新物理连接池项: {key}")
        return self.pool[key]

class PriorityTask:
    """带有优先级的任务封装"""
    def __init__(self, priority, future, func, *args):
        self.priority = priority
        self.future = future # 用于将结果返回给 REP 协程
        self.func = func
        self.args = args

    def __lt__(self, other):
        return self.priority < other.priority

class ModbusService(BaseIOService):
    def __init__(self):
        super().__init__("MODBUS")
        self.conn_pool = ConnectionPool(self.logger)
        self.task_queue = asyncio.PriorityQueue()
        self.subscriptions = {} # 订阅表

    async def worker(self):
        """串行执行器：确保单个物理通道同一时间只有一个指令，但按优先级排队"""
        while self.running:
            task = await self.task_queue.get()
            try:
                result = await task.func(*task.args)
                task.future.set_result(result)
            except Exception as e:
                task.future.set_exception(e)
            finally:
                self.task_queue.task_done()

    async def do_write(self, cfg, slave, addr, val):
        client = self.conn_pool.get_client(cfg)
        if not client.connected: client.connect()
        # 物理写操作
        res = client.write_register(addr, val, slave=slave)
        return {"status": "ok"} if not res.isError() else {"status": "error", "msg": str(res)}

    async def main_loop(self):
        # 启动后台 Worker 处理优先级任务
        asyncio.create_task(self.worker())
        
        rep_sock = self.ctx.socket(zmq.REP)
        rep_sock.bind(self.get_addr())
        
        self.logger.info(f"Modbus 工业服务就绪，等待指令...")

        while self.running:
            msg = await rep_sock.recv()
            req = self.unpack(msg)
            
            if req['op'] == 'write':
                # 创建一个 Future 用于接收异步执行结果
                fut = asyncio.get_running_loop().create_future()
                # 优先级 0 最高 (紧急写)，10 普通写
                priority = req.get('priority', 10)
                
                await self.task_queue.put(PriorityTask(
                    priority, fut, self.do_write, 
                    req['config'], req['slave'], req['addr'], req['val']
                ))
                
                # 等待队列处理完成并回包
                try:
                    res = await asyncio.wait_for(fut, timeout=5.0)
                    await rep_sock.send(self.pack(res))
                except Exception as e:
                    await rep_sock.send(self.pack({"status": "error", "msg": str(e)}))

            elif req['op'] == 'subscribe':
                # 订阅逻辑...
                await rep_sock.send(self.pack({"status": "ok"}))

if __name__ == "__main__":
    ModbusService().start()