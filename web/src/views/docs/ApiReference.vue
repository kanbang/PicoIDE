<template>
  <section class="doc-section">
    <h1>API 参考</h1>

    <h2>Flow API</h2>
    <div class="api-item">
      <div class="api-method">GET /api/flows</div>
      <div class="api-desc">获取所有 Flow 列表</div>
    </div>
    <div class="api-item">
      <div class="api-method">GET /api/flows/{flow_id}</div>
      <div class="api-desc">获取指定 Flow 详情</div>
    </div>
    <div class="api-item">
      <div class="api-method">POST /api/flows</div>
      <div class="api-desc">创建新 Flow</div>
    </div>
    <div class="api-item">
      <div class="api-method">PUT /api/flows/{flow_id}</div>
      <div class="api-desc">更新 Flow</div>
    </div>
    <div class="api-item">
      <div class="api-method">DELETE /api/flows/{flow_id}</div>
      <div class="api-desc">删除 Flow</div>
    </div>

    <h2>Execution API</h2>
    <div class="api-item">
      <div class="api-method">POST /api/engine/execute-saved</div>
      <div class="api-desc">执行 Flow</div>
    </div>
    <div class="api-item">
      <div class="api-method">POST /api/engine/stop/{execution_id}</div>
      <div class="api-desc">停止执行</div>
    </div>
    <div class="api-item">
      <div class="api-method">GET /api/engine/executions</div>
      <div class="api-desc">获取执行记录列表，支持时间范围筛选</div>
    </div>
    <div class="api-item">
      <div class="api-method">GET /api/engine/executions/{execution_id}</div>
      <div class="api-desc">获取执行详情</div>
    </div>
    <div class="api-item">
      <div class="api-method">GET /api/engine/executions/{execution_id}/outputs</div>
      <div class="api-desc">获取执行输出文件</div>
    </div>

    <h2>Block API</h2>
    <div class="api-item">
      <div class="api-method">GET /api/blocks</div>
      <div class="api-desc">获取所有 Block 定义</div>
    </div>
    <div class="api-item">
      <div class="api-method">GET /api/blocks/{block_name}</div>
      <div class="api-desc">获取指定 Block 详情</div>
    </div>
    <div class="api-item">
      <div class="api-method">POST /api/blocks</div>
      <div class="api-desc">创建新 Block（通过代码定义）</div>
    </div>

    <h2>查询参数说明</h2>
    <h3>/api/engine/executions</h3>
    <table class="api-table">
      <thead>
        <tr>
          <th>参数</th>
          <th>类型</th>
          <th>描述</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>start_time</td>
          <td>string</td>
          <td>开始时间（ISO 8601 格式）</td>
        </tr>
        <tr>
          <td>end_time</td>
          <td>string</td>
          <td>结束时间（ISO 8601 格式）</td>
        </tr>
        <tr>
          <td>status</td>
          <td>string</td>
          <td>执行状态（running/completed/failed）</td>
        </tr>
        <tr>
          <td>limit</td>
          <td>number</td>
          <td>返回数量限制（默认 20）</td>
        </tr>
        <tr>
          <td>offset</td>
          <td>number</td>
          <td>偏移量（默认 0）</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.doc-section h1 {
  margin: 0 0 24px;
  font-size: 28px;
  color: #4caf50;
}

.doc-section h2 {
  margin: 32px 0 16px;
  font-size: 20px;
  color: #e0e0e0;
}

.doc-section h3 {
  margin: 12px 0 8px;
  font-size: 16px;
  color: #c0c0c0;
}

.doc-section p {
  margin: 0 0 12px;
  line-height: 1.6;
  color: #a0a0a0;
}

.doc-section ul,
.doc-section ol {
  margin: 0 0 16px;
  padding-left: 24px;
}

.doc-section li {
  margin: 6px 0;
  color: #a0a0a0;
  line-height: 1.6;
}

.doc-section strong {
  color: #e0e0e0;
}

.doc-section code {
  background: #2d2d30;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #ce9178;
}

.api-item {
  background: #2d2d30;
  border: 1px solid #3c3c3c;
  border-left: 3px solid #4caf50;
  border-radius: 4px;
  padding: 12px 16px;
  margin: 0 0 12px;
}

.api-method {
  font-family: 'Consolas', monospace;
  font-size: 14px;
  color: #4caf50;
  margin-bottom: 4px;
}

.api-desc {
  color: #888;
  font-size: 13px;
}

.api-table {
  width: 100%;
  border-collapse: collapse;
  background: #2d2d30;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 16px;
}

.api-table th,
.api-table td {
  padding: 10px 16px;
  text-align: left;
  border-bottom: 1px solid #3c3c3c;
}

.api-table th {
  background: #3c3c3c;
  color: #e0e0e0;
  font-weight: 500;
}

.api-table td {
  color: #a0a0a0;
}

.api-table tr:last-child td {
  border-bottom: none;
}

.api-table code {
  background: #1e1e1e;
  padding: 1px 4px;
}
</style>