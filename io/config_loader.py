"""
配置加载模块
支持从 YAML 文件加载配置，并提供默认值
"""
import os
import yaml
from typing import Dict, Any


class Config:
    """配置管理类"""

    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

        # 默认配置
        defaults = {
            'serialization': 'msgpack',
            'services': {
                'can': {
                    'req_port': 5555,
                    'pub_port': 5557,
                    'ipc': 'flow_can'
                },
                'modbus': {
                    'req_port': 5556,
                    'pub_port': 5558,
                    'ipc': 'flow_modbus'
                }
            },
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s [%(levelname)s] [%(name)s:%(process)d] %(message)s',
                'datefmt': '%H:%M:%S'
            },
            'modbus_config': {
                'max_retries': 3,
                'retry_delay_base': 0.5,
                'poll_interval': 0.1,
                'heartbeat_interval': 10,
                'heartbeat_addr': 0,
                'word_order': 'big',
                'max_registers': 125,
                'gap_threshold': 10,
                'queue_maxsize': 100,
                'default_timeout': 2,
                'default_baudrate': 9600,
            }
        }

        # 如果配置文件存在，加载并合并
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._deep_merge(defaults, user_config)
            except Exception as e:
                print(f"[Config] 警告: 加载配置文件失败，使用默认值: {e}")

        self._config = defaults

    def _deep_merge(self, base: Dict, update: Dict):
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default=None):
        """获取配置项，支持点号分隔的路径"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """获取服务配置"""
        return self._config.get('services', {}).get(service_name, {})

    @property
    def serialization(self) -> str:
        """获取序列化方式"""
        return self._config.get('serialization', 'msgpack')

    @property
    def logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self._config.get('logging', {})

    @property
    def modbus_config(self) -> Dict[str, Any]:
        """获取 Modbus 配置"""
        return self._config.get('modbus_config', {})


# 全局配置实例
config = Config()