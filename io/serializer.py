"""
序列化模块
支持 msgpack 和 json 两种序列化方式
"""
import json
from typing import Any
from config_loader import config


class Serializer:
    """序列化器基类"""

    @staticmethod
    def pack(data: Any) -> bytes:
        """序列化数据"""
        raise NotImplementedError

    @staticmethod
    def unpack(data: bytes) -> Any:
        """反序列化数据"""
        raise NotImplementedError


class MsgpackSerializer(Serializer):
    """MessagePack 序列化器"""

    def __init__(self):
        try:
            import msgpack
            self.msgpack = msgpack
        except ImportError:
            raise ImportError("msgpack 未安装，请运行: pip install msgpack")

    def pack(self, data: Any) -> bytes:
        return self.msgpack.packb(data, use_bin_type=True)

    def unpack(self, data: bytes) -> Any:
        return self.msgpack.unpackb(data, raw=False)


class JsonSerializer(Serializer):
    """JSON 序列化器"""

    def pack(self, data: Any) -> bytes:
        return json.dumps(data, ensure_ascii=False).encode('utf-8')

    def unpack(self, data: bytes) -> Any:
        return json.loads(data.decode('utf-8'))


def get_serializer() -> Serializer:
    """根据配置获取序列化器"""
    serialization_type = config.serialization.lower()

    if serialization_type == 'json':
        return JsonSerializer()
    elif serialization_type == 'msgpack':
        return MsgpackSerializer()
    else:
        raise ValueError(f"不支持的序列化类型: {serialization_type}")


# 全局序列化器实例
serializer = get_serializer()