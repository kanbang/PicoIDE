<template>
  <section class="doc-section">
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

    <h2>业务域</h2>
    <p>顶部导航栏中的 <strong>业务</strong> 下拉菜单用于切换不同的业务域。每种业务域都有专属的 Block 类型：</p>
    <ul>
      <li><strong>DEMO</strong> - 演示 Block，用于学习和测试</li>
      <li><strong>WAVE</strong> - 波形分析 Block，用于信号处理</li>
      <li><strong>IOT</strong> - 物联网 Block，用于设备连接和数据采集</li>
      <li><strong>AI</strong> - AI Block，用于机器学习和推理</li>
    </ul>

    <h3>业务域工作原理</h3>
    <p>后端通过 <code>BlocksManager</code> 管理不同业务域的 Block 注册表：</p>
    <div class="code-block">
      <pre># 静态 Block 注册表（后端）
STATIC_BLOCKS_MAP = {
    "DEMO": DEMO_BLOCKS,
    "WAVE": DAQ_BLOCKS,
    # 更多业务域...
}

# 动态 Block 通过脚本注册
blocks_registry.register("WAVE", dynamic_blocks)</pre>
    </div>
    <p>当你在前端切换业务域时，会请求后端获取该业务域对应的 Block 列表。Flow Playground 的节点面板会根据当前业务域显示可用的 Block。</p>

    <h3>自定义 Block 的业务域归属</h3>
    <p>通过 <strong>Block Builder</strong> 创建的 Block 会被注册到当前选中的业务域。例如：</p>
    <ul>
      <li>选择 "WAVE" 业务域后创建的 Block，只在 WAVE 模式下可用</li>
      <li>选择 "DEMO" 业务域后创建的 Block，只在 DEMO 模式下可用</li>
    </ul>

    <h2>基本工作流程</h2>
    <ol class="steps">
      <li>选择合适的业务域</li>
      <li>在 <strong>Flow Playground</strong> 中拖拽节点到画布</li>
      <li>配置节点的参数（双击节点或使用侧边栏）</li>
      <li>通过拖拽连接节点之间的端口</li>
      <li>保存 Flow</li>
      <li>在 <strong>Flow Manager</strong> 中管理和运行 Flow</li>
      <li>在 <strong>Running Flows</strong> 中监控执行状态</li>
    </ol>
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

.steps {
  background: #2d2d30;
  border-radius: 6px;
  padding: 16px 16px 16px 40px;
}

.steps li {
  margin: 8px 0;
}
</style>