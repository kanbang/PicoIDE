<!--
 * @Descripttion: NodeFlow 文档页面
 * @version: 0.x
 * @Date: 2026-02-24
-->
<script setup lang="ts">
import { ref } from 'vue';

const activeSection = ref<string>('intro');

const sections = [
  { id: 'intro', title: '快速入门' },
  { id: 'flow', title: 'Flow 使用' },
  { id: 'blocks', title: 'Block 使用' },
  { id: 'custom', title: '自定义 Node' },
  { id: 'api', title: 'API 参考' },
];
</script>

<template>
  <div class="documentation">
    <!-- 侧边导航 -->
    <div class="sidebar">
      <h2 class="sidebar-title">NodeFlow 文档</h2>
      <nav class="nav-menu">
        <button
          v-for="section in sections"
          :key="section.id"
          :class="['nav-item', { active: activeSection === section.id }]"
          @click="activeSection = section.id"
        >
          {{ section.title }}
        </button>
      </nav>
    </div>

    <!-- 主内容区 -->
    <div class="content">
      <section v-if="activeSection === 'intro'" class="doc-section">
        <h1>快速入门</h1>
        <p>NodeFlow 是一个基于可视化节点编程的工作流引擎，让你通过拖拽和连接节点来构建复杂的业务流程。</p>

        <h2>核心概念</h2>
        <div class="concept-card">
          <h3>Flow（流）</h3>
          <p>一个 Flow 是由多个节点和连接组成的完整工作流程。每个 Flow 都有唯一的 ID 和配置。</p>
        </div>
        <div class="concept-card">
          <h3>Node（节点）</h3>
          <p>节点是 Flow 中的基本单元，每个节点代表一个具体的操作或功能。节点有输入和输出端口，用于传递数据。</p>
        </div>
        <div class="concept-card">
          <h3>Connection（连接）</h3>
          <p>连接是节点之间的数据通道，将一个节点的输出端口连接到另一个节点的输入端口，实现数据流动。</p>
        </div>
        <div class="concept-card">
          <h3>Port（端口）</h3>
          <p>端口是节点的数据输入/输出点。输入端口接收数据，输出端口发送数据。</p>
        </div>

        <h2>基本工作流程</h2>
        <ol class="steps">
          <li>在 <strong>Flow Playground</strong> 中拖拽节点到画布</li>
          <li>配置节点的参数（双击节点或使用侧边栏）</li>
          <li>通过拖拽连接节点之间的端口</li>
          <li>保存 Flow</li>
          <li>在 <strong>Flow Manager</strong> 中管理和运行 Flow</li>
          <li>在 <strong>Running Flows</strong> 中监控执行状态</li>
        </ol>
      </section>

      <section v-if="activeSection === 'flow'" class="doc-section">
        <h1>Flow 使用指南</h1>

        <h2>创建 Flow</h2>
        <p>在 <strong>Flow Manager</strong> 页面，点击"创建新 Flow"按钮，输入 Flow 名称和描述即可创建。</p>

        <h2>编辑 Flow</h2>
        <ul>
          <li><strong>添加节点</strong>：从左侧节点面板拖拽节点到画布</li>
          <li><strong>连接节点</strong>：拖拽一个节点的输出端口到另一个节点的输入端口</li>
          <li><strong>删除节点</strong>：选中节点后按 Delete 键或右键删除</li>
          <li><strong>移动节点</strong>：拖拽节点标题栏移动位置</li>
          <li><strong>缩放视图</strong>：使用鼠标滚轮或双击画布自适应视图</li>
        </ul>

        <h2>保存和加载 Flow</h2>
        <p>编辑完成后，点击"保存"按钮将 Flow 保存到后端数据库。已保存的 Flow 可以在 Flow Manager 中加载和编辑。</p>

        <h2>运行 Flow</h2>
        <p>在 Flow Manager 中，选择一个 Flow 后点击"运行"按钮即可执行。执行状态可以在 <strong>Running Flows</strong> 页面中实时查看。</p>
      </section>

      <section v-if="activeSection === 'blocks'" class="doc-section">
        <h1>Block 使用指南</h1>

        <h2>内置 Block</h2>
        <p>系统提供了多种内置 Block，涵盖常用功能：</p>
        <div class="block-list">
          <div class="block-item">
            <strong>数据处理</strong>
            <span>JSON 解析、数据转换、格式化等</span>
          </div>
          <div class="block-item">
            <strong>HTTP 请求</strong>
            <span>GET/POST 请求、API 调用等</span>
          </div>
          <div class="block-item">
            <strong>文件操作</strong>
            <span>文件读写、目录操作等</span>
          </div>
          <div class="block-item">
            <strong>逻辑控制</strong>
            <span>条件分支、循环、延迟等</span>
          </div>
          <div class="block-item">
            <strong>输出</strong>
            <span>日志输出、数据输出等</span>
          </div>
        </div>

        <h2>Block 参数配置</h2>
        <p>每个 Block 都有自己的参数面板，在右侧面板中可以配置：</p>
        <ul>
          <li><strong>输入端口</strong>：定义接收的数据类型和名称</li>
          <li><strong>输出端口</strong>：定义输出的数据类型和名称</li>
          <li><strong>选项</strong>：Block 的配置选项，如超时时间、重试次数等</li>
        </ul>
      </section>

      <section v-if="activeSection === 'custom'" class="doc-section">
        <h1>自定义 Node</h1>

        <h2>概述</h2>
        <p>通过 <strong>Block Builder</strong> 页面，你可以创建自定义的 Block 来满足特定业务需求。</p>

        <h2>Block 定义结构</h2>
        <div class="code-block">
          <pre>{
  "name": "my_custom_block",        // Block 唯一标识
  "displayName": "我的自定义节点",   // 显示名称
  "category": "My Category",        // 分类
  "inputs": [                       // 输入端口定义
    {
      "name": "data",
      "type": "string",
      "required": true
    }
  ],
  "outputs": [                      // 输出端口定义
    {
      "name": "result",
      "type": "string"
    }
  ],
  "options": [                      // 配置选项
    {
      "name": "timeout",
      "type": "number",
      "default": 30,
      "label": "超时时间(秒)"
    }
  ],
  "code": "// 执行逻辑代码"        // 执行逻辑
}</pre>
        </div>

        <h2>创建自定义 Block 步骤</h2>
        <ol class="steps">
          <li>打开 <strong>Block Builder</strong> 页面</li>
          <li>填写 Block 基本信息（名称、分类等）</li>
          <li>定义输入和输出端口</li>
          <li>添加配置选项</li>
          <li>编写执行逻辑代码</li>
          <li>点击"保存 Block"提交</li>
        </ol>

        <h2>代码执行环境</h2>
        <p>Block 的执行代码运行在后端 Python 环境中，可以使用：</p>
        <ul>
          <li><strong>输入数据</strong>：通过 <code>inputs</code> 字典获取输入端口的数据</li>
          <li><strong>配置选项</strong>：通过 <code>options</code> 字典获取配置值</li>
          <li><strong>输出数据</strong>：通过 <code>return</code> 返回输出端口的数据</li>
        </ul>

        <div class="code-block">
          <pre># 示例：数据转换 Block
def execute(inputs, options):
    data = inputs.get('data', '')
    # 处理逻辑
    result = data.upper()
    # 返回结果
    return {'result': result}</pre>
        </div>

        <h2>端口类型</h2>
        <p>支持的数据类型：</p>
        <ul>
          <li><code>string</code> - 字符串</li>
          <li><code>number</code> - 数字</li>
          <li><code>boolean</code> - 布尔值</li>
          <li><code>object</code> - JSON 对象</li>
          <li><code>array</code> - 数组</li>
          <li><code>any</code> - 任意类型</li>
        </ul>
      </section>

      <section v-if="activeSection === 'api'" class="doc-section">
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
          <div class="api-method">POST /api/engine/execute</div>
          <div class="api-desc">执行 Flow</div>
        </div>
        <div class="api-item">
          <div class="api-method">POST /api/engine/stop/{execution_id}</div>
          <div class="api-desc">停止执行</div>
        </div>
        <div class="api-item">
          <div class="api-method">GET /api/engine/executions</div>
          <div class="api-desc">获取执行记录列表</div>
        </div>
        <div class="api-item">
          <div class="api-method">GET /api/engine/executions/{execution_id}</div>
          <div class="api-desc">获取执行详情</div>
        </div>

        <h2>Block API</h2>
        <div class="api-item">
          <div class="api-method">GET /api/blocks</div>
          <div class="api-desc">获取所有 Block 定义</div>
        </div>
        <div class="api-item">
          <div class="api-method">POST /api/blocks</div>
          <div class="api-desc">创建新 Block</div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.documentation {
  display: flex;
  width: 100%;
  height: 100%;
  background: #1e1e1e;
  color: #e0e0e0;
}

.sidebar {
  width: 240px;
  background: #252526;
  border-right: 1px solid #3c3c3c;
  display: flex;
  flex-direction: column;
  padding: 16px;
  flex-shrink: 0;
}

.sidebar-title {
  margin: 0 0 16px;
  font-size: 16px;
  color: #4caf50;
  padding-bottom: 12px;
  border-bottom: 1px solid #3c3c3c;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  padding: 10px 12px;
  background: transparent;
  border: none;
  color: #888;
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
  transition: all 0.2s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #e0e0e0;
}

.nav-item.active {
  background: rgba(76, 175, 80, 0.15);
  color: #4caf50;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 32px 48px;
}

.doc-section {
  max-width: 900px;
}

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

.concept-card {
  background: #2d2d30;
  border: 1px solid #3c3c3c;
  border-radius: 6px;
  padding: 16px;
  margin: 0 0 12px;
}

.concept-card h3 {
  margin: 0 0 8px;
  color: #4caf50;
}

.concept-card p {
  margin: 0;
}

.steps {
  background: #2d2d30;
  border-radius: 6px;
  padding: 16px 16px 16px 40px;
}

.steps li {
  margin: 8px 0;
}

.block-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.block-item {
  background: #2d2d30;
  border: 1px solid #3c3c3c;
  border-radius: 6px;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.block-item strong {
  color: #4caf50;
}

.block-item span {
  color: #888;
  font-size: 13px;
}

.code-block {
  background: #1e1e1e;
  border: 1px solid #3c3c3c;
  border-radius: 6px;
  padding: 16px;
  margin: 0 0 16px;
  overflow-x: auto;
}

.code-block pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #d4d4d4;
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

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #3c3c3c;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #4a4a4a;
}
</style>