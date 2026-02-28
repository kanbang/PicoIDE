# PicoIDE IO 服务工程文档

## 一、项目概述

**PicoIDE IO** 是一个基于 Python 的工业 I/O 通信服务系统，提供 CAN 总线和 Modbus 协议的通信接口。系统采用微服务架构，通过 ZeroMQ 消息队列实现服务间通信，支持 Windows 和 Linux 跨平台运行。

## 二、技术栈

- **语言**: Python 3.10+
- **通信框架**: ZeroMQ (zmq, zmq.asyncio)
- **序列化**: MessagePack (msgpack)
- **并发模型**: asyncio 异步 I/O
- **CAN 通信**: python-can 库
- **Modbus 通信**: pymodbus 库

## 三、项目结构

```
E:\git\flow\PicoIDE\io\
├── runner.py           # 进程管理器，负责启动和监控服务
├── common.py           # 基础服务类和公共配置
├── can_service.py      # CAN 总线服务
├── modbus_service.py   # Modbus 协议服务
└── test\
    └── io_client.py    # 测试客户端
```

## 四、核心模块说明

### 4.1 runner.py - 进程管理器

**职责**: 作为守护进程，启动、监控和管理子服务进程

**核心功能**:
- 启动 CAN_SVC 和 MODBUS_SVC 两个服务
- 监控子进程状态，异常退出时自动重启
- 处理系统信号（SIGINT/SIGTERM），实现优雅关闭
- 支持平台适配（Windows 使用 CREATE_NEW_PROCESS_GROUP）

**关键类**:
- `ProcessManager`: 进程管理核心类
  - `start_process()`: 启动服务进程
  - `monitor()`: 监控循环
  - `_shutdown()`: 停止所有服务

### 4.2 common.py - 基础服务框架

**职责**: 提供所有 I/O 服务的基类和公共配置

**核心配置**:
```python
CONF = {
    "CAN": {"port": 5555, "pub_port": 5557, "ipc": "flow_can"},
    "MODBUS": {"port": 5556, "pub_port": 5558, "ipc": "flow_modbus"},
}
```

**核心类**:
- `BaseIOService`: 抽象基类
  - `get_addr()`: 根据操作系统自动选择 TCP 或 IPC 通信地址
  - `pack()`/`unpack()`: MessagePack 序列化/反序列化
  - `main_loop()`: 抽象方法，子类需实现
  - `start()`: 启动服务入口

**通信模式**:
- **REQ-REP**: 请求-响应模式（用于写操作、订阅等）
- **PUB-SUB**: 发布-订阅模式（用于数据变化推送）

### 4.3 can_service.py - CAN 总线服务

**职责**: 处理 CAN 总线通信，接收和转发 CAN 帧

**核心功能**:
- 监听 CAN 总线数据
- 通过 ZeroMQ PUB 端口实时推送 CAN 帧
- 支持多线程/异步处理

**依赖**: `python-can` 库

### 4.4 modbus_service.py - Modbus 协议服务

**职责**: 管理 Modbus 设备连接，提供读写接口和数据订阅功能

**核心功能**:
- **连接池管理**: 自动管理多台 Modbus 设备的 TCP/串口连接
- **优先级任务队列**: 写操作优先于读操作
- **数据订阅**: 支持订阅多个寄存器地址，变化检测（COV）自动推送
- **本地缓存**: 缓存最新数据，支持快速读取

**核心类**:
- `ConnectionPool`: 连接池管理
  - `get_client()`: 获取或创建 Modbus 客户端连接

- `PriorityTask`: 优先级任务封装

- `ModbusService`: Modbus 服务主类
  - `poll_worker()`: 后台轮询协程，执行写操作和订阅轮询
  - `do_write()`: 执行硬件写入
  - `main_loop()`: 处理客户端请求（write/subscribe/read_cache）

**支持的操作**:
```python
# 写操作
{"op": "write", "config": {...}, "slave": 1, "addr": 10, "val": 100, "type": "uint16"}

# 订阅操作
{"op": "subscribe", "config": {...}, "slave": 1, "tasks": [{"addr": 10, "type": "uint16"}]}

# 读取缓存
{"op": "read_cache"}
```

### 4.5 test/io_client.py - 测试客户端

**职责**: 提供客户端示例，测试 CAN 和 Modbus 服务

**核心类**:
- `IOClient`: 客户端封装
  - `init_can_subscriber()`: 初始化 CAN 订阅
  - `init_modbus_client()`: 初始化 Modbus 客户端
  - `get_can_frame()`: 接收 CAN 帧
  - `read_modbus()`: 读取 Modbus 数据

**平台兼容性修复**:
```python
# Windows 下必须使用 SelectorEventLoop
if is_win:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

## 五、通信架构

```
┌─────────────┐
│   Runner    │  ← 进程管理
└──────┬──────┘
       │
   ┌───┴──────────────────┐
   │                      │
┌──┴──────┐         ┌─────┴─────┐
│CAN_SVC  │         │MODBUS_SVC │
└──┬──────┘         └─────┬─────┘
   │                      │
   │ zmq PUB (5557)       │ zmq PUB (5558)
   │                      │
   └──────────┬───────────┘
              │
         ┌────┴────┐
         │  Client │
         └─────────┘
```

## 六、运行方式

### 6.1 启动服务
```bash
python runner.py
```

### 6.2 测试客户端
```bash
python test/io_client.py
```

## 七、关键特性

1. **跨平台支持**: 自动适配 Windows 和 Linux 的通信方式（TCP vs IPC）
2. **进程守护**: 自动重启异常退出的服务
3. **异步高并发**: 基于 asyncio 的异步 I/O 模型
4. **连接池**: Modbus 连接复用，提高效率
5. **变化检测**: 订阅模式下仅推送变化的数据（COV）
6. **优雅关闭**: 支持信号处理，安全退出

## 八、端口分配

| 服务 | REQ-REP 端口 | PUB-SUB 端口 |
|------|--------------|--------------|
| CAN  | 5555         | 5557         |
| Modbus | 5556       | 5558         |

## 九、更新日志

- 2026-01-22: 初始文档创建