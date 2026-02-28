# 输出文件系统集成说明

## 概述

基于现有的 `/api/flow/execute` API，实现了工业级的输出文件管理系统。

## 架构设计

### 后端修改（app/routes/flow.py）

#### 1. 新增功能

**输出文件收集：**
- 添加 `collect_output_files()` 函数
- 自动收集执行期间创建的文件
- 支持多种文件类型识别

**文件类型映射：**
```python
FILE_TYPE_MAP = {
    ".html": "html",
    ".csv": "csv",
    ".json": "json",
    ".txt": "text",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".pdf": "pdf",
    ".xlsx": "excel",
    ".xls": "excel",
}
```

#### 2. API端点更新

**修改后的 `/api/flow/execute` 端点：**
```python
@router.post("/execute")
async def execute(request: ExecuteRequest):
    # 执行 flow
    result = await run_flow(scripts, request.data["graph"] or {})
    
    # 收集输出文件
    output_files = collect_output_files(start_time)
    
    # 返回执行结果和输出文件
    return {
        "ok": True,
        "result": result,
        "output_files": output_files,
        "execution_time": time.time() - start_time,
        "timestamp": datetime.now().isoformat()
    }
```

**新增端点：**

1. `GET /api/flow/output-files` - 获取所有输出文件列表
2. `GET /api/flow/output-files/{file_id}` - 获取输出文件内容
3. `DELETE /api/flow/output-files/{file_id}` - 删除输出文件
4. `DELETE /api/flow/output-files/cleanup` - 清理旧输出文件

### 前端修改

#### 1. API层（web/src/api/flow.ts）

**新增接口：**
```typescript
export interface OutputFile {
  file_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  file_size: number;
  created_at: string;
  can_open: boolean;
  can_download: boolean;
}

export interface ExecuteResponse {
  ok: boolean;
  result?: any;
  output_files?: OutputFile[];
  execution_time?: number;
  timestamp?: string;
}
```

**新增函数：**
- `getOutputFiles()` - 获取所有输出文件
- `getOutputFile(fileId)` - 获取输出文件内容
- `deleteOutputFile(fileId)` - 删除输出文件
- `cleanupOutputFiles(maxAgeHours)` - 清理旧输出文件

#### 2. NodeFlow组件（web/src/components/NodeFlow/index.vue）

**修改内容：**
- RUN_COMMAND_ID 只 emit run 事件，不直接调用 API
- 暴露 outputPanelRef 供父组件访问
- 集成 OutputPanel 组件

#### 3. OutputPanel组件（web/src/components/OutputPanel.vue）

**功能：**
- 显示执行状态
- 列出输出文件
- 提供文件操作（打开、下载、删除）
- 使用 API 而不是直接调用 fetch

#### 4. 视图组件

**NodeFlowDemo.vue：**
- handleRun 方法调用 executeBlocks
- 更新 OutputPanel 的执行状态
- 显示执行结果

**SchemaManagerApiDemo.vue：**
- handleRun 方法调用 executeBlocks
- 更新 OutputPanel 的执行状态
- 显示执行结果

## 数据流程

### 1. 执行流程

```
用户点击"运行"
    ↓
NodeFlow emit run 事件
    ↓
父组件（NodeFlowDemo/SchemaManagerApiDemo）接收事件
    ↓
调用 executeBlocks API
    ↓
后端 /api/flow/execute 执行Block图
    ↓
Blocks生成输出文件（CSV、HTML等）
    ↓
后端收集输出文件
    ↓
返回 ExecutionResponse（包含 output_files）
    ↓
父组件更新 OutputPanel
    ↓
用户可以打开或下载文件
```

### 2. 文件操作流程

**打开文件：**
```
用户点击"打开"
    ↓
OutputPanel 调用 getOutputFile API
    ↓
后端返回文件内容（Blob）
    ↓
前端创建 ObjectURL
    ↓
浏览器在新标签页打开文件
```

**下载文件：**
```
用户点击"下载"
    ↓
OutputPanel 调用 getOutputFile API
    ↓
后端返回文件内容（Blob）
    ↓
前端创建下载链接
    ↓
浏览器触发文件下载
```

## 使用示例

### 前端调用

```typescript
// 执行Block图
const result = await executeBlocks({ 
  scripts: [], 
  flow: { graph: flow } 
});

// 更新输出面板
if (result.output_files) {
  outputPanelRef.value.setOutputFiles(result.output_files);
}
```

### 后端执行

```python
# 自动收集输出文件
output_files = collect_output_files(start_time)

# 返回执行结果
return {
    "ok": True,
    "result": result,
    "output_files": output_files,
    "execution_time": duration,
}
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
- 使用 Path 对象处理文件路径
- 限制在输出目录内
- 防止目录遍历攻击

### 2. 文件类型验证
- 基于扩展名识别文件类型
- 只处理已知类型文件
- 忽略未知类型文件

### 3. 文件ID安全
- 使用文件名生成 file_id
- 避免直接暴露文件路径
- 防止路径遍历攻击

## 性能优化

### 1. 异步执行
- 使用 async/await 处理长时间任务
- 不阻塞主线程

### 2. 文件收集优化
- 只收集执行期间创建的文件
- 使用时间戳过滤
- 避免重复处理

### 3. Blob处理
- 使用 URL.createObjectURL 创建临时URL
- 及时释放URL对象
- 避免内存泄漏

## 扩展性设计

### 1. 文件类型扩展
在 `FILE_TYPE_MAP` 中添加新类型：
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
@router.delete("/output-files/cleanup")
async def cleanup_output_files(
    max_age_hours: int = 24,
    max_file_count: int = 100
):
    """自定义清理策略"""
    # 实现自定义逻辑
```

## 测试建议

### 1. 单元测试
- 文件收集逻辑测试
- API端点测试
- 文件操作测试

### 2. 集成测试
- 前后端集成测试
- 文件生成和收集测试
- 文件打开和下载测试

### 3. 性能测试
- 大量文件处理测试
- 长时间执行测试
- 并发执行测试

## 最佳实践

1. **文件命名**: 使用有意义的文件名，包含时间戳或UUID
2. **错误处理**: 始终处理可能的错误情况
3. **日志记录**: 记录关键操作和错误
4. **状态管理**: 正确管理执行状态
5. **资源清理**: 及时清理临时资源
6. **用户反馈**: 提供清晰的用户反馈

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

### 问题4: 文件下载失败
**原因**: 文件被占用或不存在
**解决**: 检查文件状态，重试下载

## 总结

基于现有的 `/api/flow/execute` API，成功实现了工业级的输出文件管理系统：

✅ 后端：扩展了 execute 端点，添加了输出文件收集和管理功能
✅ 前端：更新了 API 层，添加了输出文件管理功能
✅ 集成：NodeFlow 组件与 OutputPanel 组件无缝集成
✅ 用户体验：提供了直观的文件操作界面
✅ 可维护性：代码结构清晰，易于扩展和维护

这个系统完全基于现有架构，没有引入新的依赖，保持了代码的一致性和可维护性。