import math
import time
import numpy as np
import pandas as pd
import json
from datetime import datetime
import scipy.signal as signal
from scipy.interpolate import interp1d

from flow.block import Block


# ==================== AdlinkBridge ====================
# AdlinkBridge：模拟或真实采集卡的数据桥接类
# 主要功能：管理通道参数、模拟生成振动/脉冲数据、收集结果数据供前端显示
class AdlinkBridge:
    def __init__(self) -> None:
        # 采集卡参数
        self.fSamplerate = 0      # 采样率
        self.AdRange = 0          # 量程（未使用）
        self.channels = []        # 已启用通道列表
        # 真实数据（若接入真实采集卡）
        self.ch_data = None
        # 结果数据（供前端绘图）
        self.data_t = []          # 时域数据
        self.data_p = []          # 频域数据
        self.data_xy = []         # 其他（如阶次域）

    def set_fsamplerate(self, fSamplerate):
        """设置采样率"""
        self.fSamplerate = fSamplerate

    def set_adrange(self, AdRange):
        """设置量程（备用）"""
        self.AdRange = AdRange

    def add_channel(self, channel):
        """添加启用通道"""
        self.channels.append(channel)

    def set_channels_data(self, ch_data):
        """接入真实采集数据（字典形式）"""
        self.ch_data = ch_data

    def get_channel_data(self, channel):
        """
        获取指定通道数据
        若无真实数据，则返回模拟数据（用于调试/演示）
        """
        if self.ch_data is None:
            # 模拟参数
            count = 1000
            fs = self.fSamplerate if self.fSamplerate > 0 else 10000
            t = np.linspace(0, count / fs, count, endpoint=False)

            # 基础转速：3000 RPM ≈ 50 Hz
            base_freq = 50.0
            rpm_mean = base_freq * 60

            # 轻微非匀速波动（1Hz，10%幅度）
            speed_variation = 0.1 * np.sin(2 * np.pi * 1.0 * t)
            instantaneous_rpm = rpm_mean * (1 + speed_variation)
            instantaneous_freq = instantaneous_rpm / 60

            # 扭振相位调制
            torsional_phase = 0.05 * np.sin(2 * np.pi * 5 * t)

            if channel in [0, 1, 2, 3]:  # 振动通道
                y = (
                    1.0 * np.sin(2 * np.pi * instantaneous_freq * t + torsional_phase)  # 1阶
                    + 0.3 * np.sin(2 * np.pi * 2 * instantaneous_freq * t)               # 2阶
                    + 0.1 * np.sin(2 * np.pi * 5 * instantaneous_freq * t)               # 5阶
                    + 0.2 * np.random.randn(count)                                      # 白噪声
                )
                # 模拟轴承故障冲击
                impacts = np.zeros(count)
                impact_times = np.random.choice(count, size=8, replace=False)
                impacts[impact_times] = 3.0
                impacts = signal.lfilter(*signal.butter(4, 2000 / (fs / 2), 'high'), impacts)
                y += impacts

            elif channel == 4:  # 转速脉冲通道
                pulse_times = []
                current_angle = 0.0
                for i in range(count):
                    deg_per_sec = instantaneous_rpm[i] * 6
                    current_angle += deg_per_sec / fs
                    if current_angle >= 360:
                        pulse_times.append(t[i])
                        current_angle -= 360
                y = np.zeros(count)
                pulse_idx = [int(pt * fs) for pt in pulse_times if pt < t[-1]]
                y[pulse_idx] = 5.0

            elif channel == 5:  # 瞬时转速通道
                y = instantaneous_rpm

            else:
                y = np.zeros(count)

            return {"x": t.tolist(), "y": y.tolist()}

        return self.ch_data.get(channel)

    def add_data_t(self, data_t):
        """收集时域结果"""
        self.data_t.append(data_t)

    def add_data_p(self, data_p):
        """收集频域结果"""
        self.data_p.append(data_p)

    def add_data_xy(self, data_xy):
        """收集其他结果（如阶次域）"""
        self.data_xy.append(data_xy)

    def reset(self):
        """重置状态"""
        self.init = False
        self.fSamplerate = 0
        self.AdRange = 0
        self.channels = []

    def get_card_param(self):
        """获取采集参数"""
        return {"fSamplerate": self.fSamplerate, "channels": self.channels}

    def get_result_data(self):
        """获取并清空结果数据"""
        ret = {"t": self.data_t, "p": self.data_p, "xy": self.data_xy}
        self.data_t = []
        self.data_p = []
        self.data_xy = []
        return ret

    def init_card(self):
        """初始化采集卡（模拟）"""
        if self.init:
            return
        self.init = True

adlink_bridge_instance = AdlinkBridge()

# ==================== 所有 Block（类名已优化，添加详细注释） ====================

class ChannelSource(Block):
    """从模拟采集卡获取通道数据"""
    def __init__(self):
        super().__init__("ChannelSource", category="Source")
        self.add_output("O-List-XY")
        self.add_checkbox_option("启用", default=True)
        self.add_select_option("通道", items=[f"Channel {i}" for i in range(8)], default="Channel 0")

    def on_compute(self):
        if not self.get_option("启用"):
            return
        channel_idx = int(self.get_option("通道").split(" ")[1])
        data = adlink_bridge_instance.get_channel_data(channel_idx)
        self.set_interface("O-List-XY", {"type": "channel", "data": data})


class TurbineSimulator(Block):
    """汽轮机振动模拟器（核电典型工况：3000RPM，高稳定性）"""
    def __init__(self):
        super().__init__("TurbineSimulator", category="Source")
        self.add_number_option("额定转速 (RPM)", default=3000.0, min_val=0.0, max_val=4500.0)
        self.add_number_option("转速稳定性 (%)", default=99.5, min_val=80.0, max_val=100.0)
        self.add_integer_option("键相脉冲 PPR", default=1, min_val=1, max_val=120)
        self.add_number_option("振动烈度 (μm)", default=50.0, min_val=0.0, max_val=500.0)

        self.add_output("O-Pulse-XY")
        self.add_output("O-Vibration-XY")
        self.add_output("O-InstantRPM-XY")

    def on_compute(self):
        # 参数转换
        rpm_target = self.get_option("额定转速 (RPM)")
        f0 = rpm_target / 60.0
        stability = self.get_option("转速稳定性 (%)")
        mod_depth = (100.0 - stability) / 100.0
        ppr = self.get_option("键相脉冲 PPR")
        scale = self.get_option("振动烈度 (μm)")

        # 仿真时域（10秒数据）
        t_start, t_end = 0.0, 10.0
        pulse_pts = 5000
        vib_pts = 20000
        f_mod = 0.1  # 慢速调节波动

        # 脉冲通道：生成键相脉冲 + 瞬时转速
        t_pulse = np.linspace(t_start, t_end, pulse_pts)
        omega_t_pulse = 2 * np.pi * f0 * (1.0 + mod_depth * np.sin(2 * np.pi * f_mod * t_pulse))
        instant_rpm = (omega_t_pulse / (2 * np.pi)) * 60.0

        dt_pulse = np.diff(t_pulse, prepend=t_pulse[0])
        theta_pulse = np.cumsum(omega_t_pulse * dt_pulse)

        angle_per_pulse = 2 * np.pi / ppr
        pulse_signal = (np.floor(theta_pulse / angle_per_pulse) % 2).astype(float) * 5.0

        # 振动通道：基于角度合成典型阶次（1x, 2x, 7x）
        t_vib = np.linspace(t_start, t_end, vib_pts)
        theta_interp = interp1d(t_pulse, theta_pulse, kind='cubic', fill_value='extrapolate')
        theta_t_vib = theta_interp(t_vib)

        vibration = (
            1.0 * np.sin(1.0 * theta_t_vib) +
            0.4 * np.sin(2.0 * theta_t_vib + 0.8) +
            0.1 * np.sin(7.0 * theta_t_vib + 1.2)
        )
        noise = 0.05 * np.random.randn(len(t_vib))
        vibration = (vibration + noise) * scale

        # 输出
        self.set_interface("O-Pulse-XY", {"type": "pulse", "data": {"x": t_pulse.tolist(), "y": pulse_signal.tolist()}})
        self.set_interface("O-Vibration-XY", {"type": "channel", "data": {"x": t_vib.tolist(), "y": vibration.tolist()}})
        self.set_interface("O-InstantRPM-XY", {"type": "rpm", "data": {"x": t_pulse.tolist(), "y": instant_rpm.tolist()}})


class CSVReader(Block):
    """从CSV文件读取XY数据"""
    def __init__(self):
        super().__init__("CSVReader", category="Source")
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
            print(f"CSVReader 错误: {e}")


class ConstantSource(Block):
    """输出常量值（用于测试或参数注入）"""
    def __init__(self):
        super().__init__("ConstantSource", category="Source")
        self.add_text_input_option("常量值", default="0.0")
        self.add_output("O-Value")

    def on_compute(self):
        try:
            value = float(self.get_option("常量值"))
        except:
            value = self.get_option("常量值")
        self.set_interface("O-Value", {"type": "constant", "data": value})


class XYSplitter(Block):
    """将XY信号拆分为独立的X和Y向量"""
    def __init__(self):
        super().__init__("XYSplitter", category="Conversion")
        self.add_input("I-List-XY")
        self.add_output("O-List-X")
        self.add_output("O-List-Y")

    def on_compute(self):
        data_packet = self.get_interface("I-List-XY")
        if not data_packet or "data" not in data_packet:
            self.set_interface("O-List-X", {"type": "list1d", "data": []})
            self.set_interface("O-List-Y", {"type": "list1d", "data": []})
            return

        inner_data = data_packet["data"]
        x_data = inner_data.get("x", [])
        y_data = inner_data.get("y", [])
        self.set_interface("O-List-X", {"type": "list1d", "data": x_data})
        self.set_interface("O-List-Y", {"type": "list1d", "data": y_data})


class XYMerger(Block):
    """将独立的X和Y向量合并为XY信号"""
    def __init__(self):
        super().__init__("XYMerger", category="Conversion")
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


class SignalFilter(Block):
    """数字滤波器（Butterworth）"""
    def __init__(self):
        super().__init__("SignalFilter", category="Processing")
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


class EnvelopeDetector(Block):
    """希尔伯特包络解调（轴承故障诊断常用）"""
    def __init__(self):
        super().__init__("EnvelopeDetector", category="Processing")
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


class FFT(Block):
    """快速傅里叶变换（单边幅度谱）"""
    def __init__(self):
        super().__init__("FFT", category="Transform")
        self.add_input("I-List-V")
        self.add_output("O-List-XY")

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


class OrderFFT(Block):
    """阶次谱计算（角域信号的FFT）"""
    def __init__(self):
        super().__init__("OrderFFT", category="Transform")
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")

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


class TachoToRPM(Block):
    """从键相脉冲提取瞬时转速曲线"""
    def __init__(self):
        super().__init__("TachoToRPM", category="Order Analysis")
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")
        self.add_number_option("脉冲阈值", default=2.0, min_val=0.0)

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data:
            return
        data = i_data["data"]
        x = np.array(data["x"])
        y = np.array(data["y"])
        threshold = self.get_option("脉冲阈值")
        pulse_times = x[y > threshold]
        if len(pulse_times) < 2:
            return
        intervals = np.diff(pulse_times)
        rpm_per_interval = 60.0 / intervals
        interp_func = interp1d(pulse_times[1:], rpm_per_interval, kind='linear',
                               bounds_error=False, fill_value="extrapolate")
        rpm_out = interp_func(x)
        self.set_interface("O-List-XY", {"type": "rpm", "data": {"x": x.tolist(), "y": rpm_out.tolist()}})


class AngularResampler(Block):
    """角域重采样（消除转速波动影响）"""
    def __init__(self):
        super().__init__("AngularResampler", category="Order Analysis")
        self.add_input("I-Vibration-XY")
        self.add_input("I-RPM-XY")
        self.add_output("O-List-XY")
        self.add_integer_option("每转采样点数", default=128, min_val=16, max_val=1024)

    def on_compute(self):
        vib_data = self.get_interface("I-Vibration-XY")
        rpm_data = self.get_interface("I-RPM-XY")
        if not (vib_data and rpm_data):
            return

        vib_x = np.array(vib_data["data"]["x"])
        vib_y = np.array(vib_data["data"]["y"])
        rpm_x = np.array(rpm_data["data"]["x"])
        rpm_y = np.array(rpm_data["data"]["y"])

        # 将转速插值到振动时间轴（高采样率）
        rpm_interp_func = interp1d(rpm_x, rpm_y, kind='linear', bounds_error=False, fill_value="extrapolate")
        aligned_rpm_y = rpm_interp_func(vib_x)

        # 累计角度计算
        dt = np.diff(vib_x, prepend=vib_x[0])
        angular_speed_deg_s = aligned_rpm_y * 6
        cumulative_angle = np.cumsum(angular_speed_deg_s * dt)

        # 等角度重采样
        points_per_rev = self.get_option("每转采样点数")
        total_revs = cumulative_angle[-1] / 360
        if total_revs <= 0:
            return

        target_angles = np.linspace(0, total_revs * 360, int(total_revs * points_per_rev), endpoint=False)
        interp_func = interp1d(cumulative_angle, vib_y, kind='linear', bounds_error=False, fill_value=0)
        resampled_y = interp_func(target_angles)

        self.set_interface("O-List-XY", {
            "type": "angular",
            "data": {"x": target_angles.tolist(), "y": resampled_y.tolist()}
        })


class Stats(Block):
    """基本统计量计算"""
    def __init__(self):
        super().__init__("Stats", category="Analysis")
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


class ResultSink(Block):
    """结果收集器（将数据送入AdlinkBridge供前端显示）"""
    def __init__(self):
        super().__init__("ResultSink", category="Sink")
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


class CSVSink(Block):
    """将数据保存为CSV文件"""
    def __init__(self):
        super().__init__("CSVSink", category="Sink")
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
            print(f"CSVSink 错误: {e}")

# ==================== 新增专用图表查看器类（继承结构 + 数据类型区分优化） ====================

class BaseChartViewer(Block):
    """图表查看器基类（共享选项和生成逻辑，根据类型自动适配数据）"""
    def __init__(self, name: str, category: str = "Sink", default_type: str = "line"):
        super().__init__(name, category=category)
        self.add_input("I-List-XY")
        self.add_text_input_option("文件路径", default=f"{name.lower().replace('viewer', '')}_chart.html")
        self.add_text_input_option("标题", default=f"{name.replace('Viewer', '')} Chart")
        self.add_integer_option("宽度 (px)", default=1200, min_val=800, max_val=2000)
        self.add_integer_option("高度 (px)", default=700, min_val=500, max_val=1200)
        self.add_checkbox_option("显示网格", default=True)
        self.add_checkbox_option("显示图例", default=True)
        self.add_checkbox_option("启用滚轮缩放", default=True)
        self.add_checkbox_option("启用拖拽平移", default=True)
        
        self.chart_type = default_type

    def _generate_chart(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data or "data" not in i_data:
            print(f"[{self.name}] 警告: 无输入数据，跳过生成")
            return

        raw_data = i_data["data"]
        x_raw = raw_data.get("x", [])
        y_raw = raw_data.get("y", [])

        if len(y_raw) == 0:
            print(f"[{self.name}] 警告: Y数据为空，无法生成图表")
            return

        if self.chart_type == 'bar':
            if len(x_raw) == 0 or len(x_raw) != len(y_raw):
                print(f"[{self.name}] 提示: Bar图缺少有效X轴标签，自动生成索引作为类别")
                x_data = list(range(len(y_raw)))
            else:
                x_data = x_raw
            y_data = y_raw
            border_color = '#3b82f6'
            background_color = 'rgba(59, 130, 246, 0.7)'
            tension = 0
            point_radius = 0

        elif self.chart_type == 'scatter':
            if len(x_raw) == 0 or len(x_raw) != len(y_raw):
                print(f"[{self.name}] 错误: Scatter图需要完整的X/Y坐标且长度一致，当前数据不适合")
                return
            x_data = x_raw
            y_data = y_raw
            border_color = 'rgba(59, 130, 246, 0.4)'
            background_color = '#3b82f6'
            tension = 0
            point_radius = 5

        else:  # line
            if len(x_raw) == 0 or len(x_raw) != len(y_raw):
                print(f"[{self.name}] 提示: Line图缺少X轴，自动生成等间隔索引")
                x_data = list(range(len(y_raw)))
            else:
                x_data = x_raw
            y_data = y_raw
            border_color = '#3b82f6'
            background_color = 'rgba(59, 130, 246, 0.05)'
            tension = 0.15
            point_radius = 1.5

        x_json = json.dumps(x_data)
        y_json = json.dumps(y_data)

        file_path = self.get_option("文件路径")
        title = self.get_option("标题")
        width = self.get_option("宽度 (px)")
        height = self.get_option("高度 (px)")
        show_grid = self.get_option("显示网格")
        show_legend = self.get_option("显示图例")
        enable_wheel = self.get_option("启用滚轮缩放")
        enable_drag = self.get_option("启用拖拽平移")

        typ = i_data.get("type", "")
        x_label = ("Time (s)" if typ in ["channel", "filtered", "envelope"] else
                   "Frequency (Hz)" if typ == "fourier" else
                   "Order" if typ == "order" else "X")

        html_content = f"""
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
                    legend: {{ display: {str(show_legend).lower()} }},
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

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"[{self.name}] 图表已生成: {file_path}")
        except Exception as e:
            print(f"[{self.name}] 生成失败: {e}")


class LineChartViewer(BaseChartViewer):
    """交互式折线图查看器（推荐完整XY时序数据，如波形/频谱/阶次谱）"""
    def __init__(self):
        super().__init__("LineChartViewer", default_type="line")

    def on_compute(self):
        self._generate_chart()


class BarChartViewer(BaseChartViewer):
    """交互式柱状图查看器（推荐Y值序列，X可选作为类别标签，适合离散谱显示）"""
    def __init__(self):
        super().__init__("BarChartViewer", default_type="bar")

    def on_compute(self):
        self._generate_chart()


class ScatterChartViewer(BaseChartViewer):
    """交互式散点图查看器（严格要求完整XY坐标点，适合轨迹图/相位图）"""
    def __init__(self):
        super().__init__("ScatterChartViewer", default_type="scatter")

    def on_compute(self):
        self._generate_chart()
class MQTTPublisher(Block):
    """MQTT数据发布（当前为模拟打印）"""
    def __init__(self):
        super().__init__("MQTTPublisher", category="Communication")
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
            print("MQTT 已模拟发布:", payload[:200])
        except Exception as e:
            print(f"MQTT 错误: {e}")


class Logger(Block):
    """控制台日志输出（调试用）"""
    def __init__(self):
        super().__init__("Logger", category="Debug")
        self.add_input("I-Any")
        self.add_text_input_option("前缀", default="LOG:")

    def on_compute(self):
        data = self.get_interface("I-Any")
        prefix = self.get_option("前缀")
        print(f"{prefix} {data}")


# ==================== 注册列表 ====================
daq_blocks = [
    ChannelSource(),
    TurbineSimulator(),
    CSVReader(),
    ConstantSource(),
    XYSplitter(),
    XYMerger(),
    SignalFilter(),
    EnvelopeDetector(),
    FFT(),
    OrderFFT(),
    TachoToRPM(),
    AngularResampler(),
    Stats(),
    ResultSink(),
    CSVSink(),
    LineChartViewer(),
    BarChartViewer(),
    ScatterChartViewer(),
    MQTTPublisher(),
    Logger(),
]