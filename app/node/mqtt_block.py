import json
import logging
import asyncio
import threading
from typing import Dict, List, Any, Callable, Optional, Tuple
from collections import defaultdict
import uuid

from flow.block import BaseBlock
from utils import singleton
from utils.mqtt import MqttClientEx
from paho.mqtt import client as mqtt

class FlowMqttClient(MqttClientEx):
    """
    MqttClientEx 的具体实现，增加了基于 Topic 的回调分发功能
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 存储订阅的回调: topic -> list[callback_func]
        self._topic_callbacks: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)
        # 存储通配符订阅 (简单处理，实际生产可能需要更复杂的 Topic 匹配树)
        self._wildcard_callbacks: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def register_topic_callback(self, topic: str, callback: Callable):
        """注册特定 Topic 的回调"""
        if '+' in topic or '#' in topic:
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
        topics = list(self._topic_callbacks.keys()) + list(self._wildcard_callbacks.keys())
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
        pass # 可根据需要实现系统级通知

    def on_offline(self, msg):
        pass # 可根据需要实现系统级通知



@singleton
class MqttClientManager:
    """
    MQTT 客户端实例管理工具。
    利用装饰器实现单例，确保全局唯一的连接管理中心。
    """
    def __init__(self):
        # 客户端缓存池，Key 为 (host, port, username)
        self._clients: Dict[Tuple[str, int, Optional[str]], 'FlowMqttClient'] = {}
        # 保护缓存池增删改的线程锁
        self._pool_lock = threading.Lock()

    def get_client(
        self, 
        host: str, 
        port: int, 
        username: Optional[str] = None, 
        password: Optional[str] = None, 
        client_id_prefix: str = "flow"
    ) -> 'FlowMqttClient':
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
                logger=logging.getLogger(f"Mqtt.{host}")
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

    def __init__(self):
        super().__init__()
        # 配置选项
        self.add_text_option("host", default="localhost")
        self.add_integer_option("port", default=1883)
        self.add_text_option("username", default="")
        self.add_text_option("password", default="")
        self.add_text_option("topic", default="test/topic")
        
        # 模式选择：
        # NoWait: 立即返回最后一条缓存的消息
        # WaitNew: 等待一条新的消息到达
        self.add_select_option("mode", items=["NoWait", "WaitNew"], default="WaitNew")
        self.add_integer_option("timeout", default=10, min_val=1, max_val=60) # 等待超时时间

        # 输出端口
        self.add_output("payload")
        self.add_output("topic")
        self.add_output("full_msg")

        # 运行时状态
        self._last_message = None
        self._msg_queue = asyncio.Queue(maxsize=10) 
        self._client = None
        self._registered = False

    def _mqtt_callback(self, msg_data):
        """MQTT 收到消息时的回调"""
        self._last_message = msg_data
        
        # 如果队列满了，移除旧的（防止内存溢出）
        if self._msg_queue.full():
            try:
                self._msg_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        
        # 放入队列供 async 消费
        try:
            self._msg_queue.put_nowait(msg_data)
        except Exception:
            pass

    def _ensure_subscription(self):
        """确保 Client 已初始化并注册了回调"""
        host = self.get_option("host")
        port = self.get_option("port")
        username = self.get_option("username") or None
        password = self.get_option("password") or None
        topic = self.get_option("topic")

        if not self._client:
            self._client = mqtt_manager.get_client(host, port, username, password)
        
        # 这里为了防止重复注册，简单判断一下。
        # 严谨的做法是在 Block 销毁时注销，但当前 Block 声明周期未明确定义销毁钩子
        # 因此我们利用 FlowMqttClient 的去重机制
        self._client.register_topic_callback(topic, self._mqtt_callback)

    async def async_on_compute(self, execution_id: str = None):
        self._ensure_subscription()
        
        mode = self.get_option("mode")
        topic = self.get_option("topic")
        timeout = self.get_option("timeout")

        result_msg = None

        if mode == "NoWait":
            # 直接取缓存
            result_msg = self._last_message
            if result_msg is None:
                self._logger.warning(f"No cached message for topic {topic}")
        
        elif mode == "WaitNew":
            # 清空旧队列，只等待这一刻之后的新消息
            # 注意：如果想处理积压消息，就不清空。这里假设 WaitNew 是为了同步等待未来的事件
            while not self._msg_queue.empty():
                self._msg_queue.get_nowait()
            
            try:
                self._logger.info(f"Waiting for message on {topic} (timeout: {timeout}s)...")
                result_msg = await asyncio.wait_for(self._msg_queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                self._logger.error(f"Timeout waiting for message on {topic}")
                raise TimeoutError(f"MQTT Wait Timeout: {topic}")

        # 设置输出
        if result_msg:
            # 尝试自动解析 JSON
            payload = result_msg["payload"]
            try:
                payload = json.loads(payload)
            except:
                pass # 保持原样

            self.set_interface("payload", payload)
            self.set_interface("topic", result_msg["topic"])
            self.set_interface("full_msg", result_msg)
        else:
            self.set_interface("payload", None)

    def on_compute(self, execution_id: str = None):
        """同步模式下的入口"""
        # 可以在这里使用 asyncio.run 调用 async_on_compute
        # 或者为了简单，只支持 NoWait 模式
        asyncio.run(self.async_on_compute(execution_id))

__all__ = ["MqttPublishBlock", "MqttSubscribeBlock"]