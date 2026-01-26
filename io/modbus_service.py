import asyncio
import zmq
import time
import random
import urllib.parse
import traceback
from pymodbus.client.mixin import ModbusClientMixin
from pymodbus.client import AsyncModbusTcpClient, AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException, ConnectionException
from common import BaseIOService
from config_loader import config

class ConnectionPool:
    """
    Manages a pool of connection instances for multiple hardware devices.
    Ensures efficient reuse of connections with locking for concurrency safety.
    Supports automatic cleanup of inactive connections to prevent resource leaks.
    """
    def __init__(self, logger, cleanup_interval=300, max_idle_time=600):
        self.logger = logger
        self.clients = {}  # key: (client, lock, last_used)
        self.cleanup_interval = cleanup_interval  # cleanup check interval in seconds
        self.max_idle_time = max_idle_time  # max idle time before cleanup in seconds

    async def get_client(self, cfg):
        """
        Retrieves or creates a client for the given configuration.
        Updates last_used timestamp on each access.
        """
        ctype = cfg.get("type", "tcp")
        host = cfg.get("host", "127.0.0.1")
        port = cfg.get("port", 502)
        if ctype == "serial":
            key = (ctype, port, cfg.get("baudrate", 9600))
        else:
            key = (ctype, host, port)
        if key not in self.clients:
            if ctype == "tcp":
                client = AsyncModbusTcpClient(host, port=port)
            else:
                client = AsyncModbusSerialClient(
                    port=port,
                    baudrate=cfg.get("baudrate", 9600),
                    parity=cfg.get("parity", "N"),
                    bytesize=cfg.get("bytesize", 8),
                    stopbits=cfg.get("stopbits", 1),
                )
            lock = asyncio.Lock()
            self.clients[key] = (client, lock, time.time())
            self.logger.info(f"Created connection pool entry: {key}")
        else:
            # Update last_used timestamp
            client, lock, _ = self.clients[key]
            self.clients[key] = (client, lock, time.time())
        return self.clients[key]

    async def cleanup_inactive(self):
        """
        Cleanup inactive connections that haven't been used for max_idle_time seconds.
        This method should be called periodically by a background task.
        """
        current_time = time.time()
        keys_to_remove = []

        for key, (client, lock, last_used) in self.clients.items():
            idle_time = current_time - last_used
            if idle_time > self.max_idle_time:
                keys_to_remove.append(key)
                try:
                    await client.close()
                    self.logger.info(f"Closed inactive connection: {key} (idle for {idle_time:.1f}s)")
                except Exception as e:
                    self.logger.error(f"Error closing connection {key}: {e}")

        for key in keys_to_remove:
            del self.clients[key]

        if keys_to_remove:
            self.logger.info(f"Cleanup completed: removed {len(keys_to_remove)} inactive connection(s), {len(self.clients)} remaining")

    async def close_all(self):
        """
        Close all connections in the pool. Should be called during shutdown.
        """
        for key, (client, lock, _) in list(self.clients.items()):
            try:
                await client.close()
                self.logger.info(f"Closed connection: {key}")
            except Exception as e:
                self.logger.error(f"Error closing connection {key}: {e}")
        self.clients.clear()

class PriorityTask:
    """
    Task wrapper for priority queue comparison.
    """
    def __init__(self, priority, future, func, args):
        self.priority = priority
        self.future = future
        self.func = func
        self.args = args

    def __lt__(self, other):
        return self.priority < other.priority

# 策略模式: RegisterReader接口
class RegisterReader:
    async def read(self, client, addr, count, slave):
        raise NotImplementedError

class HoldingReader(RegisterReader):
    async def read(self, client, addr, count, slave):
        res = await client.read_holding_registers(address=addr, count=count, device_id=slave)
        if res.isError():
            raise RuntimeError(f"Modbus read error: {res}")
        return res.registers

class InputReader(RegisterReader):
    async def read(self, client, addr, count, slave):
        res = await client.read_input_registers(address=addr, count=count, device_id=slave)
        if res.isError():
            raise RuntimeError(f"Modbus read error: {res}")
        return res.registers

class CoilReader(RegisterReader):
    async def read(self, client, addr, count, slave):
        res = await client.read_coils(address=addr, count=count, device_id=slave)
        if res.isError():
            raise RuntimeError(f"Modbus read error: {res}")
        return res.bits[:count]

class DiscreteReader(RegisterReader):
    async def read(self, client, addr, count, slave):
        res = await client.read_discrete_inputs(address=addr, count=count, device_id=slave)
        if res.isError():
            raise RuntimeError(f"Modbus read error: {res}")
        return res.bits[:count]

# 策略模式: RegisterWriter接口
class RegisterWriter:
    async def write(self, client, addr, payload, slave):
        raise NotImplementedError

class HoldingWriter(RegisterWriter):
    async def write(self, client, addr, payload, slave):
        if len(payload) > 1:
            res = await client.write_registers(address=addr, values=payload, device_id=slave)
        else:
            res = await client.write_register(address=addr, value=payload[0], device_id=slave)
        if res.isError():
            raise RuntimeError(f"Modbus write error: {res}")

class CoilWriter(RegisterWriter):
    async def write(self, client, addr, payload, slave):
        # Support both single bool value and list of bools for batch write
        if isinstance(payload, list):
            if not all(isinstance(v, bool) for v in payload):
                raise ValueError("All coil values must be bool")
            res = await client.write_coils(address=addr, values=payload, device_id=slave)
        else:
            if not isinstance(payload, bool):
                raise ValueError("Coil value must be bool")
            res = await client.write_coil(address=addr, value=payload, device_id=slave)
        if res.isError():
            raise RuntimeError(f"Modbus write error: {res}")

# 命令模式: OpHandler接口
class OpHandler:
    async def handle(self, service, req, send_response):
        raise NotImplementedError

class WriteHandler(OpHandler):
    async def handle(self, service, req, send_response):
        register_type = req.get("register_type", "holding")
        slave = req.get("slave", 1)
        addr = req["addr"]
        val = req["val"]
        dtype = req.get("type", "uint16")
        priority = req.get("priority", 1)
        if not isinstance(priority, int):
            await send_response({"status": "error", "msg": "Invalid priority type"})
            return
        if not all(isinstance(x, int) for x in [slave, addr]):
            await send_response({"status": "error", "msg": "Invalid slave or addr type"})
            return
        fut = asyncio.get_running_loop().create_future()
        if not await service.put_task_with_timeout(PriorityTask(priority, fut, service.do_write, (req["config"], slave, addr, val, dtype, register_type))):
            await send_response({"status": "error", "msg": "Service busy, retry later"})
            return
        try:
            res = await asyncio.wait_for(fut, timeout=10.0)
        except asyncio.TimeoutError:
            if not fut.done():
                fut.cancel()
            res = {"status": "error", "msg": "Operation timeout"}
        await send_response(res)

class BatchWriteHandler(OpHandler):
    async def handle(self, service, req, send_response):
        slave = req.get("slave", 1)
        tasks = req["tasks"]
        priority = req.get("priority", 1)
        if not isinstance(priority, int):
            await send_response({"status": "error", "msg": "Invalid priority type"})
            return
        if not isinstance(slave, int):
            await send_response({"status": "error", "msg": "Invalid slave type"})
            return
        for t in tasks:
            if not isinstance(t["addr"], int):
                await send_response({"status": "error", "msg": "Invalid addr in tasks"})
                return
        fut = asyncio.get_running_loop().create_future()
        if not await service.put_task_with_timeout(PriorityTask(priority, fut, service.do_batch_write, (req["config"], slave, tasks))):
            await send_response({"status": "error", "msg": "Service busy, retry later"})
            return
        try:
            res = await asyncio.wait_for(fut, timeout=10.0)
        except asyncio.TimeoutError:
            fut.cancel()
            res = {"status": "error", "msg": "Operation timeout"}
        await send_response(res)

class SubscribeHandler(OpHandler):
    async def handle(self, service, req, send_response):
        ckey = service._get_conn_key(req["config"])
        slave = req.get("slave", 1)
        if not isinstance(slave, int):
            await send_response({"status": "error", "msg": "Invalid slave type"})
            return
        for t in req["tasks"]:
            register_type = t.get("register_type", "holding")
            addr = t["addr"]
            if not isinstance(addr, int):
                await send_response({"status": "error", "msg": "Invalid addr in tasks"})
                return
            service.subscriptions[(ckey, slave, addr)] = {"type": t["type"], "last_val": None, "register_type": register_type}
        await send_response({"status": "ok", "msg": "Subscribed"})

class ReadCacheHandler(OpHandler):
    async def handle(self, service, req, send_response):
        cache_str_key = {f"{ckey}:{slave}:{addr}": val for (ckey, slave, addr), val in service.cache.items()}
        await send_response({"status": "ok", "cache": cache_str_key})

class ReadHandler(OpHandler):
    async def handle(self, service, req, send_response):
        ckey = service._get_conn_key(req["config"])
        slave = req.get("slave", 1)
        addr = req["addr"]
        dtype = req.get("type", "uint16")
        cache_it = req.get("cache_it", True)
        register_type = req.get("register_type", "holding")
        priority = req.get("priority", 1)
        if not isinstance(priority, int):
            await send_response({"status": "error", "msg": "Invalid priority type"})
            return
        if not all(isinstance(x, int) for x in [slave, addr]):
            await send_response({"status": "error", "msg": "Invalid slave or addr type"})
            return
        key = (ckey, slave, addr)
        if key in service.cache:
            res = {"status": "ok", "val": service.cache[key]}
            await send_response(res)
        else:
            fut = asyncio.get_running_loop().create_future()
            if not await service.put_task_with_timeout(PriorityTask(priority, fut, service.do_read, (req["config"], slave, addr, dtype, cache_it, register_type))):
                await send_response({"status": "error", "msg": "Service busy, retry later"})
                return
            try:
                res = await asyncio.wait_for(fut, timeout=10.0)
            except asyncio.TimeoutError:
                fut.cancel()
                res = {"status": "error", "msg": "Operation timeout"}
            await send_response(res)

class BatchReadHandler(OpHandler):
    async def handle(self, service, req, send_response):
        slave = req.get("slave", 1)
        tasks = req["tasks"]
        priority = req.get("priority", 1)
        if not isinstance(priority, int):
            await send_response({"status": "error", "msg": "Invalid priority type"})
            return
        if not isinstance(slave, int):
            await send_response({"status": "error", "msg": "Invalid slave type"})
            return
        for t in tasks:
            if not isinstance(t["addr"], int):
                await send_response({"status": "error", "msg": "Invalid addr in tasks"})
                return
        cache_it = req.get("cache_it", True)
        fut = asyncio.get_running_loop().create_future()
        if not await service.put_task_with_timeout(PriorityTask(priority, fut, service.do_batch_read, (req["config"], slave, tasks, cache_it))):
            await send_response({"status": "error", "msg": "Service busy, retry later"})
            return
        try:
            res = await asyncio.wait_for(fut, timeout=10.0)
        except asyncio.TimeoutError:
            fut.cancel()
            res = {"status": "error", "msg": "Operation timeout"}
        await send_response(res)

class SetHeartbeatHandler(OpHandler):
    async def handle(self, service, req, send_response):
        ckey = service._get_conn_key(req["config"])
        heartbeat_slave = req.get("heartbeat_slave", 1)
        heartbeat_addr = req.get("heartbeat_addr", service.default_heartbeat_addr)
        if not all(isinstance(x, int) for x in [heartbeat_slave, heartbeat_addr]):
            await send_response({"status": "error", "msg": "Invalid heartbeat slave or addr type"})
            return
        service.heartbeat_slaves[ckey] = heartbeat_slave
        service.heartbeat_addrs[ckey] = heartbeat_addr
        if ckey not in service.heartbeat_tasks:
            service.heartbeat_tasks[ckey] = asyncio.create_task(service.heartbeat_worker(ckey))
        await send_response({"status": "ok", "msg": "Heartbeat set"})

# 策略模式: ZmqSendStrategy 接口
class ZmqSendStrategy:
    async def send(self, sock, client_id, packed_res):
        raise NotImplementedError

class RouterSend(ZmqSendStrategy):
    async def send(self, sock, client_id, packed_res):
        await sock.send_multipart([client_id, b'', packed_res])

class RepSend(ZmqSendStrategy):
    async def send(self, sock, client_id, packed_res):
        await sock.send(packed_res)

# 策略模式: ZmqRecvStrategy 接口
class ZmqRecvStrategy:
    async def recv(self, sock):
        raise NotImplementedError

class RouterRecv(ZmqRecvStrategy):
    async def recv(self, sock):
        client_id, _, raw = await sock.recv_multipart()
        return client_id, raw

class RepRecv(ZmqRecvStrategy):
    async def recv(self, sock):
        raw = await sock.recv()
        return b'', raw

class ZmqServerStrategy:
    def __init__(self, sock_type, bind_addr, logger):
        self.sock = zmq.asyncio.Context.instance().socket(sock_type)
        self.sock.bind(bind_addr)
        logger.info(f"{sock_type} socket ready: {bind_addr}")
        self.send_strategy = None
        self.recv_strategy = None

class RouterStrategy(ZmqServerStrategy):
    def __init__(self, bind_addr, logger):
        super().__init__(zmq.ROUTER, bind_addr, logger)
        self.send_strategy = RouterSend()
        self.recv_strategy = RouterRecv()

class RepStrategy(ZmqServerStrategy):
    def __init__(self, bind_addr, logger):
        super().__init__(zmq.REP, bind_addr, logger)
        self.send_strategy = RepSend()
        self.recv_strategy = RepRecv()

class ModbusService(BaseIOService):
    """
    Asynchronous Modbus service for handling device communications.
    Supports TCP and serial connections, subscriptions, reads/writes, batch operations, and heartbeats.
    Designed for industrial-grade reliability with retries, locking, and error handling.
    """
    def __init__(self):
        super().__init__("modbus")
        self.zmq_mode = config.get('zmq_mode', 'router')  # 'router' (default) or 'rep'
        self.logger.info(f"Using ZeroMQ mode: {self.zmq_mode}")
        self.zmq_strategies = {
            'router': RouterStrategy,
            'rep': RepStrategy
        }
        strategy_class = self.zmq_strategies.get(self.zmq_mode)
        if not strategy_class:
            raise ValueError(f"Unsupported zmq_mode: {self.zmq_mode}")
        self.zmq_strategy = strategy_class(self.get_addr(), self.logger)

        self.conn_pool = ConnectionPool(self.logger)
        self.task_queue = asyncio.PriorityQueue(maxsize=100)  # Limited size for backpressure
        self.subscriptions = {}  # (conn_key, slave, addr): {"type": dtype, "last_val": None, "register_type": reg_type}
        self.cache = {}  # (conn_key, slave, addr): value

        self.max_retries = config.modbus_config.get("max_retries", 3)
        self.retry_delay_base = config.modbus_config.get("retry_delay_base", 0.5)
        self.poll_interval = config.modbus_config.get("poll_interval", 0.1)
        self.heartbeat_interval = config.modbus_config.get("heartbeat_interval", 10)
        self.default_heartbeat_addr = config.modbus_config.get("heartbeat_addr", 0)
        self.heartbeat_tasks = {}  # conn_key: heartbeat_task
        self.heartbeat_slaves = {}  # conn_key: slave_id
        self.heartbeat_addrs = {}  # conn_key: addr
        self.word_order = 'big'  # Configurable byte order
        self.dtype_map = {
            "uint16": ModbusClientMixin.DATATYPE.UINT16,
            "int16": ModbusClientMixin.DATATYPE.INT16,
            "uint32": ModbusClientMixin.DATATYPE.UINT32,
            "int32": ModbusClientMixin.DATATYPE.INT32,
            "float32": ModbusClientMixin.DATATYPE.FLOAT32,
            "float64": ModbusClientMixin.DATATYPE.FLOAT64,
            "uint64": ModbusClientMixin.DATATYPE.UINT64,
            "int64": ModbusClientMixin.DATATYPE.INT64,
            "string": ModbusClientMixin.DATATYPE.STRING,
            "bits": ModbusClientMixin.DATATYPE.BITS,
        }
        self.max_registers = 125  # Modbus standard limit
        self.gap_threshold = 10  # Gap threshold for batching
        self.send_queue = asyncio.Queue(maxsize=100)  # Limited size for backpressure
        self.task_put_timeout = config.modbus_config.get("task_put_timeout", 5.0)  # Timeout for queue put
        # Task references
        self.polling_task = None
        self.sender_task = None
        self.processor_task = None
        self.cleanup_task = None
        self.sock = self.zmq_strategy.sock  # Set from strategy

        # Register readers and writers
        self.register_readers = {
            "holding": HoldingReader(),
            "input": InputReader(),
            "coil": CoilReader(),
            "discrete": DiscreteReader()
        }
        self.register_writers = {
            "holding": HoldingWriter(),
            "coil": CoilWriter()
        }

        # Op handlers
        self.op_handlers = {
            "write": WriteHandler(),
            "batch_write": BatchWriteHandler(),
            "subscribe": SubscribeHandler(),
            "read_cache": ReadCacheHandler(),
            "read": ReadHandler(),
            "batch_read": BatchReadHandler(),
            "set_heartbeat": SetHeartbeatHandler()
        }

    def _get_conn_key(self, cfg):
        """
        Generates a connection key from configuration.
        """
        ctype = cfg.get('type', 'tcp')
        if ctype == "serial":
            return f"{ctype}://{cfg.get('port')}:{cfg.get('baudrate', 9600)}"
        return f"{ctype}://{cfg.get('host','127.0.0.1')}:{cfg.get('port',502)}"

    def _parse_conn_key(self, ckey):
        """
        Parses connection key back to configuration dict.
        Returns None on error.
        """
        try:
            parsed = urllib.parse.urlparse(ckey)
            if not parsed.scheme or not parsed.port:
                raise ValueError(f"Invalid connection key: {ckey}")
            if parsed.scheme == "serial":
                parts = parsed.netloc.split(':') if parsed.netloc else parsed.path.split(':')
                return {"type": parsed.scheme, "port": parts[0], "baudrate": int(parts[1])}
            return {"type": parsed.scheme, "host": parsed.hostname, "port": parsed.port}
        except Exception as e:
            self.logger.error(f"Parse conn_key error: {e}")
            return None

    async def retry_operation(self, func, *args, log_msg="操作"):
        """
        Retries an operation with exponential backoff.
        """
        for attempt in range(self.max_retries):
            try:
                return await func(*args)
            except (ModbusException, ConnectionException) as e:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.retry_delay_base * (2**attempt) + random.uniform(0, 0.1)
                self.logger.warning(f"{log_msg} retry {attempt+1}/{self.max_retries}: {e}, waiting {delay:.2f}s")
                await asyncio.sleep(delay)
            except Exception as e:
                self.logger.error(f"Unexpected error in {log_msg}: {e}")
                self.logger.error(traceback.format_exc())
                raise

    async def put_task_with_timeout(self, task):
        """
        Puts a task to the queue with timeout.
        Returns False if timeout occurs, True otherwise.
        """
        try:
            await asyncio.wait_for(self.task_queue.put(task), timeout=self.task_put_timeout)
            return True
        except asyncio.TimeoutError:
            self.logger.warning(f"Task queue full, task rejected (timeout={self.task_put_timeout}s)")
            return False

    async def reconnect(self, client, log_msg="重连"):
        """
        Reconnects the client.
        """
        async def connect_func():
            if client.connected:
                await client.close()
            if not await client.connect():
                raise ConnectionException("Connection failed")
            self.logger.info(f"{log_msg} successful")
            return True
        return await self.retry_operation(connect_func, log_msg=log_msg)

    async def heartbeat_worker(self, ckey):
        """
        Heartbeat coroutine for each connection to detect liveness.
        """
        cfg = self._parse_conn_key(ckey)
        if cfg is None:
            return
        client, lock, _ = await self.conn_pool.get_client(cfg)
        slave = self.heartbeat_slaves.get(ckey, 1)
        addr = self.heartbeat_addrs.get(ckey, self.default_heartbeat_addr)
        while self.running:
            async with lock:
                try:
                    if not client.connected:
                        await self.reconnect(client, log_msg=f"Heartbeat reconnect {ckey}")
                    await client.read_holding_registers(address=addr, count=1, device_id=slave)
                except Exception as e:
                    self.logger.error(f"Heartbeat failed {ckey}: {e}")
                    self.logger.error(traceback.format_exc())
            await asyncio.sleep(self.heartbeat_interval)

    def _get_dtype_params(self, dtype):
        """
        Returns count and DATATYPE for given dtype.
        Raises ValueError on unsupported dtype.
        """
        dtype = dtype.lower().replace(" ", "")
        if dtype in ["bool", "coil"]:
            return 1, None
        if dtype not in self.dtype_map:
            raise ValueError(f"Unsupported dtype: {dtype}")
        datatype_enum = self.dtype_map[dtype]
        count = datatype_enum.value[1]
        if count == 0:
            raise ValueError(f"Datatype {dtype} requires explicit count specification")
        return count, datatype_enum

    async def _build_batches(self, items, is_write=False):
        """
        Builds batches for reads/writes, considering gaps and limits.
        """
        batches = []
        current_batch = []
        current_start = None
        current_count = 0
        for item in items:
            if is_write:
                addr = item["addr"]
                info = item
            else:
                addr, info = item
            count, _ = self._get_dtype_params(info["type"])
            if not current_batch:
                current_batch = [item]
                current_start = addr
                current_count = count
            else:
                if is_write:
                    prev_addr = current_batch[-1]["addr"]
                    prev_info = current_batch[-1]
                else:
                    prev_addr = current_batch[-1][0]
                    prev_info = current_batch[-1][1]
                prev_count, _ = self._get_dtype_params(prev_info["type"])
                prev_end = prev_addr + prev_count - 1
                gap = addr - (prev_end + 1)
                potential_count = current_count + gap + count
                if (is_write and gap != 0) or (not is_write and (gap > self.gap_threshold or potential_count > self.max_registers)):
                    total_count = prev_end - current_start + 1
                    batches.append((current_start, total_count, current_batch))
                    current_batch = [item]
                    current_start = addr
                    current_count = count
                else:
                    current_batch.append(item)
                    current_count = potential_count
        if current_batch:
            if is_write:
                prev_addr = current_batch[-1]["addr"]
                prev_info = current_batch[-1]
            else:
                prev_addr = current_batch[-1][0]
                prev_info = current_batch[-1][1]
            prev_count, _ = self._get_dtype_params(prev_info["type"])
            prev_end = prev_addr + prev_count - 1
            total_count = prev_end - current_start + 1
            batches.append((current_start, total_count, current_batch))
        return batches

    async def process_group(self, ckey, slave, items):
        """
        Processes polling for a single (ckey, slave) group.
        """
        cfg = self._parse_conn_key(ckey)
        if cfg is None:
            return
        client, lock, _ = await self.conn_pool.get_client(cfg)
        async with lock:
            try:
                if not client.connected:
                    await self.reconnect(client, log_msg=f"Polling reconnect {ckey}")
                grouped_by_reg = {}
                for addr, info in items:
                    reg_type = info.get("register_type", "holding")
                    grouped_by_reg.setdefault(reg_type, []).append((addr, info))
                for reg_type, reg_items in grouped_by_reg.items():
                    reg_items.sort(key=lambda x: x[0])
                    batches = await self._build_batches(reg_items)
                    reader = self.register_readers.get(reg_type)
                    if not reader:
                        raise ValueError(f"Unsupported register_type: {reg_type}")
                    for start_addr, total_count, batch_items in batches:
                        registers = await reader.read(client, start_addr, total_count, slave)
                        for addr, info in batch_items:
                            rel_offset = addr - start_addr
                            count, data_type = self._get_dtype_params(info["type"])
                            vals = registers[rel_offset:rel_offset + count]
                            if len(vals) < count:
                                raise RuntimeError(f"Insufficient data for addr {addr}: expected {count}, got {len(vals)}")
                            if reg_type in ["coil", "discrete"] or data_type is None:
                                val = vals[0] if count == 1 else vals
                            else:
                                val = client.convert_from_registers(vals, data_type, word_order=self.word_order)
                            if val != info["last_val"]:
                                info["last_val"] = val
                                self.cache[(ckey, slave, addr)] = val
                                msg = {"ckey": ckey, "slave": slave, "addr": addr, "val": val, "ts": time.time()}
                                await self.send_queue.put([b"modbus.update", self.pack(msg)])
            except ModbusException as e:
                self.logger.error(f"Modbus exception {ckey} slave={slave}: {e}")
                self.logger.error(traceback.format_exc())
            except ConnectionException as e:
                self.logger.error(f"Connection exception {ckey} slave={slave}: {e}")
                self.logger.error(traceback.format_exc())
            except Exception as e:
                self.logger.error(f"Polling exception {ckey} slave={slave}: {e}")
                self.logger.error(traceback.format_exc())

    async def sender_worker(self, pub_sock):
        """
        Dedicated sender coroutine for publishing messages from queue.
        """
        while self.running:
            try:
                msg_parts = await self.send_queue.get()
                await pub_sock.send_multipart(msg_parts)
                self.send_queue.task_done()
            except Exception as e:
                self.logger.error(f"Send exception: {e}")
                self.logger.error(traceback.format_exc())

    async def processor_worker(self):
        """
        Dedicated processor for handling priority tasks from queue.
        """
        while self.running:
            try:
                task = await self.task_queue.get()
                try:
                    res = await task.func(*task.args)
                    if not task.future.done():
                        task.future.set_result(res)
                except asyncio.CancelledError:
                    if not task.future.done():
                        task.future.set_exception(asyncio.CancelledError("Task cancelled"))
                except Exception as e:
                    self.logger.error(f"Processor task error: {e}")
                    self.logger.error(traceback.format_exc())
                    if not task.future.done():
                        task.future.set_exception(e)
                finally:
                    self.task_queue.task_done()
            except asyncio.CancelledError:
                break

    async def poll_worker(self):
        """
        Background polling coroutine for subscribed addresses.
        """
        pub_sock = self.ctx.socket(zmq.PUB)
        pub_sock.bind(self.get_addr(is_pub=True))
        self.logger.info(f"PUB channel ready: {self.get_addr(is_pub=True)}")
        self.sender_task = asyncio.create_task(self.sender_worker(pub_sock))
        while self.running:
            grouped = {}
            for key, info in self.subscriptions.items():
                ckey, slave, addr = key
                k = (ckey, slave)
                grouped.setdefault(k, []).append((addr, info))
            tasks = []
            for (ckey, slave), items in grouped.items():
                items.sort(key=lambda x: x[0])
                tasks.append(asyncio.create_task(self.process_group(ckey, slave, items)))
            if tasks:
                await asyncio.gather(*tasks)
            await asyncio.sleep(self.poll_interval)

    async def do_write(self, cfg, slave, addr, val, dtype, register_type="holding"):
        """
        Performs a single write operation to hardware.
        """
        self.logger.debug(f"do_write: slave={slave}, addr={addr}, val={val} (type={type(val)}), dtype={dtype}, register_type={register_type}")
        client, lock, _ = await self.conn_pool.get_client(cfg)
        async with lock:
            if not client.connected:
                await self.reconnect(client, log_msg="Write reconnect")
            async def write_func():
                count, data_type = self._get_dtype_params(dtype)
                writer = self.register_writers.get(register_type)
                if not writer:
                    raise ValueError(f"Write not supported for {register_type}")
                converted_val = val
                if data_type is not None and "int" in dtype.lower() and not isinstance(converted_val, int):
                    raise ValueError("Value must be integer for int dtype")
                payload = client.convert_to_registers(converted_val, data_type, word_order=self.word_order) if data_type is not None else [val]
                await writer.write(client, addr, payload, slave)
                return {"status": "ok"}
            try:
                return await self.retry_operation(write_func, log_msg="Write register")
            except ValueError as e:
                self.logger.error(f"Value conversion error: {e}")
                self.logger.error(traceback.format_exc())
                return {"status": "error", "msg": str(e)}

    async def do_batch_write(self, cfg, slave, tasks):
        """
        Performs optimized batch write: sorts, batches continuous addresses.
        """
        if not tasks:
            return {"status": "ok"}
        self.logger.debug(f"do_batch_write: slave={slave}, tasks={tasks}")
        grouped_by_reg = {}
        for task in tasks:
            reg_type = task.get("register_type", "holding")
            grouped_by_reg.setdefault(reg_type, []).append(task)
        partial_results = []
        for reg_type, reg_tasks in grouped_by_reg.items():
            sorted_tasks = sorted(reg_tasks, key=lambda t: t["addr"])
            client, lock, _ = await self.conn_pool.get_client(cfg)
            async with lock:
                if not client.connected:
                    await self.reconnect(client, log_msg="Batch write reconnect")
                batches = await self._build_batches(sorted_tasks, is_write=True)
                writer = self.register_writers.get(reg_type)
                if not writer:
                    partial_results.append({"status": "error", "msg": f"Batch write not supported for {reg_type}"})
                    continue
                for start_addr, _, batch_items in batches:
                    try:
                        payload = []
                        for item in batch_items:
                            _, data_type = self._get_dtype_params(item["type"])
                            val = item["val"]
                            if data_type is not None and "int" in item["type"].lower() and not isinstance(val, int):
                                raise ValueError("Value must be integer for int dtype")
                            vals = client.convert_to_registers(val, data_type, word_order=self.word_order) if data_type is not None else [val]
                            payload.extend(vals)
                        async def batch_write_func():
                            await writer.write(client, start_addr, payload, slave)
                            return {"status": "ok"}
                        res = await self.retry_operation(batch_write_func, log_msg="Batch write register")
                        partial_results.append(res)
                    except Exception as e:
                        self.logger.error(f"Batch write error for reg_type={reg_type}: {e}")
                        self.logger.error(traceback.format_exc())
                        partial_results.append({"status": "error", "msg": str(e)})
        errors = [r for r in partial_results if r.get("status") == "error"]
        if errors:
            return {"status": "partial_error", "msg": f"Batch write errors: {errors}", "results": partial_results}
        return {"status": "ok"}

    async def do_read(self, cfg, slave, addr, dtype, cache_it, register_type="holding"):
        """
        Performs a single read operation from hardware.
        """
        self.logger.debug(f"do_read: slave={slave}, addr={addr}, dtype={dtype}, register_type={register_type}")
        client, lock, _ = await self.conn_pool.get_client(cfg)
        async with lock:
            if not client.connected:
                await self.reconnect(client, log_msg="Read reconnect")
            async def read_func():
                count, data_type = self._get_dtype_params(dtype)
                reader = self.register_readers.get(register_type)
                if not reader:
                    raise ValueError(f"Unsupported register_type: {register_type}")
                vals = await reader.read(client, addr, count, slave)
                if len(vals) < count:
                    raise RuntimeError(f"Insufficient data for addr {addr}: expected {count}, got {len(vals)}")
                if register_type in ["coil", "discrete"] or data_type is None:
                    val = vals[0] if count == 1 else vals
                else:
                    val = client.convert_from_registers(vals, data_type, word_order=self.word_order)
                return val
            try:
                val = await self.retry_operation(read_func, log_msg="Read register")
                if cache_it:
                    ckey = self._get_conn_key(cfg)
                    self.cache[(ckey, slave, addr)] = val
                return {"status": "ok", "val": val}
            except ValueError as e:
                self.logger.error(f"Value conversion error: {e}")
                self.logger.error(traceback.format_exc())
                return {"status": "error", "msg": str(e)}

    async def do_batch_read(self, cfg, slave, tasks, cache_it):
        """
        Performs optimized batch read: sorts, batches with gaps and limits.
        """
        if not tasks:
            return {"status": "ok", "vals": {}}
        self.logger.debug(f"do_batch_read: slave={slave}, tasks={tasks}")
        grouped_by_reg = {}
        for task in tasks:
            reg_type = task.get("register_type", "holding")
            grouped_by_reg.setdefault(reg_type, []).append(task)
        results = {}
        for reg_type, reg_tasks in grouped_by_reg.items():
            sorted_tasks = sorted(reg_tasks, key=lambda t: t["addr"])
            client, lock, _ = await self.conn_pool.get_client(cfg)
            async with lock:
                if not client.connected:
                    await self.reconnect(client, log_msg="Batch read reconnect")
                norm_items = [(t["addr"], t) for t in sorted_tasks]
                batches = await self._build_batches(norm_items, is_write=False)
                reader = self.register_readers.get(reg_type)
                if not reader:
                    return {"status": "error", "msg": f"Unsupported register_type: {reg_type}"}
                for start_addr, total_count, batch_items in batches:
                    async def batch_read_func():
                        registers = await reader.read(client, start_addr, total_count, slave)
                        return registers
                    try:
                        registers = await self.retry_operation(batch_read_func, log_msg="Batch read register")
                        if len(registers) < total_count:
                            raise RuntimeError(f"Response length mismatch: expected {total_count}, got {len(registers)}")
                        for b_item in batch_items:
                            b_addr, b_info = b_item
                            rel_offset = b_addr - start_addr
                            count, data_type = self._get_dtype_params(b_info["type"])
                            vals = registers[rel_offset:rel_offset + count]
                            if len(vals) < count:
                                raise RuntimeError(f"Insufficient data for addr {b_addr}: expected {count}, got {len(vals)}")
                            if reg_type in ["coil", "discrete"] or data_type is None:
                                val = vals[0] if count == 1 else vals
                            else:
                                val = client.convert_from_registers(vals, data_type, word_order=self.word_order)
                            results[b_addr] = val
                            if cache_it:
                                ckey = self._get_conn_key(cfg)
                                self.cache[(ckey, slave, b_addr)] = val
                    except Exception as e:
                        self.logger.error(f"Batch read error for reg_type={reg_type}: {e}")
                        self.logger.error(traceback.format_exc())
                        return {"status": "error", "msg": str(e)}
        return {"status": "ok", "vals": results}

    async def cleanup_worker(self):
        """
        Background cleanup coroutine for inactive connections.
        Runs periodically to close connections that haven't been used.
        """
        while self.running:
            try:
                await asyncio.sleep(self.conn_pool.cleanup_interval)
                await self.conn_pool.cleanup_inactive()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Cleanup worker error: {e}")
                self.logger.error(traceback.format_exc())

    async def _handle_request(self, sock, client_id, req):
        """
        Handles a single request from a client.
        Sends response via the provided sock (ROUTER or REP).
        """
        async def send_response(res):
            packed_res = self.pack(res)
            await self.zmq_strategy.send_strategy.send(sock, client_id, packed_res)

        op = req.get("op")
        try:
            handler = self.op_handlers.get(op)
            if handler:
                await handler.handle(self, req, send_response)
            else:
                await send_response({"status": "error", "msg": "Unknown operation"})
        except KeyError as e:
            await send_response({"status": "error", "msg": f"Missing key: {e}"})
        except Exception as e:
            self.logger.error(f"Request handler error: {e}")
            self.logger.error(traceback.format_exc())
            await send_response({"status": "error", "msg": str(e)})

    async def main_loop(self):
        """
        Main request processing loop using ZeroMQ socket based on mode.
        Supports 'router' (concurrent) or 'rep' (synchronous).
        """
        self.polling_task = asyncio.create_task(self.poll_worker())
        self.processor_task = asyncio.create_task(self.processor_worker())
        self.cleanup_task = asyncio.create_task(self.cleanup_worker())

        while self.running:
            try:
                client_id, raw = await self.zmq_strategy.recv_strategy.recv(self.sock)
                req = self.unpack(raw)
                op = req.get("op")
                self.logger.debug(f"Received request: op={op}")
                if self.zmq_mode == 'router':
                    asyncio.create_task(self._handle_request(self.sock, client_id, req))
                else:
                    await self._handle_request(self.sock, client_id, req)
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                self.logger.error(traceback.format_exc())

    async def shutdown(self):
        """
        Graceful shutdown: cancels tasks, drains queues, closes clients and sock.
        """
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        if self.sender_task:
            self.sender_task.cancel()
            try:
                await self.sender_task
            except asyncio.CancelledError:
                pass
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        await self.send_queue.join()
        while not self.task_queue.empty():
            task = await self.task_queue.get()
            if not task.future.done():
                task.future.set_exception(asyncio.CancelledError("Service shutdown"))
            self.task_queue.task_done()
        for task in self.heartbeat_tasks.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await self.conn_pool.close_all()
        if self.sock:
            self.sock.close()
        await super().shutdown()

if __name__ == "__main__":
    ModbusService().start()