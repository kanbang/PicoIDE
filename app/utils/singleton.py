'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-14 14:51:13
LastEditors: zhai
LastEditTime: 2026-01-14 14:51:30
'''
from functools import wraps
import threading

def singleton(cls):
    """
    工业级单例装饰器：
    确保在一个进程生命周期内，该类仅存在一个实例。
    """
    instances = {}
    lock = threading.Lock()  # 线程锁，防止初始化时的竞争

    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            with lock:
                # Double-Check Locking
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance