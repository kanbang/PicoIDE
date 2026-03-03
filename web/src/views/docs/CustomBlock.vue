<template>
  <section class="doc-section">
    <h1>自定义 Block 开发指南</h1>

    <h2>概述</h2>
    <p>自定义 Block 通过编写 Python 类继承 <code>BaseBlock</code> 来实现。每个 Block 定义了一个独立的功能模块，可以在 Flow 中复用。</p>

    <h2>BaseBlock 基类</h2>
    <div class="code-block">
      <pre>from node.base_block import BaseBlock

class MyBlock(BaseBlock):
    """自定义 Block 类"""

    NAME = "my_block"        # Block 唯一标识
    CATEGORY = "My Category" # 所属分类

    def __init__(self):
        super().__init__()
        # 初始化代码

    async def on_compute(self, execution_id: Optional[str] = None):
        """执行计算逻辑"""
        pass</pre>
    </div>

    <h2>核心属性</h2>
    <div class="api-item">
      <div class="api-method">NAME</div>
      <div class="api-desc">Block 的唯一标识符，必须在所有 Block 中唯一</div>
    </div>
    <div class="api-item">
      <div class="api-method">CATEGORY</div>
      <div class="api-desc">Block 所属的分类，用于在节点库中分组显示</div>
    </div>
    <div class="api-item">
      <div class="api-method">STREAMING</div>
      <div class="api-desc">标识 Block 是否支持流式处理。设置为 True 表示该节点可以持续接收和处理数据流，适用于实时数据处理场景。</div>
    </div>

    <h3>STREAMING 属性详解</h3>
    <p><code>STREAMING</code> 属性用于定义 Block 的数据处理模式：</p>
    <div class="code-block">
      <pre>class StreamBlock(BaseBlock):
    """流式处理 Block 示例"""

    NAME = "stream_processor"
    CATEGORY = "实时"
    STREAMING = True  # 启用流式模式</pre>
    </div>

    <h4>作用</h4>
    <ul>
      <li><strong>持续处理</strong>：启用后，Block 会持续监听输入端口，新数据到达时立即处理</li>
      <li><strong>低延迟</strong>：减少数据累积，实现近实时处理</li>
      <li><strong>资源优化</strong>：避免等待完整数据集，减少内存占用</li>
    </ul>

    <h4>应用场景</h4>
    <ul>
      <li><strong>实时监控</strong>：设备传感器数据实时监控和报警</li>
      <li><strong>信号处理</strong>：音频/视频流的实时分析和处理</li>
      <li><strong>数据采集</strong>：工业现场数据的持续采集和处理</li>
      <li><strong>日志分析</strong>：系统日志的实时解析和分析</li>
    </ul>

    <h4>流式 Block 开发要点</h4>
    <div class="note-card">
      <h3>数据缓冲</h3>
      <p>流式处理时，需要实现数据缓冲机制，防止数据丢失或处理积压。</p>
    </div>
    <div class="note-card">
      <h3>状态管理</h3>
      <p>维护内部状态以实现增量处理，如滑动窗口、累积统计等。</p>
    </div>
    <div class="note-card">
      <h3>异常处理</h3>
      <p>流式 Block 的异常不应中断整个流程，需要实现容错机制。</p>
    </div>

    <div class="code-block">
      <pre>class MovingAverage(BaseBlock):
    """移动平均流式处理示例"""

    NAME = "moving_average"
    CATEGORY = "实时"
    STREAMING = True

    def __init__(self):
        super().__init__()
        self.add_input("I-Value")
        self.add_output("O-Avg")
        self.add_number_option("窗口大小", default=10, min=1, max=100)

        # 内部状态
        self._buffer = []
        self._window_size = 10

    async def on_compute(self, execution_id: Optional[str] = None):
        # 获取新数据
        i_data = self.get_interface("I-Value")
        value = i_data["data"]["value"]

        # 更新窗口大小
        self._window_size = self.get_option("窗口大小")

        # 添加到缓冲区
        self._buffer.append(value)
        if len(self._buffer) > self._window_size:
            self._buffer.pop(0)

        # 计算移动平均
        avg = sum(self._buffer) / len(self._buffer)

        # 输出
        self.set_interface("O-Avg", {"data": {"value": avg}})</pre>
    </div>

    <h2>定义输入输出端口</h2>
    <div class="code-block">
      <pre>def __init__(self):
    super().__init__()

    # 添加输入端口
    self.add_input("I-Data")

    # 添加输出端口
    self.add_output("O-Result")</pre>
    </div>
    <p>端口命名建议：</p>
    <ul>
      <li>输入端口以 <code>I-</code> 开头，如 <code>I-Data</code></li>
      <li>输出端口以 <code>O-</code> 开头，如 <code>O-Result</code></li>
    </ul>

    <h2>添加配置选项</h2>
    <div class="code-block">
      <pre>def __init__(self):
    super().__init__()

    # 添加复选框选项
    self.add_checkbox_option("启用修正", default=True)

    # 添加数字输入选项
    self.add_number_option("阈值", default=100, min=0, max=1000)

    # 添加下拉选项
    self.add_select_option("模式", default="A", options=["A", "B", "C"])

    # 添加文本输入选项
    self.add_text_option("备注", default="")</pre>
    </div>

    <h2>获取输入数据</h2>
    <div class="code-block">
      <pre>async def on_compute(self, execution_id: Optional[str] = None):
    # 获取输入端口数据
    i_data = self.get_interface("I-Data")

    # 提取数据
    data = i_data["data"]
    x = np.array(data["x"])
    y = np.array(data["y"])

    # 提取元数据
    meta = data.get("meta", {})</pre>
    </div>

    <h2>设置输出数据</h2>
    <div class="code-block">
      <pre>async def on_compute(self, execution_id: Optional[str] = None):
    # ... 处理逻辑 ...

    # 创建元数据
    new_meta = SignalMetadata(
        fs=1000,
        unit="V",
        domain="frequency",
        data_type="spectrum"
    )

    # 设置输出
    self.set_interface(
        "O-Result",
        SignalData(
            x=freqs.tolist(),
            y=mag.tolist(),
            meta=new_meta,
            type="spectrum"
        ).to_dict()
    )</pre>
    </div>

    <h2>获取配置选项</h2>
    <div class="code-block">
      <pre>async def on_compute(self, execution_id: Optional[str] = None):
    # 获取配置选项
    enable_fix = self.get_option("启用修正")
    threshold = self.get_option("阈值")
    mode = self.get_option("模式")

    # 使用选项值
    if enable_fix and threshold > 0:
        # 处理逻辑
        pass</pre>
    </div>

    <h2>完整示例：FFT Block</h2>
    <div class="code-block">
      <pre>class FFT(BaseBlock):
    """
    工业级 FFT

    功能：
    - 单边幅值谱
    - 幅值修正
    - 频率分辨率计算

    输入：时域信号（建议已分段）
    输出：频域信号
    """

    NAME = "FFT"
    CATEGORY = "分析"

    def __init__(self):
        super().__init__()

        self.add_input("I-List-XY")
        self.add_output("O-List-XY")

        self.add_checkbox_option("幅值修正", default=True)

    async def on_compute(self, execution_id: Optional[str] = None):
        """执行计算"""
        try:
            i_data = self.get_interface("I-List-XY")

            if not self._validate_input_data(i_data):
                return

            data = i_data["data"]
            meta = data.get("meta", {})

            x = np.array(data["x"])
            y = np.array(data["y"])

            # 获取采样率
            fs = meta.get("fs")
            if fs is None:
                fs = calculate_fs_from_time_axis(x)

            N = len(y)
            if N < 2:
                raise DataValidationError("数据点数不足")

            # 计算FFT
            fft_vals = np.fft.rfft(y)

            # 幅值修正
            if self.get_option("幅值修正"):
                mag = np.abs(fft_vals) / N * 2.0
            else:
                mag = np.abs(fft_vals)

            # 频率轴
            freqs = np.fft.rfftfreq(N, 1.0 / fs)

            # 创建元数据
            new_meta = SignalMetadata(
                fs=fs,
                unit="V",
                domain="frequency",
                data_type="spectrum",
                df=fs / N,
                description="FFT频谱",
            )

            # 输出
            self.set_interface(
                "O-List-XY",
                SignalData(
                    x=freqs.tolist(),
                    y=mag.tolist(),
                    meta=new_meta,
                    type="spectrum"
                ).to_dict(),
            )

        except Exception as e:
            self._log_error(e, "FFT")
            raise</pre>
    </div>

    <h2>注意事项</h2>
    <div class="note-card">
      <h3>异步执行</h3>
      <p><code>on_compute</code> 是异步方法，必须使用 <code>async def</code> 定义。对于耗时操作，使用 <code>await</code> 或异步库。</p>
    </div>
    <div class="note-card">
      <h3>错误处理</h3>
      <p>必须使用 try-except 捕获异常，并通过 <code>self._log_error(e, "Block名称")</code> 记录错误。</p>
    </div>
    <div class="note-card">
      <h3>数据验证</h3>
      <p>在处理数据前，使用 <code>self._validate_input_data(i_data)</code> 验证输入数据的完整性。</p>
    </div>
    <div class="note-card">
      <h3>元数据管理</h3>
      <p>输出数据必须包含完整的元信息（采样率、单位、数据类型等），确保下游节点正确处理数据。</p>
    </div>
    <div class="note-card">
      <h3>性能优化</h3>
      <p>对于大数据处理，考虑分段处理、使用 numpy/pandas 等高效库。</p>
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

.doc-section code {
  background: #2d2d30;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #ce9178;
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