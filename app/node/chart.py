import json
from flow.block import BaseBlock


class BaseChartViewer(BaseBlock):
    """
    图表查看器基类

    功能：
    - 生成交互式HTML图表
    - 支持多种图表类型
    - 可配置样式和交互
    """

    NAME = "BaseChartViewer"
    CATEGORY = "输出"

    def __init__(self, default_type: str = "line"):
        super().__init__()

        self.add_input("I-List-XY")

        # 使用统一的输出目录
        default_filename = f"{self.NAME.lower().replace('viewer', '')}_chart.html"
        self.add_text_input_option("文件路径", default=default_filename)
        self.add_text_input_option(
            "标题", default=f"{self.NAME.replace('Viewer', '')} Chart"
        )
        self.add_integer_option("宽度 (px)", default=1200, min_val=800, max_val=2000)
        self.add_integer_option("高度 (px)", default=700, min_val=500, max_val=1200)
        self.add_checkbox_option("显示网格", default=True)
        self.add_checkbox_option("显示图例", default=True)
        self.add_checkbox_option("启用滚轮缩放", default=True)
        self.add_checkbox_option("启用拖拽平移", default=True)

        self.chart_type = default_type

    def _generate_chart(self, execution_id: str = None):
        """生成图表"""
        try:
            i_data = self.get_interface("I-List-XY")

            if not self._validate_input_data(i_data):
                return

            # 直接从SignalData格式中提取数据
            inner = i_data.get("data", {})
            x_raw = inner.get("x", [])
            y_raw = inner.get("y", [])

            # 如果x为空但y不为空，生成索引作为x
            if not x_raw and y_raw:
                x_raw = list(range(len(y_raw)))

            if len(y_raw) == 0:
                self._logger.warning("Y数据为空")
                return

            # 根据图表类型处理数据
            if self.chart_type == "bar":
                if len(x_raw) == 0 or len(x_raw) != len(y_raw):
                    x_data = list(range(len(y_raw)))
                else:
                    x_data = x_raw
                y_data = y_raw
                border_color = "#3b82f6"
                background_color = "rgba(59, 130, 246, 0.7)"
                tension = 0
                point_radius = 0

            elif self.chart_type == "scatter":
                if len(x_raw) == 0 or len(x_raw) != len(y_raw):
                    self._logger.warning("Scatter图需要完整的X/Y坐标")
                    return
                x_data = x_raw
                y_data = y_raw
                border_color = "rgba(59, 130, 246, 0.4)"
                background_color = "#3b82f6"
                tension = 0
                point_radius = 5

            else:  # line
                if len(x_raw) == 0 or len(x_raw) != len(y_raw):
                    x_data = list(range(len(y_raw)))
                else:
                    x_data = x_raw
                y_data = y_raw
                border_color = "#3b82f6"
                background_color = "rgba(59, 130, 246, 0.05)"
                tension = 0.15
                point_radius = 1.5

            # 生成JSON
            x_json = json.dumps(x_data)
            y_json = json.dumps(y_data)

            # 获取配置
            file_path = self.get_option("文件路径")
            title = self.get_option("标题")
            width = self.get_option("宽度 (px)")
            height = self.get_option("高度 (px)")
            show_grid = self.get_option("显示网格")
            show_legend = self.get_option("显示图例")
            enable_wheel = self.get_option("启用滚轮缩放")
            enable_drag = self.get_option("启用拖拽平移")

            # 确定X轴标签
            typ = i_data.get("type", "")
            x_label = (
                "Time (s)"
                if typ in ["channel", "filtered", "envelope"]
                else (
                    "Frequency (Hz)"
                    if typ == "fourier"
                    else "Order" if typ == "order" else "X"
                )
            )

            # 生成HTML
            html_content = self._generate_html(
                title,
                width,
                height,
                x_label,
                x_json,
                y_json,
                border_color,
                background_color,
                tension,
                point_radius,
                show_grid,
                show_legend,
                enable_wheel,
                enable_drag,
            )

            # 使用通用文件写入方法
            def write_html(full_path, mode: str):
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                self._logger.info(f"图表已生成: {full_path}")

            self._write_file(
                filename=file_path,
                write_func=write_html,
                execution_id=execution_id,
                description=f"{title}图表",
                metadata={
                    "chart_type": self.chart_type,
                    "title": title,
                    "width": width,
                    "height": height,
                },
            )

        except Exception as e:
            self._log_error(e, "图表生成")
            raise

    def _generate_html(
        self,
        title,
        width,
        height,
        x_label,
        x_json,
        y_json,
        border_color,
        background_color,
        tension,
        point_radius,
        show_grid,
        show_legend,
        enable_wheel,
        enable_drag,
    ) -> str:
        """生成HTML内容"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/hammerjs@2.0.8"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); margin: 0; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: {width}px; margin: 0 auto; background: white; border-radius: 16px;
                      box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }}
        header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
        h1 {{ margin: 0; font-weight: 500; font-size: 1.8em; }}
        .hint {{ 
            text-align: center; color: #64748b; font-size: 0.85em; 
            margin: 8px 0 12px 0; padding: 6px 0;
            background: rgba(37, 99, 235, 0.05); border-radius: 6px;
        }}
        .chart-wrapper {{ position: relative; height: {height}px; padding: 20px; cursor: default; }}
        .chart-wrapper:hover {{ cursor: grab; }}
        .chart-wrapper:active {{ cursor: grabbing; }}
    </style>
</head>
<body>
    <div class="container">
        <header><h1>{title}</h1></header>
        <div class="hint">
            交互提示：滚轮缩放 · 左键拖拽平移 · 双击重置
        </div>
        <div class="chart-wrapper">
            <canvas id="chart"></canvas>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('chart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: '{self.chart_type}',
            data: {{ 
                labels: {x_json}, 
                datasets: [{{
                    label: '{title}',
                    data: {y_json},
                    borderColor: '{border_color}',
                    backgroundColor: '{background_color}',
                    borderWidth: 2,
                    tension: {tension},
                    pointRadius: {point_radius},
                    fill: false
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                animation: {{ duration: 800 }},
                interaction: {{ intersect: false, mode: 'index' }},
plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        cornerRadius: 8,
                        padding: 10
                    }},
                    zoom: {{
                        pan: {{
                            enabled: {str(enable_drag).lower()},
                            mode: 'x',
                            modifierKey: null,
                            threshold: 1,
                            speed: 20
                        }},
                        zoom: {{
                            wheel: {{ enabled: {str(enable_wheel).lower()} }},
                            pinch: {{ enabled: true }},
                            mode: 'x'
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{ display: true, text: '{x_label}', font: {{ size: 14 }} }},
                        grid: {{ display: {str(show_grid).lower()}, color: 'rgba(0,0,0,0.05)' }}
                    }},
                    y: {{
                        title: {{ display: true, text: 'Amplitude', font: {{ size: 14 }} }},
                        grid: {{ display: {str(show_grid).lower()}, color: 'rgba(0,0,0,0.05)' }}
                    }}
                }}
            }}
        }});

        document.querySelector('canvas').addEventListener('dblclick', (e) => {{
            e.preventDefault();
            chart.resetZoom('none');
        }});
    </script>
</body>
</html>
"""


class LineChartViewer(BaseChartViewer):
    """交互式折线图查看器"""

    NAME = "LineChartViewer"
    CATEGORY = "输出"

    def __init__(self):
        super().__init__(default_type="line")

    async def on_compute(self, execution_id: Optional[str] = None):
        self._generate_chart(execution_id)


class BarChartViewer(BaseChartViewer):
    """交互式柱状图查看器"""

    NAME = "BarChartViewer"
    CATEGORY = "输出"

    def __init__(self):
        super().__init__(default_type="bar")

    async def on_compute(self, execution_id: Optional[str] = None):
        self._generate_chart(execution_id)


class ScatterChartViewer(BaseChartViewer):
    """交互式散点图查看器"""

    NAME = "ScatterChartViewer"
    CATEGORY = "输出"

    def __init__(self):
        super().__init__(default_type="scatter")

    async def on_compute(self, execution_id: Optional[str] = None):
        self._generate_chart(execution_id)


class TrajectoryChartViewer(BaseBlock):
    """
    轨迹图查看器（通用X-Y轨迹显示）

    功能：
    - 显示两路信号的轨迹（X-Y平面）
    - 适合显示转子轴心轨迹、相图、李萨如曲线等
    - 支持交互式缩放和旋转
    - 颜色表示时间进程

    输入：
    - I-List-X: X方向数据（list1d格式）
    - I-List-Y: Y方向数据（list1d格式）

    使用场景：
    - 轴心轨迹分析
    - 相位平面分析
    - 李萨如图形
    - 任意X-Y轨迹显示
    """

    NAME = "TrajectoryChartViewer"
    CATEGORY = "输出"

    def __init__(self):
        super().__init__()

        self.add_input("I-List-X")
        self.add_input("I-List-Y")

        self.add_text_input_option("文件路径", default="trajectory_chart.html")
        self.add_text_input_option("标题", default="轴心轨迹图")
        self.add_integer_option("宽度 (px)", default=800, min_val=600, max_val=2000)
        self.add_integer_option("高度 (px)", default=800, min_val=600, max_val=2000)
        self.add_checkbox_option("显示网格", default=True)
        self.add_number_option("线条宽度", default=2.0, min_val=0.5, max_val=5.0)
        self.add_select_option("配色方案", items=["彩虹", "热力"], default="彩虹")

    async def on_compute(self, execution_id: Optional[str] = None):
        """执行计算"""
        try:
            data_x = self.get_interface("I-List-X")
            data_y = self.get_interface("I-List-Y")

            if not (data_x and data_y):
                self._logger.warning("输入数据不完整")
                return

            # 提取数据 - 支持多种格式
            if isinstance(data_x, dict) and "data" in data_x:
                x_data = (
                    data_x["data"]
                    if isinstance(data_x["data"], list)
                    else data_x["data"].get("y", [])
                )
            else:
                x_data = data_x if isinstance(data_x, list) else []

            if isinstance(data_y, dict) and "data" in data_y:
                y_data = (
                    data_y["data"]
                    if isinstance(data_y["data"], list)
                    else data_y["data"].get("y", [])
                )
            else:
                y_data = data_y if isinstance(data_y, list) else []

            if len(x_data) == 0 or len(y_data) == 0:
                self._logger.warning("数据为空")
                return

            if len(x_data) != len(y_data):
                self._logger.warning(
                    f"X和Y数据长度不匹配: {len(x_data)} != {len(y_data)}"
                )
                return

            # 获取配置
            file_path = self.get_option("文件路径")
            title = self.get_option("标题")
            width = self.get_option("宽度 (px)")
            height = self.get_option("高度 (px)")
            show_grid = self.get_option("显示网格")
            line_width = self.get_option("线条宽度")
            color_scheme = self.get_option("配色方案")

            # 生成时间索引（用于颜色映射）
            time_indices = list(range(len(x_data)))

            # 生成HTML
            html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        .container {{
            max-width: {width}px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        header {{
            background: #2563eb;
            color: white;
            padding: 20px;
            text-align: center;
        }}
        h1 {{
            margin: 0;
            font-weight: 500;
            font-size: 1.8em;
        }}
        .hint {{
            text-align: center;
            color: #64748b;
            font-size: 0.85em;
            margin: 8px 0 12px 0;
            padding: 6px 0;
            background: rgba(37, 99, 235, 0.05);
            border-radius: 6px;
        }}
        .chart-wrapper {{
            position: relative;
            height: {height}px;
            padding: 20px;
            cursor: default;
        }}
        .chart-wrapper:hover {{
            cursor: grab;
        }}
        .chart-wrapper:active {{
            cursor: grabbing;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header><h1>{title}</h1></header>
        <div class="hint">
            交互提示：滚轮缩放 · 左键拖拽平移 · 双击重置 · 颜色表示时间进程
        </div>
        <div class="chart-wrapper">
            <canvas id="chart"></canvas>
        </div>
    </div>

    <script>
        const xData = {json.dumps(x_data)};
        const yData = {json.dumps(y_data)};
        const timeIndices = {json.dumps(time_indices)};
        const totalPoints = {len(x_data)};

        // 生成颜色数组
        function generateColors(indices, scheme) {{
            const colors = [];
            for (let i = 0; i < indices.length; i++) {{
                const ratio = indices[i] / totalPoints;
                let r, g, b;
                
                if (scheme === '彩虹') {{
                    const hue = ratio * 360;
                    const color = hslToRgb(hue / 360, 0.7, 0.5);
                    r = color[0];
                    g = color[1];
                    b = color[2];
                }} else if (scheme === '热力') {{
                    r = Math.floor(255 * ratio);
                    g = Math.floor(255 * (1 - ratio) * 0.5);
                    b = Math.floor(255 * (1 - ratio));
                }}
                
                colors.push(`rgba(${{r}}, ${{g}}, ${{b}}, 0.8)`);
            }}
            return colors;
        }}

        // HSL转RGB
        function hslToRgb(h, s, l) {{
            let r, g, b;
            if (s === 0) {{
                r = g = b = l;
            }} else {{
                const hue2rgb = (p, q, t) => {{
                    if (t < 0) t += 1;
                    if (t > 1) t -= 1;
                    if (t < 1/6) return p + (q - p) * 6 * t;
                    if (t < 1/2) return q;
                    if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
                    return p;
                }};
                const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
                const p = 2 * l - q;
                r = hue2rgb(p, q, h + 1/3);
                g = hue2rgb(p, q, h);
                b = hue2rgb(p, q, h - 1/3);
            }}
            return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)];
        }}

        const colors = generateColors(timeIndices, '{color_scheme}');

        const ctx = document.getElementById('chart').getContext('2d');
        const chart = new Chart(ctx, {{
            type: 'line',
            data: {{
                datasets: [{{
                    label: '{title}',
                    data: xData.map((x, i) => ({{x: x, y: yData[i]}})),
                    borderColor: colors,
                    backgroundColor: colors,
                    borderWidth: {line_width},
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    tension: 0.1,
                    showLine: true
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                animation: {{
                    duration: 800
                }},
                interaction: {{
                    intersect: false,
                    mode: 'nearest'
                }},
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        cornerRadius: 8,
                        padding: 10,
                        callbacks: {{
                            label: function(context) {{
                                const index = context.dataIndex;
                                return [
                                    'X: ' + context.parsed.x.toFixed(2),
                                    'Y: ' + context.parsed.y.toFixed(2),
                                    '时间索引: ' + index
                                ];
                            }}
                        }}
                    }},
                    zoom: {{
                        pan: {{
                            enabled: true,
                            mode: 'xy',
                            modifierKey: null,
                            threshold: 1,
                            speed: 20
                        }},
                        zoom: {{
                            wheel: {{ enabled: true }},
                            pinch: {{ enabled: true }},
                            mode: 'xy'
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        type: 'linear',
                        position: 'bottom',
                        title: {{
                            display: true,
                            text: 'X方向振动 (μm)',
                            font: {{ size: 14 }}
                        }},
                        grid: {{
                            display: {str(show_grid).lower()},
                            color: 'rgba(0,0,0,0.05)'
                        }}
                    }},
                    y: {{
                        type: 'linear',
                        position: 'left',
                        title: {{
                            display: true,
                            text: 'Y方向振动 (μm)',
                            font: {{ size: 14 }}
                        }},
                        grid: {{
                            display: {str(show_grid).lower()},
                            color: 'rgba(0,0,0,0.05)'
                        }}
                    }}
                }}
            }}
        }});

        document.querySelector('canvas').addEventListener('dblclick', (e) => {{
            e.preventDefault();
            chart.resetZoom('none');
        }});
    </script>
</body>
</html>
"""

            # 使用通用文件写入方法
            def write_html(full_path, mode: str):
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                self._logger.info(f"轨迹图已生成: {full_path}")

            self._write_file(
                filename=file_path,
                write_func=write_html,
                execution_id=execution_id,
                description=f"{title}轨迹图",
                metadata={
                    "chart_type": "trajectory",
                    "title": title,
                    "width": width,
                    "height": height,
                },
            )

        except Exception as e:
            self._log_error(e, "轨迹图")


class OrderMapChartViewer(BaseBlock):
    """
    阶次瀑布图查看器

    功能：
    - 显示OrderMap三维数据（阶次-转速-幅值）
    - 使用热力图或3D曲面图
    - 支持交互式缩放和旋转
    """

    NAME = "OrderMapChartViewer"
    CATEGORY = "输出"

    def __init__(self):
        super().__init__()

        self.add_input("I-OrderMap")
        self.add_text_input_option("文件路径", default="order_map_chart.html")
        self.add_text_input_option("标题", default="Order Map Chart")
        self.add_integer_option("宽度 (px)", default=1200, min_val=800, max_val=2000)
        self.add_integer_option("高度 (px)", default=700, min_val=500, max_val=1200)
        self.add_select_option("显示模式", items=["热力图", "3D曲面"], default="热力图")
        self.add_checkbox_option("显示颜色条", default=True)
        self.add_checkbox_option("反转Y轴", default=False)

    async def on_compute(self, execution_id: Optional[str] = None):
        """生成阶次图"""
        try:
            i_data = self.get_interface("I-OrderMap")

            if not self._validate_input_data(i_data):
                return

            # 检查数据类型
            if i_data.get("type") != "order_map":
                self._logger.warning("输入数据不是OrderMap格式")
                return

            # 提取数据
            maps = i_data.get("data", [])
            if not maps or len(maps) == 0:
                self._logger.warning("OrderMap数据为空")
                return

            # 获取配置
            file_path = self.get_option("文件路径")
            title = self.get_option("标题")
            width = self.get_option("宽度 (px)")
            height = self.get_option("高度 (px)")
            display_mode = self.get_option("显示模式")
            show_colorbar = self.get_option("显示颜色条")
            reverse_y = self.get_option("反转Y轴")

            # 准备数据
            rpm_values = [frame["rpm"] for frame in maps]
            order_values = maps[0]["order"] if maps else []
            mag_values = [frame["mag"] for frame in maps]

            # 转换为numpy数组
            rpm_array = np.array(rpm_values)
            order_array = np.array(order_values)
            mag_array = np.array(mag_values)

            # 生成HTML
            html_content = self._generate_order_map_html(
                title,
                width,
                height,
                rpm_array.tolist(),
                order_array.tolist(),
                mag_array.tolist(),
                display_mode,
                show_colorbar,
                reverse_y,
            )

            # 使用通用文件写入方法
            def write_html(full_path, mode: str):
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                self._logger.info(f"阶次图已生成: {full_path}")

            self._write_file(
                filename=file_path,
                write_func=write_html,
                execution_id=execution_id,
                description=f"{title}阶次图",
                metadata={
                    "chart_type": "order_map",
                    "title": title,
                    "width": width,
                    "height": height,
                },
            )

        except Exception as e:
            self._log_error(e, "阶次图生成")
            raise

    def _generate_order_map_html(
        self,
        title,
        width,
        height,
        rpm_values,
        order_values,
        mag_values,
        display_mode,
        show_colorbar,
        reverse_y,
    ) -> str:
        """生成阶次图HTML"""

        rpm_json = json.dumps(rpm_values)
        order_json = json.dumps(order_values)
        mag_json = json.dumps(mag_values)

        y_axis_direction = "descending" if reverse_y else "ascending"

        if display_mode == "热力图":
            return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); margin: 0; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: {width}px; margin: 0 auto; background: white; border-radius: 16px;
                      box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }}
        header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
        h1 {{ margin: 0; font-weight: 500; font-size: 1.8em; }}
        .hint {{ 
            text-align: center; color: #64748b; font-size: 0.85em; 
            margin: 8px 0 12px 0; padding: 6px 0;
            background: rgba(37, 99, 235, 0.05); border-radius: 6px;
        }}
        #chart {{ width: 100%; height: {height}px; }}
    </style>
</head>
<body>
    <div class="container">
        <header><h1>{title}</h1></header>
        <div class="hint">
            交互提示：鼠标滚轮缩放 · 拖拽平移 · 悬停查看数值
        </div>
        <div id="chart"></div>
    </div>

    <script>
        const rpmValues = {rpm_json};
        const orderValues = {order_json};
        const magValues = {mag_json};

        const data = [{{
            z: magValues,
            x: orderValues,
            y: rpmValues,
            type: 'heatmap',
            colorscale: 'Viridis',
            colorbar: {{ show: {str(show_colorbar).lower()}, title: '幅值' }},
            showscale: {str(show_colorbar).lower()}
        }}];

        const layout = {{
            title: '{{title}}',
            xaxis: {{ title: '阶次 (Order)' }},
            yaxis: {{ 
                title: '转速 (RPM)',
                autorange: '{y_axis_direction}'
            }},
            margin: {{ t: 50, r: 50, b: 50, l: 60 }},
            hovermode: 'closest'
        }};

        const config = {{
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['lasso2d', 'select2d']
        }};

        Plotly.newPlot('chart', data, layout, config);
    </script>
</body>
</html>
"""
        else:  # 3D Surface
            return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); margin: 0; padding: 20px; min-height: 100vh; }}
        .container {{ max-width: {width}px; margin: 0 auto; background: white; border-radius: 16px;
                      box-shadow: 0 10px 30px rgba(0,0,0,0.1); overflow: hidden; }}
        header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
        h1 {{ margin: 0; font-weight: 500; font-size: 1.8em; }}
        .hint {{ 
            text-align: center; color: #64748b; font-size: 0.85em; 
            margin: 8px 0 12px 0; padding: 6px 0;
            background: rgba(37, 99, 235, 0.05); border-radius: 6px;
        }}
        #chart {{ width: 100%; height: {height}px; }}
    </style>
</head>
<body>
    <div class="container">
        <header><h1>{title}</h1></header>
        <div class="hint">
            交互提示：鼠标拖拽旋转 · 滚轮缩放 · 悬停查看数值
        </div>
        <div id="chart"></div>
    </div>

    <script>
        const rpmValues = {rpm_json};
        const orderValues = {order_json};
        const magValues = {mag_json};

        const data = [{{
            z: magValues,
            x: orderValues,
            y: rpmValues,
            type: 'surface',
            colorscale: 'Viridis',
            colorbar: {{ show: {str(show_colorbar).lower()}, title: '幅值' }},
            showscale: {str(show_colorbar).lower()},
            contours: {{
                z: {{
                    show: true,
                    usecolormap: true,
                    highlightcolor: "#42f462",
                    project: {{ z: true }}
                }}
            }}
        }}];

        const layout = {{
            title: '{{title}} - 3D视图',
            scene: {{
                xaxis: {{ title: '阶次 (Order)' }},
                yaxis: {{ title: '转速 (RPM)' }},
                zaxis: {{ title: '幅值' }},
                camera: {{
                    eye: {{ x: 1.5, y: 1.5, z: 1.5 }}
                }}
            }},
            margin: {{ t: 50, r: 50, b: 50, l: 60 }}
        }};

        const config = {{
            responsive: true,
            displayModeBar: true,
            displaylogo: false
        }};

        Plotly.newPlot('chart', data, layout, config);
    </script>
</body>
</html>
"""

