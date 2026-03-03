<template>
  <section class="doc-section">
    <h1>Block Builder 使用指南</h1>

    <h2>概述</h2>
    <p><strong>Block Builder</strong> 集成了 VS Code Web 版编辑器，提供完整的代码编辑体验。通过编写 Python 脚本来定义自定义 Block，实现更复杂的业务逻辑。</p>

    <h2>界面布局</h2>
    <ul>
      <li><strong>左侧文件浏览器</strong>：显示和编辑 Block 脚本文件，支持文件夹组织</li>
      <li><strong>中央代码编辑器</strong>：VS Code 风格的代码编辑器，支持语法高亮、自动补全、代码导航</li>
    </ul>

    <h2>文件组织</h2>
    <p>推荐<strong>每个 Block 一个文件</strong>，便于管理和维护：</p>
    <div class="code-block">
      <pre>/blocks/
  ├── fft.py              # FFT Block
  ├── filter.py           # 滤波器 Block
  ├── analysis.py         # 数据分析 Block
  └── custom/             # 自定义 Block 目录
      ├── sensor.py
      └── converter.py</pre>
    </div>
    <p>文件命名建议使用小写字母和下划线，与 Block 的 NAME 属性保持一致或相关联。</p>

    <h2>基本操作</h2>
    <div class="operation-card">
      <h3>创建文件</h3>
      <p>在左侧文件浏览器中右键点击目录，选择新建文件或文件夹。</p>
    </div>
    <div class="operation-card">
      <h3>编写代码</h3>
      <p>在编辑器中编写继承自 <code>BaseBlock</code> 的 Python 类。</p>
    </div>
    <div class="operation-card">
      <h3>保存文件</h3>
      <p>使用 Ctrl+S (Cmd+S) 或点击工具栏保存按钮。文件会自动保存到后端虚拟文件系统。</p>
    </div>
    <div class="operation-card">
      <h3>验证代码</h3>
      <p>在 Flow Playground 中右键菜单查看新创建的 Block 是否可用。</p>
    </div>

    <h2>在 Playground 中使用自定义 Block</h2>
    <p>保存的 Block 脚本会自动注册到当前业务域，在 <strong>Flow Playground</strong> 中：</p>
    <ul>
      <li><strong>右键点击</strong>画布空白处，打开节点浏览菜单</li>
      <li><strong>按分类</strong>浏览，找到自定义 Block 所在的分类</li>
      <li><strong>点击选择</strong>自定义 Block，将其添加到画布</li>
    </ul>

    <h2>业务域关联</h2>
    <p>Block Builder 中的文件与当前选中的业务域关联：</p>
    <ul>
      <li><strong>DEMO</strong>：创建的 Block 只在 DEMO 业务域下可用</li>
      <li><strong>WAVE</strong>：创建的 Block 只在 WAVE 业务域下可用</li>
      <li><strong>IOT</strong>：创建的 Block 只在 IOT 业务域下可用</li>
      <li><strong>AI</strong>：创建的 Block 只在 AI 业务域下可用</li>
    </ul>

    <div class="note-card">
      <h3>重要提示</h3>
      <p>切换业务域后，之前在其他业务域创建的 Block 脚本不会自动显示。每个业务域的脚本独立存储在虚拟文件系统中。如需跨业务域使用相同的 Block，需要分别在每个业务域下创建对应的脚本文件。</p>
    </div>

    <h2>存储机制</h2>
    <p>Block 脚本存储在后端虚拟文件系统（VFS）中：</p>
    <ul>
      <li>通过 <code>/api/vfs</code> 接口进行文件读写操作</li>
      <li>文件按业务域隔离存储</li>
      <li>支持创建目录、文件、删除等基本文件操作</li>
    </ul>

    <h2>开发建议</h2>
    <ul>
      <li><strong>一个文件一个 Block</strong>：便于定位和调试问题</li>
      <li><strong>使用清晰的命名</strong>：文件名和 Block NAME 保持一致</li>
      <li><strong>添加文档字符串</strong>：为 Block 类添加详细的文档说明</li>
      <li><strong>错误处理</strong>：在 <code>on_compute</code> 中添加 try-except 处理异常</li>
      <li><strong>日志记录</strong>：使用 <code>self._logger</code> 记录关键信息便于调试</li>
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