<template>
  <section class="doc-section">
    <h1>Flow Playground 使用指南</h1>

    <h2>概述</h2>
    <p><strong>Flow Playground</strong> 是一个用于<strong>演练和测试</strong>的 Flow 可视化编辑器。它提供了一个轻量级的环境，让你可以快速实验新的 Flow 设计、测试 Block 的功能，而不需要担心影响生产数据。</p>

    <h3>适用场景</h3>
    <ul>
      <li><strong>学习练习</strong>：熟悉节点连接方式和数据流动</li>
      <li><strong>功能测试</strong>：验证 Block 的输入输出是否正确</li>
      <li><strong>快速原型</strong>：在构建正式 Flow 前先进行原型设计</li>
      <li><strong>调试验证</strong>：测试复杂的数据处理逻辑</li>
    </ul>

    <div class="note-card">
      <h3>重要提示</h3>
      <p>Playground 中的 Flow 数据保存在浏览器本地，不会保存到后端数据库。如需持久化存储和管理 Flow，请使用 <strong>Flow Manager</strong>。</p>
    </div>

    <h2>界面布局</h2>
    <ul>
      <li><strong>中央画布</strong>：主要编辑区域，用于放置和连接节点</li>
      <li><strong>顶部工具栏</strong>：保存、运行/停止等操作按钮</li>
      <li><strong>右侧面板</strong>：输出面板，显示执行结果和输出文件</li>
      <li><strong>下方面板</strong>：运行日志面板，显示实时执行日志（运行时自动展开）</li>
    </ul>

    <h2>基本操作</h2>
    <div class="operation-card">
      <h3>添加节点</h3>
      <p>在画布上<strong>右键点击</strong>，打开节点浏览菜单。按分类浏览可用节点，点击选择要添加的节点。</p>
    </div>
    <div class="operation-card">
      <h3>连接节点</h3>
      <p>拖拽一个节点的输出端口（右侧）到另一个节点的输入端口（左侧）。</p>
    </div>
    <div class="operation-card">
      <h3>删除节点</h3>
      <p>选中节点后按 Delete 键或 Backspace 键删除。</p>
    </div>
    <div class="operation-card">
      <h3>移动节点</h3>
      <p>拖拽节点标题栏移动位置。</p>
    </div>
    <div class="operation-card">
      <h3>配置参数</h3>
      <p>双击节点打开参数配置面板，编辑节点的输入值和配置选项。</p>
    </div>
    <div class="operation-card">
      <h3>缩放视图</h3>
      <p>使用鼠标滚轮缩放画布，双击画布自适应视图。</p>
    </div>
    <div class="operation-card">
      <h3>删除连接</h3>
      <p>右键点击连接线或拖拽端口分离连接。</p>
    </div>

    <h2>节点端口类型</h2>
    <ul>
      <li><strong>输入端口</strong>：位于节点左侧，接收上游数据</li>
      <li><strong>输出端口</strong>：位于节点右侧，向下游发送数据</li>
      <li><strong>数据类型</strong>：不同端口支持不同的数据类型，连接时会自动检查兼容性</li>
    </ul>

    <h2>输出面板</h2>
    <p>运行 Flow 后，右侧输出面板会显示：</p>
    <ul>
      <li><strong>执行状态</strong>：显示运行中、已完成、失败等状态</li>
      <li><strong>执行时长</strong>：Flow 运行所花费的时间</li>
      <li><strong>输出文件</strong>：生成的文件列表，可下载或打开查看</li>
      <li><strong>日志事件</strong>：节点的实时日志输出</li>
      <li><strong>错误信息</strong>：执行过程中的错误详情</li>
    </ul>

    <h2>运行日志面板</h2>
    <p>位于画布下方，运行 Flow 时自动展开，显示：</p>
    <ul>
      <li><strong>节点执行日志</strong>：每个节点的执行状态和输出</li>
      <li><strong>SSE 连接状态</strong>：与服务器的实时连接状态</li>
      <li><strong>错误和警告</strong>：执行过程中的错误和警告信息</li>
    </ul>

    <h2>保存和加载</h2>
    <p><strong>Flow Playground</strong> 将 Flow 数据保存在浏览器的 <code>localStorage</code> 中，不会保存到后端数据库：</p>
    <div class="note-card">
      <h3>存储位置</h3>
      <p>数据存储键为 <code>nodeflow_flow_{business}</code>，其中 <code>{business}</code> 是当前业务域（DEMO、WAVE、IOT、AI）。每个业务域的 Flow 独立存储。</p>
    </div>
    <div class="note-card">
      <h3>自动加载</h3>
      <p>打开 Playground 时会自动从 localStorage 加载当前业务域的 Flow。</p>
    </div>
    <div class="note-card">
      <h3>跨浏览器限制</h3>
      <p>由于数据存储在浏览器本地，更换浏览器或清除缓存会导致数据丢失。如需持久化存储，请使用 Flow Manager。</p>
    </div>

    <h2>运行 Flow</h2>
    <ul>
      <li>点击顶部工具栏的<strong>运行</strong>按钮开始执行 Flow</li>
      <li>运行过程中可以点击<strong>停止</strong>按钮中断执行</li>
      <li>运行结果会自动显示在输出面板中</li>
      <li>详细日志会在下方运行日志面板中实时更新</li>
    </ul>
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

.operation-card {
  background: #2d2d30;
  border: 1px solid #3c3c3c;
  border-radius: 6px;
  padding: 12px 16px;
  margin: 0 0 8px;
}

.operation-card h3 {
  margin: 0 0 4px;
  color: #4caf50;
}

.operation-card p {
  margin: 0;
}

.note-card {
  background: #2d2d30;
  border: 1px solid #3c3c3c;
  border-radius: 6px;
  padding: 12px 16px;
  margin: 0 0 8px;
}

.note-card h3 {
  margin: 0 0 4px;
  color: #d4a351;
}

.note-card p {
  margin: 0;
}
</style>