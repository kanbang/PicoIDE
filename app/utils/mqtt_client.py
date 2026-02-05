import json
import logging
from time import sleep
from typing import Any, Callable, Optional, Dict, List, Tuple
import paho.mqtt.client as mqtt
from abc import ABC, abstractmethod
from paho.mqtt.reasoncodes import ReasonCode
import threading
import time
import uuid
from collections import defaultdict
from paho.mqtt import subscribe

# 上线和下线消息主题
online_topic = "$SYS/brokers/+/clients/+/connected"
offline_topic = "$SYS/brokers/+/clients/+/disconnected"

def generate_mqtt_reply_id():
    return "mqtt_reply_" + str(uuid.uuid4()).replace("-", "")

class MqttClientEx(ABC):
    def __init__(
        self,
        host: str,
        port: int,
        client_id: str = "",
        rpc_callback_topic: str | None = None,
        username=None,
        password=None,
        keepalive_interval: int = 10,
        logger: logging.Logger = None,
    ) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password

        self.mqtt_client = None
        self.is_connected = False
        self.is_loop_start = False

        self.reconnect_delay = 10

        # 心跳间隔时间（秒）
        self.client_keep_alive_time = keepalive_interval

        self.rpc_callback_topic = rpc_callback_topic
        self.callback_map = {}

        # 定时任务属性
        self._task_active = threading.Event()  # 控制标志
        self._task_thread = None  # task线程
        self._tasks = []  # 存储定时任务的配置
        self._tasks_lock = threading.Lock()  # 线程锁

        # 新增连接检查相关属性
        self._check_active = threading.Event()  # 新增控制标志
        self._check_thread = None

        # 用于等待连接的 Event（只保留同步版本）
        self._connected_thread_event = threading.Event()

        # logger
        self._logger = logger

    def connect(self, block: bool = False, timeout: float = 15.0) -> bool:
        if self.is_connected:
            return True
        if not self._check_thread:
            self._connect_once()
            self._start_connection_checker()

        if block:
            return self.wait_for_connected(timeout)
        return self.is_connected

    def disconnect(self):
        self._stop_connection_checker()
        self._stop_task_timer()
        if self.is_connected and self.mqtt_client:
            self.mqtt_client.disconnect()
            self.is_connected = False
            self.is_loop_start = False

    def publish(self, topic: str, data: str, qos=0, wait: bool = False) -> bool:
        if self.is_connected:
            try:
                message = self.mqtt_client.publish(topic, data, qos)
                if wait:
                    message.wait_for_publish()
            except Exception as e:
                self.print_error(f"paho mqtt publish exception: {e}")
                return False
            return True
        return False

    # 发布 RPC 请求
    def rpc_publish(self, topic, payload, pub_callback=None, ret_callback=None, timeout=15.0):
        # 生成唯一的回复ID
        reply_id = generate_mqtt_reply_id()
        rpc_data = {"reply_id": reply_id, "payload": payload}

        # 发布到指定的 RPC 请求主题
        self.publish(topic, json.dumps(rpc_data), qos=1)  # 使用 qos=1 确保可靠

        # 执行发布后的回调
        if pub_callback:
            pub_callback()

        # 设置返回回调并添加超时清理
        if ret_callback:
            self.callback_map[reply_id] = ret_callback

            # 添加一次性超时任务
            def timeout_callback():
                if reply_id in self.callback_map:
                    callback = self.callback_map.pop(reply_id)
                    try:
                        callback({"error": "timeout"})  # 传递超时错误
                    except Exception as e:
                        self.print_error(f"RPC timeout callback error: {e}")

            self.add_task(interval=timeout, callback=timeout_callback, once=True)

    def add_task(
        self,
        interval: float,
        callback: Callable[[], Any],
        task_id: Optional[str] = None,
        once: bool = False,
    ) -> str:
        """
        添加定时任务
        :param interval: 任务执行间隔（秒）
        :param callback: 任务回调函数
        :param task_id: 任务唯一标识（可选）
        :param once: 是否一次性任务
        :return: task_id
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        with self._tasks_lock:  # 加锁
            self._tasks.append(
                {
                    "interval": interval,
                    "callback": callback,
                    "last_run": time.time(),
                    "task_id": task_id,
                    "once": once,
                }
            )
        return task_id

    def remove_task(self, task_id):
        """
        移除定时任务
        :param task_id: 任务唯一标识
        """
        with self._tasks_lock:  # 加锁
            self._tasks = [task for task in self._tasks if task["task_id"] != task_id]

    @abstractmethod
    def on_connect(self, client, userdata, flags, rc):
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        pass

    @abstractmethod
    def on_disconnect(self, client, userdata, msg):
        pass

    @abstractmethod
    def on_message(self, client, userdata, msg):
        pass

    @abstractmethod
    def on_error(self, client, userdata, msg):
        pass

    @abstractmethod
    def on_online(self, msg):
        data = json.loads(msg)
        self.print_info("online", data["clientid"], data["username"])

    @abstractmethod
    def on_offline(self, msg):
        data = json.loads(msg)
        self.print_info("offline", data["clientid"], data["username"])

    def print_info(self, msg):
        if self._logger:
            self._logger.info(f"[MqttClient]: {msg}")
        else:
            print(f"[MqttClient]: {msg}")

    def print_error(self, msg):
        if self._logger:
            self._logger.error(f"[MqttClient]: {msg}")
        else:
            print(f"[MqttClient]: {msg}")

    def _check_connection(self) -> bool:
        if self.is_connected:
            return True

        return self._connect_once()

    # rpc 回调函数
    def _on_rpc_callback(self, topic, msg):
        data = json.loads(msg)
        reply_id = data.get("reply_id")
        if reply_id in self.callback_map:
            callback = self.callback_map.pop(reply_id)
            if callback:
                callback(data)

    def _connect_once(self) -> bool:
        if self.is_loop_start:
            return True

        self.print_info(f"connecting to mqtt-broker (host: {self.host} | port: {self.port})")

        if self.mqtt_client is None:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id)
            if self.username:
                self.mqtt_client.username_pw_set(self.username, self.password)

            self.mqtt_client.on_connect = self._on_connect
            self.mqtt_client.on_disconnect = self._on_disconnect
            self.mqtt_client.on_message = self._on_message
            self.mqtt_client.on_subscribe = self._on_subscribe
            self.mqtt_client.on_publish = self._on_publish

            self.mqtt_client.message_callback_add(
                online_topic,
                lambda client, userdata, msg: self.on_online(msg.payload.decode()),
            )
            self.mqtt_client.message_callback_add(
                offline_topic,
                lambda client, userdata, msg: self.on_offline(msg.payload.decode()),
            )

            self.mqtt_client.reconnect_delay_set(min_delay=1, max_delay=self.reconnect_delay)

        try:
            self.mqtt_client.connect(host=self.host, port=self.port, keepalive=self.client_keep_alive_time)
            self.mqtt_client.loop_start()
            self.is_loop_start = True

            self.print_info("mqtt client loop start")
            return True

        except Exception as e:
            err_msg = f"mqtt connect exception: {e}"
            self.on_error(None, None, err_msg)
            return False

    def _on_connect(self, mqttc, userdata, flags, reason_code: ReasonCode, properties):
        self.print_info(f"Received connect() status [{reason_code}]")
        self.is_connected = not reason_code.is_failure

        if self.is_connected:
            self.print_info("connected to mqtt-broker")

            # 订阅上线和下线消息主题
            mqttc.subscribe([(online_topic, 1), (offline_topic, 1)])

            # 订阅rpc响应主题
            if self.rpc_callback_topic:
                self.mqtt_client.subscribe(self.rpc_callback_topic)
                self.mqtt_client.message_callback_add(
                    self.rpc_callback_topic,
                    lambda client, userdata, msg: self._on_rpc_callback(msg.topic, msg.payload.decode()),
                )

            self.on_connect(mqttc, userdata, flags, reason_code)

            """连接成功时启动心跳"""
            self._start_task_timer()  # 连接成功后启动心跳

            # 通知等待事件
            self._connected_thread_event.set()

        else:
            err_msg = "mqtt error: " + reason_code.getName()
            self.on_error(mqttc, userdata, err_msg)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self.print_info(f"client disconnected from mqtt-broker: {reason_code}")

        self.is_connected = False
        self.is_loop_start = False
        self.on_disconnect(client, userdata, reason_code)
        # loop_stop() 不能写在on_disconnect 回调里, 否则 threading.current_thread() == client._thread
        # 客户端无法清除client._thread 子进程，以后再使用loop_start()就无效了


        self._stop_task_timer()  # 断开时停止

    def _on_subscribe(self, client, userdata, mid, reason_codes, properties):
        self.print_info(f"subscribed: {mid} {reason_codes}")

    def _on_publish(self, client, userdata, mid, reason_code, properties):
        self.print_info(f"published: {mid} {reason_code}")

    def _on_message(self, client, userdata, msg):
        # 消息接收回调
        self.on_message(client, userdata, msg)

    def _start_task_timer(self):
        self._stop_task_timer()
        self._task_active.set()

        def task_loop():
            while self._task_active.is_set():
                cur_time = time.time()
                with self._tasks_lock:
                    tasks = self._tasks.copy()

                if not tasks:
                    time.sleep(0.1)
                    continue

                to_remove = []  # 收集要移除的任务
                for task in tasks:
                    elapsed = cur_time - task["last_run"]
                    if elapsed >= task["interval"]:
                        if self.is_connected or task.get("once", False):  # 对于超时，不依赖 is_connected
                            try:
                                task["callback"]()
                            except Exception as e:
                                self.print_error(f"Task error: {e}")
                        if task.get("once", False):
                            to_remove.append(task["task_id"])
                        else:
                            task["last_run"] = cur_time  # 周期任务更新 last_run

                # 移除一次性任务
                if to_remove:
                    with self._tasks_lock:
                        self._tasks = [t for t in self._tasks if t["task_id"] not in to_remove]

                # 计算下次 sleep
                if self._tasks:
                    next_wait = min(
                        (t["interval"] - (cur_time - t["last_run"]) for t in self._tasks),
                        default=0.1
                    )
                    time.sleep(max(0, next_wait))
                else:
                    time.sleep(0.1)

        self._task_thread = threading.Thread(
            target=task_loop, name="mqtt_task_timer", daemon=True
        )
        self._task_thread.start()

    def _stop_task_timer(self):
        """停止task线程"""
        self._task_active.clear()
        if self._task_thread and self._task_thread.is_alive():
            self._task_thread.join(timeout=2)  # 等待线程结束
        self._task_thread = None

    def _start_connection_checker(self):
        """启动连接检查线程"""

        def connection_check_loop():
            """连接检查主循环"""
            while self._check_active.is_set():
                self._check_connection()
                time.sleep(3)  # 保持3秒检查间隔

        self._check_active.set()
        self._check_thread = threading.Thread(
            target=connection_check_loop, name="mqtt_connection_checker", daemon=True
        )
        self._check_thread.start()

    def _stop_connection_checker(self):
        """停止连接检查线程"""
        self._check_active.clear()
        if self._check_thread and self._check_thread.is_alive():
            self._check_thread.join(timeout=2)  # 等待线程结束
        self._check_thread = None

    def wait_for_connected(self, timeout: float = 15.0) -> bool:
        """阻塞等待连接成功"""
        if self.is_connected:
            return True
            
        self._connected_thread_event.clear()
        # 确保已经尝试连接
        if not self.is_loop_start:
            self._connect_once()
            
        return self._connected_thread_event.wait(timeout=timeout)

    def __del__(self):
        self.disconnect()