<template>
  <section class="doc-section">
    <h1>Flow Manager 使用指南</h1>

    <h2>概述</h2>
    <p><strong>Flow Manager</strong> 用于管理已保存的 Flow，包括列表查看、加载编辑、运行执行等操作。</p>

    <h2>界面布局</h2>
    <ul>
      <li><strong>左侧列表</strong>：显示所有已保存的 Flow，可按名称搜索</li>
      <li><strong>右侧编辑器</strong>：选中 Flow 后加载到 Playground 进行编辑</li>
      <li><strong>顶部工具栏</strong>：创建新 Flow、删除选中 Flow、运行等操作</li>
    </ul>

    <h2>基本操作</h2>
    <div class="operation-card">
      <h3>创建新 Flow</h3>
      <p>点击"创建新 Flow"按钮，输入 Flow 名称和描述即可创建空的 Flow。</p>
    </div>
    <div class="operation-card">
      <h3>加载 Flow</h3>
      <p>在左侧列表中点击 Flow 名称，将其加载到右侧编辑器。</p>
    </div>
    <div class="operation-card">
      <h3>编辑 Flow</h3>
      <p>在右侧编辑器中修改 Flow，点击"保存"按钮保存修改。</p>
    </div>
    <div class="operation-card">
      <h3>删除 Flow</h3>
      <p>选中 Flow 后点击"删除"按钮，确认后永久删除。</p>
    </div>
    <div class="operation-card">
      <h3>运行 Flow</h3>
      <p>选中 Flow 后点击"运行"按钮，执行 Flow 并在 Running Flows 页面中查看结果。</p>
    </div>
    <div class="operation-card">
      <h3>搜索 Flow</h3>
      <p>在搜索框中输入 Flow 名称或描述，快速查找 Flow。</p>
    </div>
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
</style>