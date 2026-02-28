# 输出文件管理系统

## 概述

这是一个工业级的Block执行和输出文件管理系统，用于处理DAQ（数据采集）流程的执行结果。

## 架构设计

### 后端架构

#### 1. 执行引擎 (`routes/execution.py`)

**核心类：**

- **ExecutionConfig**: 执行配置管理
  - 输出目录配置
  - 文件类型映射
  - 浏览器可打开类型识别

- **ExecutionStatus**: 执行状态枚举
  - PENDING: 等待执行
  - RUNNING: 执行中
  - COMPLETED: 执行完成
  - FAILED: 执行失败
  - CANCELLED: 执行取消

- **OutputFile**: 输出文件信息
  - 文件ID（唯一标识）
  - 文件名和路径
  - 文件类型和大小
  - 创建时间
  - 生成此文件的Block信息
  - 元数据

- **ExecutionResult**: 执行结果
  - 执行ID和状态
  - 时间信息（开始、结束、持续时间）
  - 输出文件列表
  - 错误和警告列表
  - 统计信息

- **ExecutionEngine**: 执行引擎
  - Block图执行
  - 输出文件收集
  - 执行状态跟踪
  - 错误处理和日志
  - 旧文件清理

#### 2. API路由 (`routes/execution_api.py`)

**端点：**

- `POST /api/execution/execute` - 执行Block图
- `GET /api/execution/results/{execution_id}` - 获取执行结果
- `GET /api/execution/files/{file_id}` - 获取文件内容
- `GET /api/execution/files` - 列出所有输出文件
- `DELETE /api/execution/files/{file_id}` - 删除文件
- `DELETE /api/execution/cleanup` - 清理旧文件

### 前端架构

#### 1. OutputPanel组件 (`components/OutputPanel.vue`)

**功能：**
- 显示执行状态
- 列出输出文件
- 提供文件操作（打开、下载、删除）
- 显示错误和警告信息
- 文件刷新和清理功能

**特性：**
- 响应式设计
- 实时状态更新
- 文件类型识别
- 文件大小格式化
- 错误处理和用户提示

#### 2. NodeFlow集成

**修改内容：**
- RUN命令调用执行API
- 集成OutputPanel组件
- 处理执行结果
- 文件操作事件处理

## 数据流程

### 1. 执行流程

```
用户点击"运行"
    ↓
NodeFlow发送执行请求
    ↓
后端ExecutionEngine执行Block图
    ↓
Blocks生成输出文件（CSV、HTML等）
    ↓
ExecutionEngine收集输出文件
    ↓
返回ExecutionResult给前端
    ↓
OutputPanel显示输出文件列表
```

### 2. 文件操作流程

**打开文件：**
```
用户点击"打开"
    ↓
前端发送GET请求到/api/execution/files/{file_id}
    ↓
后端返回FileResponse
    ↓
浏览器在新标签页打开文件
```

**下载文件：**
```
用户点击"下载"
    ↓
前端创建下载链接
    ↓
浏览器触发文件下载
```

## 文件类型处理

### 浏览器可打开类型
- HTML - 在新标签页打开
- JSON - 在新标签页打开
- TXT - 在新标签页打开

### 需要下载类型
- CSV - 下载到本地
- 图像文件（PNG、JPG） - 下载到本地
- PDF - 下载到本地
- Excel（XLSX、XLS） - 下载到本地

## 安全性考虑

### 1. 文件路径验证
- 使用Path对象处理文件路径
- 限制在输出目录内
- 防止目录遍历攻击

### 2. 文件大小限制
- 记录文件大小信息
- 防止过大文件传输

### 3. 文件类型验证
- 基于扩展名识别文件类型
- 只处理已知类型文件
- 忽略未知类型文件

### 4. 清理机制
- 定期清理旧文件
- 防止磁盘空间耗尽
- 可配置清理策略

## 性能优化

### 1. 异步执行
- 使用BackgroundTasks处理长时间任务
- 不阻塞主线程

### 2. 文件收集优化
- 只收集执行期间创建的文件
- 避免重复处理
- 使用时间戳过滤

### 3. 内存管理
- 流式处理大文件
- 及时清理临时数据
- 限制并发操作

## 扩展性设计

### 1. 文件类型扩展
在`ExecutionConfig.FILE_TYPE_MAP`中添加新类型：
```python
FILE_TYPE_MAP = {
    ".html": "html",
    ".csv": "csv",
    # 添加新类型
    ".parquet": "parquet",
    ".hdf5": "hdf5",
}
```

### 2. 自定义清理策略
```python
def cleanup_old_files(self, max_age_hours: int = 24, max_file_count: int = 100):
    """自定义清理策略"""
    # 实现自定义逻辑
```

### 3. 执行监控
添加执行监控和统计：
```python
@dataclass
class ExecutionMetrics:
    """执行指标"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_duration: float
    total_output_files: int
```

## 错误处理

### 1. 执行错误
- 捕获所有异常
- 记录详细错误信息
- 返回友好的错误消息

### 2. 文件操作错误
- 验证文件存在性
- 处理IO错误
- 提供重试机制

### 3. 网络错误
- 超时处理
- 重试逻辑
- 离线支持

## 日志记录

### 日志级别
- DEBUG: 详细调试信息
- INFO: 一般操作信息
- WARNING: 警告信息
- ERROR: 错误信息

### 日志内容
- 执行开始/结束时间
- Block执行状态
- 文件创建/删除
- 错误堆栈跟踪

## 测试建议

### 1. 单元测试
- ExecutionEngine测试
- 文件收集逻辑测试
- 错误处理测试

### 2. 集成测试
- API端点测试
- 前后端集成测试
- 文件操作测试

### 3. 性能测试
- 大量文件处理
- 长时间执行
- 并发执行

## 使用示例

### 前端调用

```typescript
// 执行Block图
const response = await fetch('/api/execution/execute', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    blocks: [...],
    connections: [...],
  }),
});

const result = await response.json();
console.log('执行结果:', result);
```

### 后端收集文件

```python

```

## 最佳实践

1. **文件命名**: 使用有意义的文件名，包含时间戳或UUID
2. **错误处理**: 始终处理可能的错误情况
3. **日志记录**: 记录关键操作和错误
4. **性能监控**: 监控执行时间和资源使用
5. **安全检查**: 验证所有用户输入和文件路径
6. **清理维护**: 定期清理旧文件和临时数据
7. **文档更新**: 保持文档与代码同步

## 未来改进

1. **实时进度**: WebSocket支持实时执行进度
2. **批量操作**: 支持批量文件下载
3. **预览功能**: 文件内容预览
4. **版本控制**: 输出文件版本管理
5. **云存储**: 支持云存储集成
6. **压缩传输**: 大文件压缩传输
7. **缓存机制**: 文件内容缓存
8. **权限管理**: 文件访问权限控制

## 故障排查

### 问题1: 文件未显示
**原因**: 文件创建时间不在执行期间
**解决**: 检查文件时间戳，确保在执行期间创建

### 问题2: 文件无法打开
**原因**: 文件类型不支持
**解决**: 下载文件到本地，使用相应软件打开

### 问题3: 执行失败
**原因**: Block执行错误
**解决**: 查看错误日志，检查Block配置

### 问题4: 文件删除失败
**原因**: 文件被占用
**解决**: 关闭文件后重试

## 联系方式

如有问题或建议，请联系开发团队。