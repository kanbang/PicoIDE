# Flow 开发说明

这份文档是 `app/flow` 的开发者导览，重点说明当前运行时如何组织、扩展点在哪里，以及哪些设计边界在修改时需要格外小心。

## 1. 模块总览

- `__init__.py`
  - 提供给路由层使用的公共入口。
  - 暴露引擎注册、启动/停止执行、生成 `execution_id` 等辅助方法。
- `block.py`
  - Block 基类抽象。
  - `BaseBlock` 中包含共享的文件输出辅助逻辑。
- `blocks_manager.py`
  - 静态 Block 注册表。
  - 支持从 Python 脚本动态构建 Block。
- `engine.py`
  - 负责 flow 图编译，以及内存中的执行运行时。
- `engine_manager.py`
  - 单例编排器。
  - 负责已注册的 Block 库、预编译引擎、运行中执行实例的管理。
- `runtime_bus.py`
  - 运行时事件通道，SSE 依赖它分发事件。
- `collector.py`
  - 轻量级内存文件收集器。
  - 可选支持异步写入数据库。
- `output.py`
  - 面向数据库的输出文件 / 执行文件生命周期管理与清理。
- `setting.py`
  - Flow 运行时设置项。
- `log.py`
  - Flow 相关模块的日志初始化。

## 2. 执行生命周期

当前主执行链路大致如下：

1. 路由层加载已保存的 flow 图和业务脚本。
2. `register_business_engine(business, scripts)` 将脚本中的 Block 类注册到 `EngineManager`。
3. `async_start_flow(...)` 调用 `EngineManager.start_execution(...)`。
4. `EngineManager.acquire(...)` 复用或创建一个预编译好的 `ComputeEngine`。
5. `ComputeEngine.run(execution_id)` 创建 `Execution`。
6. `Execution.run()` 找出源节点，并调度 `_execute_node(...)` 任务。
7. 节点执行完成后，`_trigger_successors(...)` 会把输出写入下游输入，并触发后继节点。
8. 运行时事件通过 `RuntimeEventBus` 发出。
9. 输出文件通过 `FileCollector` 收集，并在需要时持久化到数据库。
10. 前端通过 `/api/engine/stream/{execution_id}` 订阅 SSE，并据此更新界面。

## 3. Graph 模型约定

`ComputeEngine.set_flow(...)` 期望的图结构大致如下：

- `nodes`: 节点定义列表
- `connections`: 连线定义列表
- 每个节点通常包含：
  - `id`
  - `type`
  - `inputs`
  - `outputs`

编译阶段内部使用 `networkx.MultiDiGraph`，边上会携带：

- `out_p`: 源节点输出端口名
- `in_p`: 目标节点输入端口名

关于环路：

- 如果图不是 DAG，引擎会记录 warning。
- 当前没有专门的环路调度器。
- 因此带环行为目前主要靠 Block 自身设计兜住，而不是引擎层保证。

## 4. Block 扩展指南

新增 Block 一般继承 `Block` 或 `BaseBlock`。

最小要求：

- 声明 `NAME`
- 可选声明 `CATEGORY`
- 实现 `async def on_compute(self, execution_id: str = None)`

`BaseBlock` 中常用的辅助方法：

- `_log_compute_start(...)`
- `_log_compute_end()`
- `_log_error(...)`
- `_validate_input_data(...)`
- `_write_file(...)`

接口约定：

- 使用 `add_input(...)` / `add_output(...)` 定义输入输出
- 使用 `set_interface(...)` 写出结果
- 使用 `get_interface(...)` 读取上游值
- 配置项可使用 `add_text_option(...)`、`add_select_option(...)`、`add_number_option(...)` 等辅助方法

流式 Block：

- 设置 `STREAMING = True`
- 对于源流式节点，`Execution._execute_node(...)` 会循环重入执行
- 结束时抛出 `GenerationComplete`，表示源节点正常完成

## 5. 输出与文件流转

这里有两个相互关联的子系统：

### `collector.py`

执行过程中使用，目标是低延迟收集与事件通知。

- 按 `execution_id` 在内存中存储文件信息
- 当 `ENABLE_DB_WRITE=True` 时可选持久化到数据库
- 对外主要暴露：
  - `add_file(...)`
  - `update_file(...)`
  - `get_files(...)`
  - `clear_execution(...)`

### `output.py`

偏数据库侧的输出管理层。

- 查询输出记录
- 解析文件路径
- 软删除 / 硬删除
- 清理过期输出和执行记录

实际路由处理中，会根据 `settings.ENABLE_DB_WRITE` 在这两条路径之间切换。

## 6. 事件模型

运行时事件类型定义在 `runtime_bus.py` 中：

- `log`
- `debug`
- `info`
- `error`
- `data`
- `file`
- `status`
- `execution_completed`
- `execution_failed`
- `execution_stopped`

前端的 SSE 协议目前强依赖以下几类事件：

- `status`
- `file`
- 结束类事件：
  - `execution_completed`
  - `execution_failed`
  - `execution_stopped`

如果要改这些事件的 payload，至少要同时核对：

- `app/routes/engine/views.py`
- `web/src/components/NodeFlow/index.vue`
- `web/src/components/NodeFlow/OutputPanel.vue`
- `web/src/views/FlowMonitor.vue`

## 7. 关键设置项

定义在 `setting.py`：

- `OUTPUT_DIR`
- `TEMP_DIR`
- `ENABLE_DB_WRITE`
- `FILE_RETENTION_HOURS`
- `SOFT_DELETE_RETENTION_DAYS`
- `EXECUTION_RETENTION_DAYS`
- `CLEANUP_INTERVAL_HOURS`
- `BROWSER_OPENABLE`

这些并不只是普通常量，更像运行时行为开关。调整它们会直接改变持久化、保留期和清理语义。

## 8. 已知设计边界

下面这些不是理论问题，而是当前实现里已经存在的注意点。

1. `FileCollector` 只保存一个全局事件回调。
   - 每个 `ComputeEngine` 初始化时都会覆盖它。
   - 如果并发存在多个 engine，文件事件可能会被路由到最后一个 engine 的回调。

2. 文件事件目前可能从不止一个地方发出。
   - `BaseBlock._write_file(...)` 会直接发送文件事件。
   - `FileCollector` 的回调链路也可能再通过 engine 发一次文件事件。
   - 如果前端依赖“只收到一次”文件更新，这一段很值得单独审计。

3. `OutputFileManager` 在 `__init__` 里启动清理线程。
   - 但单例是靠 `__new__` 实现的，重复实例化路径仍可能反复执行 `__init__`。
   - 如果没有额外保护，就可能启动多个后台清理线程。

4. 引擎缓存里存的是预编译后的 `ComputeEngine` 实例。
   - 这样做性能不错。
   - 但也意味着凡是挂在 engine 初始化阶段的全局协作者，都要特别检查是否真的适合缓存共享。

## 9. 安全修改建议

如果需要改这个子系统，风险较低的处理顺序建议是：

1. 先稳定事件语义
2. 再把 execution 级状态和全局单例拆开
3. 再统一文件生命周期职责
4. 最后再整理引擎缓存和清理线程行为

做中等规模改动时，建议至少验证下面这些场景：

- 已保存 flow 的执行
- 停止执行
- SSE 日志
- SSE 文件事件
- 输出文件列表
- 执行历史列表

## 10. 建议的下一步重构

按收益排序，比较值得做的重构如下：

1. 把 `FileCollector.set_event_callback(...)` 改为 execution 级监听器。
2. 收敛重复的文件事件发送路径，只保留一个权威出口。
3. 给 `OutputFileManager` 的后台任务启动加保护。
4. 补一组聚焦测试，覆盖：
   - 多订阅者 SSE
   - 不同 business 下的并发执行
   - 文件新增 / 更新链路
