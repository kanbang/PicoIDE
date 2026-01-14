import math
import time
import numpy as np
import pandas as pd
import json
# import paho.mqtt.publish as mqtt_publish
from datetime import datetime
import scipy.signal as signal
from scipy.interpolate import interp1d

from flow.block import Block


# ==================== AdlinkBridge ====================

class AdlinkBridge:
    def __init__(self) -> None:
        # card param
        self.fSamplerate = 0
        self.AdRange = 0
        self.channels = []
        # card data
        self.ch_data = None
        # result data
        # 时域
        self.data_t = []
        # 频域
        self.data_p = []
        # x, y
        self.data_xy = []

    def set_fsamplerate(self, fSamplerate):
        self.fSamplerate = fSamplerate

    def set_adrange(self, AdRange):
        self.AdRange = AdRange

    def add_channel(self, channel):
        self.channels.append(channel)

    def set_channels_data(self, ch_data):
        self.ch_data = ch_data
    def get_channel_data(self, channel):
        if self.ch_data is None:
            # 高级模拟：1000 个点，采样率可配置（默认 10kHz）
            count = 1000
            fs = self.fSamplerate if self.fSamplerate > 0 else 10000  # 默认 10kHz
            t = np.linspace(0, count / fs, count, endpoint=False)

            # 基础参数（模拟一台有故障的电机，平均转速 3000 RPM = 50 Hz）
            base_freq = 50.0  # 基频 (转频)
            rpm_mean = base_freq * 60

            # 非匀速波动（模拟低频扭振或变速过程）
            speed_variation = 0.1 * np.sin(2 * np.pi * 1.0 * t)  # 1Hz 波动，幅度 10%
            instantaneous_rpm = rpm_mean * (1 + speed_variation)
            instantaneous_freq = instantaneous_rpm / 60

            # 扭振相位调制（额外相位噪声）
            torsional_phase = 0.05 * np.sin(2 * np.pi * 5 * t)  # 5Hz 扭振

            if channel in [0, 1, 2, 3]:  # 振动通道
                # 谐波 + 冲击 + 噪声 + 扭振调制
                y = (
                    1.0 * np.sin(2 * np.pi * instantaneous_freq * t + torsional_phase)  # 1阶
                    + 0.3 * np.sin(2 * np.pi * 2 * instantaneous_freq * t)               # 2阶
                    + 0.1 * np.sin(2 * np.pi * 5 * instantaneous_freq * t)               # 5阶
                    + 0.2 * np.random.randn(count)                                      # 白噪声
                )
                # 随机冲击（模拟轴承故障）
                impacts = np.zeros(count)
                impact_times = np.random.choice(count, size=8, replace=False)
                impacts[impact_times] = 3.0
                impacts = signal.lfilter(*signal.butter(4, 2000 / (fs / 2), 'high'), impacts)
                y += impacts

            elif channel == 4:  # 转速脉冲通道（非匀速）
                pulse_times = []
                current_angle = 0.0
                for i in range(count):
                    deg_per_sec = instantaneous_rpm[i] * 6  # RPM to deg/s
                    current_angle += deg_per_sec / fs
                    if current_angle >= 360:
                        pulse_times.append(t[i])
                        current_angle -= 360
                y = np.zeros(count)
                pulse_idx = [int(pt * fs) for pt in pulse_times if pt < t[-1]]
                y[pulse_idx] = 5.0  # 高电平脉冲

            elif channel == 5:  # 直接瞬时转速通道
                y = instantaneous_rpm

            else:
                y = np.zeros(count)

            x_data = t.tolist()
            y_data = y.tolist()

            return {"x": x_data, "y": y_data}

        return self.ch_data.get(channel)

    def add_data_t(self, data_t):
        self.data_t.append(data_t)

    def add_data_p(self, data_p):
        self.data_p.append(data_p)

    def add_data_xy(self, data_xy):
        self.data_xy.append(data_xy)

    def reset(self):
        self.init = False
        self.fSamplerate = 0
        self.AdRange = 0
        self.channels = []

    def get_card_param(self):
        return {"fSamplerate": self.fSamplerate, "channels": self.channels}

    def get_result_data(self):
        ret = {"t": self.data_t, "p": self.data_p, "xy": self.data_xy}
        self.data_t = []
        self.data_p = []
        self.data_xy = []
        return ret

    def init_card(self):
        if self.init:
            return
        self.init = True

adlink_bridge_instance = AdlinkBridge()

# ==================== 所有 Block（已设置 category） ====================

class ChannelBlock(Block):
    def __init__(self):
        super().__init__("Channel", category="Source")
        self.add_output("O-List-XY")
        self.add_checkbox_option("启用", default=True)
        self.add_select_option(
            "通道", items=[f"Channel {i}" for i in range(8)], default="Channel 0"
        )

    def on_compute(self):
        if not self.get_option("启用"):
            return
        channel_str = self.get_option("通道")
        channel_idx = int(channel_str.split(" ")[1])
        data = adlink_bridge_instance.get_channel_data(channel_idx)
        self.set_interface("O-List-XY", {"type": "channel", "data": data})



class NonUniformSpeedSimulatorBlock(Block):
    def __init__(self):
        super().__init__("NonUniformSpeedSimulator", category="Source")
        
        # 只保留最核心、常用的参数
        self.add_number_option("基本转频 (Hz)", default=2.0, min_val=0.1, max_val=50.0)
        self.add_number_option("转速波动幅度 (%)", default=30.0, min_val=0.0, max_val=100.0)
        self.add_number_option("波动频率 (Hz)", default=0.2, min_val=0.0, max_val=5.0)
        self.add_integer_option("每转脉冲数 PPR", default=1, min_val=1, max_val=60)
        self.add_number_option("整体信号幅度", default=1.0, min_val=0.1, max_val=10.0)
        self.add_number_option("噪声幅度", default=0.02, min_val=0.0, max_val=1.0)
        
        # 输出端口
        self.add_output("O-Pulse-XY")          # 转速脉冲信号（方波）
        self.add_output("O-Vibration-XY")      # 扭振信号（固定10/20/30阶）
        self.add_output("O-InstantRPM-XY")    # 瞬时转速曲线

    def on_compute(self):
        # 参数读取
        f0 = self.get_option("基本转频 (Hz)")
        mod_percent = self.get_option("转速波动幅度 (%)") / 100.0  # 转为小数
        f_mod = self.get_option("波动频率 (Hz)")
        ppr = self.get_option("每转脉冲数 PPR")
        scale = self.get_option("整体信号幅度")
        noise_amp = self.get_option("噪声幅度")
        
        # 固定参数
        t_start, t_end = 0.0, 10.0
        pulse_points = 5000      # 脉冲通道采样率
        vib_points = 20000       # 振动通道更高采样率
        
        # 固定阶次成分（经典10/20/30阶，相对幅值固定，整体缩放）
        orders = [10.0, 20.0, 30.0]
        rel_amps = [0.5, 0.3, 0.2]   # 相对幅值
        phases = [0.0, 0.5, 1.0]
        
        # === 生成脉冲通道 ===
        pulse_time = np.linspace(t_start, t_end, pulse_points)
        omega_t = 2 * np.pi * f0 * (1.0 + mod_percent * np.sin(2 * np.pi * f_mod * pulse_time))
        instant_rpm = omega_t / (2 * np.pi) * 60.0
        
        dtheta = (omega_t[:-1] + omega_t[1:]) / 2.0 * np.diff(pulse_time)
        theta = np.cumsum(dtheta)
        theta = np.insert(theta, 0, 0.0)
        
        angle_per_pulse = 2 * np.pi / ppr
        pulse_state = (np.floor(theta / angle_per_pulse) % 2).astype(float)
        pulse_state *= 5.0  # 方波电平
        
        # === 生成振动通道 ===
        torsional_time = np.linspace(t_start, t_end, vib_points)
        theta_interp = interp1d(pulse_time, theta, kind='cubic', fill_value='extrapolate')
        theta_t = theta_interp(torsional_time)
        
        torsional_value = np.zeros(len(torsional_time))
        for order, rel_amp, phase in zip(orders, rel_amps, phases):
            torsional_value += rel_amp * np.sin(order * theta_t + phase)
        torsional_value *= scale  # 整体幅度缩放
        torsional_value += noise_amp * np.random.randn(len(torsional_time))
        
        # === 输出 ===
        self.set_interface("O-Pulse-XY", {
            "type": "pulse",
            "data": {"x": pulse_time.tolist(), "y": pulse_state.tolist()}
        })
        
        self.set_interface("O-Vibration-XY", {
            "type": "vibration_nonuniform",
            "data": {"x": torsional_time.tolist(), "y": torsional_value.tolist()}
        })
        
        self.set_interface("O-InstantRPM-XY", {
            "type": "rpm_nonuniform",
            "data": {"x": pulse_time.tolist(), "y": instant_rpm.tolist()}
        })


class ReadCSVBlock(Block):
    def __init__(self):
        super().__init__("ReadCSV", category="Source")
        self.add_text_input_option("文件路径", default="data.csv")
        self.add_text_input_option("X列名 (可选)", default="")
        self.add_text_input_option("Y列名 (可选)", default="")
        self.add_checkbox_option("有表头", default=True)
        self.add_output("O-List-XY")

    def on_compute(self):
        file_path = self.get_option("文件路径")
        x_col = self.get_option("X列名 (可选)").strip() or None
        y_col = self.get_option("Y列名 (可选)").strip() or None
        header = 0 if self.get_option("有表头") else None

        try:
            df = pd.read_csv(file_path, header=header)
            if df.empty:
                return

            if x_col is None and y_col is None:
                if len(df.columns) >= 2:
                    x_data = df.iloc[:, 0].tolist()
                    y_data = df.iloc[:, 1].tolist()
                else:
                    return
            else:
                x_data = df[x_col].tolist() if x_col else list(range(len(df)))
                y_data = df[y_col].tolist() if y_col else []

            data = {"x": x_data, "y": y_data}
            self.set_interface("O-List-XY", {"type": "list2d", "data": data})
        except Exception as e:
            print(f"ReadCSVBlock 错误: {e}")


class ConstantBlock(Block):
    def __init__(self):
        super().__init__("Constant", category="Source")
        self.add_text_input_option("常量值", default="0.0")
        self.add_output("O-Value")

    def on_compute(self):
        try:
            value = float(self.get_option("常量值"))
        except:
            value = self.get_option("常量值")
        self.set_interface("O-Value", {"type": "constant", "data": value})

class SignalSplitterBlock(Block):
    def __init__(self):
        super().__init__("SignalSplitter", category="Conversion")
        self.add_input("I-List-XY")                   
        self.add_output("O-List-X")                 
        self.add_output("O-List-Y")

    def on_compute(self):
        data_packet = self.get_interface("I-List-XY")
        if not data_packet or "data" not in data_packet:
            # 输入无效时，输出空数据（避免下游阻塞）
            self.set_interface("O-List-X", {"type": "list1d", "data": []})
            self.set_interface("O-List-Y", {"type": "list1d", "data": []})
            return

        inner_data = data_packet["data"]

        # 确保始终有值（即使为空列表）
        x_data = inner_data.get("x", [])
        y_data = inner_data.get("y", [])
        self.set_interface("O-List-X", {"type": "list1d", "data": x_data})
        self.set_interface("O-List-Y", {"type": "list1d", "data": y_data})


class ToList2DBlock(Block):
    def __init__(self):
        super().__init__("ToList2D", category="Conversion")
        self.add_input("I-List-X")
        self.add_input("I-List-Y")
        self.add_output("O-List-XY")

    def on_compute(self):
        i_data_x = self.get_interface("I-List-X")
        i_data_y = self.get_interface("I-List-Y")
        if not (i_data_x and i_data_y):
            return
        self.set_interface(
            "O-List-XY",
            {"type": "list2d", "data": {"x": i_data_x["data"], "y": i_data_y["data"]}},
        )


class FilterBlock(Block):
    def __init__(self):
        super().__init__("Filter", category="Processing")
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")
        self.add_select_option("类型", items=["lowpass", "highpass", "bandpass", "bandstop"], default="lowpass")
        self.add_text_input_option("截止频率 (Hz, 用逗号分隔带通)", default="1000")
        self.add_integer_option("阶数", default=4, min_val=1, max_val=12)

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data:
            return
        data = i_data["data"]
        x = np.array(data["x"])
        y = np.array(data["y"])
        fs = 1 / np.mean(np.diff(x)) if len(x) > 1 else 10000

        freqs = [float(f.strip()) for f in self.get_option("截止频率 (Hz, 用逗号分隔带通)").split(",")]
        order = self.get_option("阶数")
        if len(freqs) == 1:
            freqs = freqs[0]
        b, a = signal.butter(order, [f / (fs / 2) for f in (freqs if isinstance(freqs, list) else [freqs])], btype=self.get_option("类型"))
        y_filtered = signal.filtfilt(b, a, y)

        self.set_interface("O-List-XY", {"type": "filtered", "data": {"x": x.tolist(), "y": y_filtered.tolist()}})


class EnvelopeBlock(Block):
    def __init__(self):
        super().__init__("Envelope", category="Processing")
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data:
            return
        data = i_data["data"]
        x = np.array(data["x"])
        y = np.array(data["y"])
        analytic = signal.hilbert(y)
        envelope = np.abs(analytic)
        self.set_interface("O-List-XY", {"type": "envelope", "data": {"x": x.tolist(), "y": envelope.tolist()}})


class FourierTransformBlock(Block):
    def __init__(self):
        super().__init__("FourierTransform", category="Transform")
        self.add_input("I-List-V")
        self.add_output("O-List-XY")
        self.add_checkbox_option("绝对值", default=True)

    def _do_fft(self, signal, seconds=1.0):
        N = len(signal)
        if N == 0:
            return {"x": [], "y": []}
        fs = N / seconds
        fft_result = np.fft.fft(signal)
        magnitude = np.abs(fft_result) / N * 2
        magnitude = magnitude[: N // 2]
        freqs = np.fft.fftfreq(N, 1 / fs)[: N // 2]
        return {"x": freqs.tolist(), "y": magnitude.tolist()}

    def on_compute(self):
        i_data = self.get_interface("I-List-V")
        if not i_data:
            return
        fdata = self._do_fft(i_data["data"])
        self.set_interface("O-List-XY", {"type": "fourier", "data": fdata})


class OrderFFTBlock(Block):
    def __init__(self):
        super().__init__("OrderFFT", category="Transform")
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")
        self.add_checkbox_option("绝对值", default=True)

    def _do_order_fft(self, signal):
        N = len(signal)
        if N == 0:
            return {"x": [], "y": []}
        fft_result = np.fft.fft(signal)
        magnitude = np.abs(fft_result) / N * 2
        magnitude = magnitude[:N//2]
        orders = np.linspace(0, N/2, N//2)
        return {"x": orders.tolist(), "y": magnitude.tolist()}

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data:
            return
        signal_y = np.array(i_data["data"]["y"])
        fdata = self._do_order_fft(signal_y)
        self.set_interface("O-List-XY", {"type": "order", "data": fdata})


class PulseToRPMBlock(Block):
    def __init__(self):
        super().__init__("PulseToRPM", category="Order Analysis")
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")
        self.add_number_option("脉冲电平阈值", default=2.0, min_val=0.0)

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data:
            return
        data = i_data["data"]
        x = np.array(data["x"])
        y = np.array(data["y"])
        threshold = self.get_option("脉冲电平阈值")
        pulse_times = x[y > threshold]
        if len(pulse_times) < 2:
            return
        intervals = np.diff(pulse_times)
        rpm_per_interval = 60.0 / intervals
        interp_func = interp1d(pulse_times[1:], rpm_per_interval, kind='linear',
                               bounds_error=False, fill_value="extrapolate")
        rpm_out = interp_func(x)
        self.set_interface("O-List-XY", {"type": "rpm", "data": {"x": x.tolist(), "y": rpm_out.tolist()}})


class AngularResamplingBlock(Block):
    def __init__(self):
        super().__init__("AngularResampling", category="Order Analysis")
        self.add_input("I-Vibration-XY")
        self.add_input("I-RPM-XY")
        self.add_output("O-List-XY")
        self.add_integer_option("每转采样点数", default=128, min_val=16, max_val=1024)

    def on_compute(self):
        vib_data = self.get_interface("I-Vibration-XY")
        rpm_data = self.get_interface("I-RPM-XY")
        if not (vib_data and rpm_data):
            return
        vib = vib_data["data"]
        rpm = rpm_data["data"]
        t = np.array(vib["x"])
        vib_y = np.array(vib["y"])
        rpm_y = np.array(rpm["y"])
        dt = np.diff(t, prepend=t[0])
        angular_speed_deg_s = rpm_y * 6
        cumulative_angle = np.cumsum(angular_speed_deg_s * dt)
        points_per_rev = self.get_option("每转采样点数")
        total_revs = cumulative_angle[-1] / 360
        target_angles = np.linspace(0, total_revs * 360, int(total_revs * points_per_rev), endpoint=False)
        interp_func = interp1d(cumulative_angle, vib_y, kind='linear', bounds_error=False, fill_value=0)
        resampled_y = interp_func(target_angles)
        self.set_interface("O-List-XY", {"type": "angular", "data": {"x": target_angles.tolist(), "y": resampled_y.tolist()}})


class StatisticsBlock(Block):
    def __init__(self):
        super().__init__("Statistics", category="Analysis")
        self.add_input("I-List-XY")
        self.add_output("O-Dict")

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data or "data" not in i_data:
            return
        y = np.array(i_data["data"].get("y", []))
        if len(y) == 0:
            return
        stats = {
            "count": len(y),
            "mean": float(np.mean(y)),
            "std": float(np.std(y)),
            "min": float(np.min(y)),
            "max": float(np.max(y)),
            "timestamp": datetime.now().isoformat()
        }
        self.set_interface("O-Dict", {"type": "stats", "data": stats})


class ResultBlock(Block):
    def __init__(self):
        super().__init__("Result", category="Sink")
        self.add_input("List-XY")
        self.add_select_option("类型", items=["时域", "频域", "FREE"], default="时域")
        self.add_text_input_option("名称", default="New Plot")

    def on_compute(self):
        i_data = self.get_interface("List-XY")
        if not i_data:
            return
        t = self.get_option("类型")
        name = self.get_option("名称")
        payload = {"name": name, "value": i_data["data"]}
        if t == "时域":
            adlink_bridge_instance.add_data_t(payload)
        elif t == "频域":
            adlink_bridge_instance.add_data_p(payload)
        else:
            adlink_bridge_instance.add_data_xy(payload)


class WriteCSVBlock(Block):
    def __init__(self):
        super().__init__("WriteCSV", category="Sink")
        self.add_input("I-List-XY")
        self.add_text_input_option("文件路径", default="output.csv")
        self.add_checkbox_option("追加模式", default=False)
        self.add_checkbox_option("包含表头", default=True)

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data or "data" not in i_data:
            return
        file_path = self.get_option("文件路径")
        mode = 'a' if self.get_option("追加模式") else 'w'
        header = self.get_option("包含表头") and mode == 'w'
        data = i_data["data"]
        x = data.get("x", [])
        y = data.get("y", [])
        if not x:
            x = list(range(len(y)))
        df = pd.DataFrame({"x": x, "y": y})
        try:
            df.to_csv(file_path, mode=mode, header=header, index=False)
        except Exception as e:
            print(f"WriteCSVBlock 错误: {e}")
class GenerateHTMLChartBlock(Block):
    def __init__(self):
        super().__init__("GenerateHTMLChart", category="Sink")
        self.add_input("I-List-XY")
        self.add_text_input_option("文件路径", default="chart.html")
        self.add_text_input_option("图表标题", default="DAQ Chart")
        self.add_select_option("图表类型", items=["line", "scatter", "bar"], default="line")
        
        # 尺寸配置（保持之前优化）
        self.add_integer_option("图表宽度 (px)", default=1200, min_val=600, max_val=2000)
        self.add_integer_option("图表高度 (px)", default=700, min_val=400, max_val=1200)
        
        # 新增交互选项
        self.add_checkbox_option("启用X轴缩放/拖动", default=True)
        self.add_checkbox_option("显示重置缩放按钮", default=True)
        self.add_checkbox_option("显示网格线", default=True)
        self.add_checkbox_option("显示图例", default=True)

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data or "data" not in i_data:
            return

        data = i_data["data"]
        x = json.dumps(data.get("x", []))
        y = json.dumps(data.get("y", []))

        file_path = self.get_option("文件路径")
        title = self.get_option("图表标题")
        chart_type = self.get_option("图表类型")
        
        width = self.get_option("图表宽度 (px)")
        height = self.get_option("图表高度 (px)")
        enable_zoom = self.get_option("启用X轴缩放/拖动")
        show_reset_btn = self.get_option("显示重置缩放按钮")
        show_grid = self.get_option("显示网格线")
        show_legend = self.get_option("显示图例")

        # 自动判断X轴标签
        typ = i_data.get("type", "")
        x_label = ("Time (s)" if typ in ["channel", "filtered", "envelope"] else
                   "Frequency (Hz)" if typ == "fourier" else
                   "Order" if typ == "order" else "X")

        # Zoom插件配置字符串（仅在启用时注入）
        zoom_plugin_script = ""
        zoom_options = ""
        if enable_zoom:
            zoom_plugin_script = '<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>'
            zoom_options = """
                zoom: {
                    wheel: {
                        enabled: true,
                    },
                    drag: {
                        enabled: true,
                        backgroundColor: 'rgba(75,192,192,0.2)',
                        borderColor: 'rgb(75,192,192)',
                        borderWidth: 1
                    },
                    mode: 'x',
                },
                pan: {
                    enabled: true,
                    mode: 'x',
                },
            """

        # 重置按钮HTML（仅在启用且用户选择时显示）
        reset_btn_html = ""
        if enable_zoom and show_reset_btn:
            reset_btn_html = '''
                <div style="text-align:center; margin:15px 0;">
                    <button onclick="myChart.resetZoom()" style="padding:8px 16px; font-size:14px; cursor:pointer;">
                        重置缩放
                    </button>
                </div>
            '''

        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    {zoom_plugin_script}
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f9f9f9;
        }}
        .chart-container {{
            max-width: {width}px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        canvas {{
            width: 100% !important;
            height: {height}px !important;
        }}
        h2 {{
            text-align: center;
            color: #333;
        }}
    </style>
</head>
<body>
    <h2>{title}</h2>
    {reset_btn_html}
    <div class="chart-container">
        <canvas id="myChart"></canvas>
    </div>
    <script>
        const ctx = document.getElementById('myChart').getContext('2d');
        const myChart = new Chart(ctx, {{
            type: '{chart_type}',
            data: {{
                labels: {x},
                datasets: [{{
                    label: '{title}',
                    data: {y},
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.2,
                    fill: false,
                    pointRadius: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        display: {str(show_legend).lower()}
                    }},
                    {zoom_options}
                }},
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: '{x_label}',
                            font: {{ size: 14 }}
                        }},
                        grid: {{
                            display: {str(show_grid).lower()}
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: 'Amplitude',
                            font: {{ size: 14 }}
                        }},
                        grid: {{
                            display: {str(show_grid).lower()}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
        """

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML图表已保存: {file_path} (尺寸: {width}x{height}px, X轴缩放: {'启用' if enable_zoom else '禁用'})")
        except Exception as e:
            print(f"GenerateHTMLChartBlock 错误: {e}")

class MQTTPublishBlock(Block):
    def __init__(self):
        super().__init__("MQTTPublish", category="Communication")
        self.add_input("I-Any")
        self.add_text_input_option("Broker地址", default="broker.hivemq.com")
        self.add_text_input_option("端口", default="1883")
        self.add_text_input_option("主题", default="daq/data")
        self.add_text_input_option("用户名 (可选)", default="")
        self.add_text_input_option("密码 (可选)", default="")

    def on_compute(self):
        i_data = self.get_interface("I-Any")
        if i_data is None:
            return
        broker = self.get_option("Broker地址")
        port = int(self.get_option("端口"))
        topic = self.get_option("主题")
        username = self.get_option("用户名 (可选)") or None
        password = self.get_option("密码 (可选)") or None
        auth = {'username': username, 'password': password} if username else None
        try:
            payload = json.dumps(i_data)
            # mqtt_publish.single(topic, payload=payload, hostname=broker, port=port, auth=auth)
        except Exception as e:
            print(f"MQTTPublishBlock 错误: {e}")


class LoggerBlock(Block):
    def __init__(self):
        super().__init__("Logger", category="Debug")
        self.add_input("I-Any")
        self.add_text_input_option("前缀", default="LOG:")

    def on_compute(self):
        data = self.get_interface("I-Any")
        prefix = self.get_option("前缀")
        print(f"{prefix} {data}")


# ==================== 示例实例列表（用于注册或测试） ====================
daq_blocks = [
    ChannelBlock(),
    NonUniformSpeedSimulatorBlock(),
    ReadCSVBlock(),
    ConstantBlock(),
    SignalSplitterBlock(),
    ToList2DBlock(),
    FilterBlock(),
    EnvelopeBlock(),
    FourierTransformBlock(),
    OrderFFTBlock(),
    PulseToRPMBlock(),
    AngularResamplingBlock(),
    StatisticsBlock(),
    ResultBlock(),
    WriteCSVBlock(),
    GenerateHTMLChartBlock(),
    MQTTPublishBlock(),
    LoggerBlock(),
]