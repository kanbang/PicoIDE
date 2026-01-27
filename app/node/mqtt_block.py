import json
import logging
import asyncio
import threading
from typing import Dict, List, Any, Callable, Optional, Tuple
from collections import defaultdict
import uuid

from flow.block import BaseBlock
from utils.singleton import singleton
from utils.mqtt_client import MqttClientEx
from paho.mqtt import client as mqtt


class FlowMqttClient(MqttClientEx):
    """
    MqttClientEx 的具体实现，增加了基于 Topic 的回调分发功能
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 存储订阅的回调: topic -> list[callback_func]
        self._topic_callbacks: Dict[str, List[Callable[[Any], None]]] = defaultdict(
            list
        )
        # 存储通配符订阅 (简单处理，实际生产可能需要更复杂的 Topic 匹配树)
        self._wildcard_callbacks: Dict[str, List[Callable[[Any], None]]] = defaultdict(
            list
        )

    def register_topic_callback(self, topic: str, callback: Callable):
        """注册特定 Topic 的回调"""
        if "+" in topic or "#" in topic:
            if callback not in self._wildcard_callbacks[topic]:
                self._wildcard_callbacks[topic].append(callback)
        else:
            if callback not in self._topic_callbacks[topic]:
                self._topic_callbacks[topic].append(callback)

        # 如果已连接，直接订阅
        if self.is_connected:
            self.mqtt_client.subscribe(topic)

    def remove_topic_callback(self, topic: str, callback: Callable):
        """移除回调"""
        if topic in self._topic_callbacks:
            if callback in self._topic_callbacks[topic]:
                self._topic_callbacks[topic].remove(callback)
        # 注意：这里一般不取消订阅(Unsubscribe)，因为可能还有其他 Block 在监听同一个 Topic

    def on_connect(self, client, userdata, flags, rc):
        # 重连后重新订阅所有注册的 Topic
        topics = list(self._topic_callbacks.keys()) + list(
            self._wildcard_callbacks.keys()
        )
        for topic in topics:
            client.subscribe(topic)

    def on_disconnect(self, client, userdata, msg):
        pass

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode()

        # 1. 精确匹配
        if topic in self._topic_callbacks:
            for cb in self._topic_callbacks[topic]:
                try:
                    cb({"topic": topic, "payload": payload, "qos": msg.qos})
                except Exception as e:
                    self.print_error(f"Callback error on {topic}: {e}")

        # 2. 简单的通配符处理 (仅演示 #，实际需更严谨匹配)
        for sub_topic, cbs in self._wildcard_callbacks.items():
            # 这里使用了 paho 自带的 topic_matches_sub 逻辑会更好，
            # 但为了不引入额外依赖，这里简化处理，或者假设用户使用 paho.mqtt.client.topic_matches_sub
            if mqtt.topic_matches_sub(sub_topic, topic):
                for cb in cbs:
                    cb({"topic": topic, "payload": payload, "qos": msg.qos})

    def on_error(self, client, userdata, msg):
        self.print_error(f"Error: {msg}")

    def on_online(self, msg):
        pass  # 可根据需要实现系统级通知

    def on_offline(self, msg):
        pass  # 可根据需要实现系统级通知


@singleton
class MqttClientManager:
    """
    MQTT 客户端实例管理工具。
    利用装饰器实现单例，确保全局唯一的连接管理中心。
    """

    def __init__(self):
        # 客户端缓存池，Key 为 (host, port, username)
        self._clients: Dict[Tuple[str, int, Optional[str]], "FlowMqttClient"] = {}
        # 保护缓存池增删改的线程锁
        self._pool_lock = threading.Lock()

    def get_client(
        self,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id_prefix: str = "flow",
    ) -> "FlowMqttClient":
        """
        获取或创建一个复用的 MQTT 客户端。
        """
        key = (host, port, username)

        # 1. 快速检索
        if key in self._clients:
            return self._clients[key]

        # 2. 线程安全地创建新连接
        with self._pool_lock:
            # 二次检查，防止并发穿透
            if key in self._clients:
                return self._clients[key]

            full_client_id = f"{client_id_prefix}_{uuid.uuid4().hex[:6]}"

            client = FlowMqttClient(
                host=host,
                port=port,
                username=username,
                password=password,
                client_id=full_client_id,
                logger=logging.getLogger(f"Mqtt.{host}"),
            )

            client.connect()
            self._clients[key] = client
            return client

    def remove_client(self, host: str, port: int, username: Optional[str] = None):
        """关闭并移除指定的客户端"""
        key = (host, port, username)
        with self._pool_lock:
            client = self._clients.pop(key, None)
            if client:
                client.disconnect()


mqtt_manager = MqttClientManager()


class MqttPublishBlock(BaseBlock):
    NAME = "MqttPublish"
    CATEGORY = "IoT"

    def __init__(self):
        super().__init__()
        # 定义输入端口
        self.add_input("topic")
        self.add_input("payload")

        # 定义配置选项
        self.add_text_option("host", default="localhost")
        self.add_integer_option("port", default=1883)
        self.add_text_option("username", default="")
        self.add_text_option("password", default="")
        self.add_select_option("qos", items=["0", "1", "2"], default="0")

        # 定义输出（可选，用于输出发送状态）
        self.add_output("status")

    def on_compute(self, execution_id: str = None):
        # 1. 获取配置
        host = self.get_option("host")
        port = self.get_option("port")
        username = self.get_option("username") or None
        password = self.get_option("password") or None
        qos = int(self.get_option("qos"))

        # 2. 获取输入数据 (优先使用 Input 端口，如果没有则使用 Option 或者报错)
        topic = self.get_interface("topic")
        payload = self.get_interface("payload")

        if not topic:
            raise ValueError("MQTT Publish requires a topic")

        # 确保 payload 是字符串
        if not isinstance(payload, str):
            payload = json.dumps(payload) if payload is not None else ""

        # 3. 获取 Client 并发送
        client = mqtt_manager.get_client(host, port, username, password)

        # 检查连接状态
        if not client.is_connected:
            # 尝试触发一次连接检查（虽然 Manager 会自动重连，但这里可以做个防御）
            client._check_connection()

        success = client.publish(topic, payload, qos=qos)

        if success:
            self.set_interface("status", {"status": "ok", "topic": topic})
            self._logger.info(f"Published to {topic}")
        else:
            self.set_interface("status", {"status": "failed"})
            raise RuntimeError(f"Failed to publish to {topic}")


class MqttSubscribeBlock(BaseBlock):
    NAME = "MqttSubscribe"
    CATEGORY = "IoT"
    STREAMING = True

    def __init__(self):
        super().__init__()
        # 配置选项
        self.add_text_input_option("host", default="localhost")
        self.add_integer_option("port", default=1883)
        self.add_text_input_option("username", default="")
        self.add_text_input_option("password", default="")
        self.add_text_input_option("topic", default="test/topic")

        # 输出端口
        self.add_output("payload")
        self.add_output("topic")
        self.add_output("full_msg")

        # 运行时状态
        self._last_message = None
        self._msg_queue = asyncio.Queue(maxsize=10)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client = None
        self._registered = False

    def _on_mqtt_msg(self, data):
        # 此处由 MQTT 线程调用，安全地推入异步队列
        if self._loop is None:
            # 如果此时 loop 还没获取到，说明节点还没启动完，忽略该消息
            return

        # 使用之前保存的 loop 引用，安全地跨线程调度
        self._loop.call_soon_threadsafe(self._msg_queue.put_nowait, data)

    async def async_on_compute(self, execution_id: str = None):
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        # 引擎启动后，第一个执行的就是这里，它会卡在 await
        if not self._registered:
            client = mqtt_manager.get_client(self.get_option("host"), 1883)
            client.register_topic_callback(self.get_option("topic"), self._on_mqtt_msg)
            self._registered = True

        # 阻塞直到新消息，一旦 get 到，本方法结束，引擎自动触发下游
        msg = await self._msg_queue.get()
        self.set_interface("payload", msg["payload"])
        self.set_interface("topic", msg["topic"])
        self.set_interface("full_msg", msg)


__all__ = ["MqttPublishBlock", "MqttSubscribeBlock"]
