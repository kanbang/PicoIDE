'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-22 10:54:51
LastEditors: zhai
LastEditTime: 2026-01-22 10:55:00
'''
import subprocess
import sys
import time
import os
import signal
import platform

# 定义要运行的服务模块路径
SERVICES = [
    {"name": "CAN_SVC", "path": "can_service.py"},
    {"name": "MODBUS_SVC", "path": "modbus_service.py"},
]

class ProcessManager:
    def __init__(self):
        self.procs = {} # {name: subprocess.Popen}
        self.running = True
        self.interpreter = sys.executable  # 使用当前环境的 Python
        
        # 信号处理
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def start_process(self, svc_info):
        name = svc_info["name"]
        script_path = os.path.join(os.getcwd(), svc_info["path"])
        
        if not os.path.exists(script_path):
            print(f"[Runner] 错误: 找不到文件 {script_path}")
            return None

        print(f"[Runner] 正在启动 {name} ...")
        
        # Windows 下使用 new_process_group 可以更好地隔离信号
        creationflags = 0
        if platform.system() == "Windows":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        p = subprocess.Popen(
            [self.interpreter, script_path],
            creationflags=creationflags
            # 在生产环境可以重定向 stdout/stderr 到文件
        )
        self.procs[name] = {"popen": p, "info": svc_info, "start_time": time.time()}
        return p

    def monitor(self):
        print(f"[Runner] 守护进程启动. PID: {os.getpid()}")
        print(f"[Runner] 平台: {platform.system()}")
        
        # 初始启动
        for svc in SERVICES:
            self.start_process(svc)

        while self.running:
            for name, meta in list(self.procs.items()):
                p = meta["popen"]
                ret_code = p.poll()
                
                if ret_code is not None:
                    # 进程已退出
                    duration = time.time() - meta["start_time"]
                    print(f"[Runner] 警告: {name} 退出 (代码 {ret_code}). 运行了 {duration:.2f}s")
                    
                    # 简单防抖：如果运行时间太短，稍微等待再重启
                    if duration < 2:
                        time.sleep(1)
                    
                    self.start_process(meta["info"])
            
            time.sleep(1)

    def _shutdown(self, signum, frame):
        print("\n[Runner] 正在停止所有服务...")
        self.running = False
        for name, meta in self.procs.items():
            p = meta["popen"]
            print(f"   -> 终止 {name} (PID: {p.pid})")
            p.terminate()
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
        sys.exit(0)

if __name__ == "__main__":
    manager = ProcessManager()
    manager.monitor()