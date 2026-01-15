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
    """
    核电汽轮机高精度模拟器

    物理层级：
    - phase(t)        ：真实角位移（核心）
    - omega(t)        ：瞬时角速度（真值）
    - Tacho Pulse     ：可测转速输入
    - Radial Vib      ：径向振动（1X / 2X / BPF）
    - Torsional Vib   ：扭振（角速度调制）
    """

    def __init__(self):
        super().__init__("TurbineSimulator", category="Source")

        # ===== 转速 / 扭振参数 =====
        self.add_number_option("额定转速 (RPM)", default=3000.0)
        self.add_number_option("转速稳定性 (%)", default=99.95)
        self.add_number_option("低频晃动频率 (Hz)", default=0.05)
        self.add_number_option("角速度噪声 (rad/s)", default=0.05)

        # ===== 采样与键相 =====
        self.add_integer_option("键相脉冲 PPR", default=1)
        self.add_number_option("采样率 (Hz)", default=51200.0)
        self.add_number_option("模拟时长 (s)", default=2.0)

        # ===== 振动参数 =====
        self.add_number_option("1X 振幅 (μm)", default=30.0)
        self.add_number_option("2X 振幅 (μm)", default=8.0)
        self.add_integer_option("叶片数 (BPF)", default=42)

        self.add_number_option("扭振系数", default=0.02)  # 相对角速度扰动

        # ===== 输出 =====
        self.add_output("O-Pulse-XY")
        self.add_output("O-InstantRPM-XY")
        self.add_output("O-AvgRPM-XY")
        self.add_output("O-Vibration-XY")
        self.add_output("O-Torsional-XY")

    def on_compute(self):
        import numpy as np

        # ===== 参数 =====
        rpm_nom = self.get_option("额定转速 (RPM)")
        stability = self.get_option("转速稳定性 (%)")
        f_mod = self.get_option("低频晃动频率 (Hz)")
        noise_w = self.get_option("角速度噪声 (rad/s)")
        ppr = self.get_option("键相脉冲 PPR")
        fs = self.get_option("采样率 (Hz)")
        T = self.get_option("模拟时长 (s)")
        torsion_k = self.get_option("扭振系数")

        t = np.arange(0, T, 1/fs)
        dt = 1/fs

        # ===== 1. 角速度 ω(t) =====
        w0 = 2 * np.pi * rpm_nom / 60.0
        mod_depth = (100.0 - stability) / 100.0

        w_drift = w0 * mod_depth * np.sin(2 * np.pi * f_mod * t)
        w_noise = noise_w * np.random.randn(len(t))

        omega = w0 + w_drift + w_noise

        # ===== 2. 相位积分（绝对核心）=====
        phase = np.cumsum(omega) * dt

        # ===== 3. 瞬时 RPM（真值）=====
        instant_rpm = omega * 60.0 / (2 * np.pi)

        # ===== 4. 键相脉冲 =====
        pulse_phase = phase * ppr / (2 * np.pi)
        pulse = np.where((pulse_phase % 1.0) < 0.5, 5.0, 0.0)

        # ===== 5. 每转平均 RPM（理想测量）=====
        rev_idx = np.where(np.diff(np.floor(phase / (2*np.pi))))[0]
        if len(rev_idx) > 1:
            t_rev = t[rev_idx]
            dt_rev = np.diff(t_rev)
            rpm_avg = 60.0 / dt_rev
            t_mid = (t_rev[:-1] + t_rev[1:]) / 2.0
        else:
            t_mid, rpm_avg = [], []

        # ===== 6. 径向振动（严格锁相）=====
        vib_1x = self.get_option("1X 振幅 (μm)") * np.sin(phase)
        vib_2x = self.get_option("2X 振幅 (μm)") * np.sin(2 * phase + np.pi/4)
        vib_bpf = 2.0 * np.sin(self.get_option("叶片数 (BPF)") * phase)

        vibration = vib_1x + vib_2x + vib_bpf + 0.5 * np.random.randn(len(t))

        # ===== 7. 扭振信号（角速度调制）=====
        torsional = torsion_k * (omega - w0)

        # ===== 8. 输出 =====
        self.set_interface("O-Pulse-XY", {
            "type": "pulse",
            "data": {"x": t.tolist(), "y": pulse.tolist()}
        })

        self.set_interface("O-InstantRPM-XY", {
            "type": "rpm",
            "data": {"x": t[::10].tolist(), "y": instant_rpm[::10].tolist()}
        })

        self.set_interface("O-AvgRPM-XY", {
            "type": "rpm",
            "data": {"x": t_mid.tolist(), "y": rpm_avg.tolist()}
        })

        self.set_interface("O-Vibration-XY", {
            "type": "vibration",
            "data": {"x": t.tolist(), "y": vibration.tolist()}
        })

        self.set_interface("O-Torsional-XY", {
            "type": "torsional",
            "data": {"x": t.tolist(), "y": torsional.tolist()}
        })



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


class TimeWindow(Block):
    """
    工业级时间窗口模块
    - 负责：窗口长度、重叠、窗口函数
    - 不负责：FFT
    """
    def __init__(self):
        super().__init__("TimeWindow", category="Processing")

        self.add_input("I-List-XY")
        self.add_output("O-List-XY")

        self.add_number_option("窗口长度 (s)", default=1.0)
        self.add_number_option("重叠率 (%)", default=0.0)
        self.add_select_option(
            "窗口函数",
            items=["rect", "hann", "hamming"],
            default="hann"
        )
        self.add_select_option(
            "输出模式",
            items=["首个窗口", "全部窗口"],
            default="首个窗口"
        )

    def _get_window(self, n, win_type):
        if win_type == "hann":
            return np.hanning(n)
        elif win_type == "hamming":
            return np.hamming(n)
        else:
            return np.ones(n)

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data:
            return

        data = i_data["data"]
        x = np.array(data["x"])
        y = np.array(data["y"])
        meta = data.get("meta", {})

        fs = meta.get("fs")
        if fs is None:
            fs = 1.0 / np.mean(np.diff(x))

        win_sec = self.get_option("窗口长度 (s)")
        overlap = self.get_option("重叠率 (%)") / 100.0
        win_type = self.get_option("窗口函数")
        mode = self.get_option("输出模式")

        win_len = int(win_sec * fs)
        if win_len <= 1 or win_len > len(y):
            return

        hop = int(win_len * (1.0 - overlap))
        if hop <= 0:
            hop = win_len

        window = self._get_window(win_len, win_type)

        segments = []
        for start in range(0, len(y) - win_len + 1, hop):
            seg_y = y[start:start + win_len] * window
            seg_x = x[start:start + win_len]
            segments.append((seg_x, seg_y))

        if not segments:
            return

        if mode == "首个窗口":
            seg_x, seg_y = segments[0]
            self.set_interface("O-List-XY", {
                "type": "time_segment",
                "data": {
                    "x": seg_x.tolist(),
                    "y": seg_y.tolist(),
                    "meta": {
                        **meta,
                        "window_sec": win_sec,
                        "window": win_type
                    }
                }
            })

        else:
            # 输出多段（为后续平均谱准备）
            self.set_interface("O-List-XY", {
                "type": "time_segments",
                "data": {
                    "segments": [
                        {
                            "x": sx.tolist(),
                            "y": sy.tolist()
                        } for sx, sy in segments
                    ],
                    "meta": {
                        **meta,
                        "window_sec": win_sec,
                        "window": win_type
                    }
                }
            })


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
    """
    工业级 FFT
    - 输入：已分段的时域信号
    - 输出：单边幅值谱
    """
    def __init__(self):
        super().__init__("FFT", category="Transform")

        self.add_input("I-List-XY")
        self.add_output("O-List-XY")

        self.add_checkbox_option("幅值修正", default=True)

    def on_compute(self):
        i_data = self.get_interface("I-List-XY")
        if not i_data:
            return

        data = i_data["data"]
        meta = data.get("meta", {})

        x = np.array(data["x"])
        y = np.array(data["y"])

        fs = meta.get("fs")
        if fs is None:
            fs = 1.0 / np.mean(np.diff(x))

        N = len(y)
        if N < 2:
            return

        fft_vals = np.fft.rfft(y)
        mag = np.abs(fft_vals) / N * 2.0
        freqs = np.fft.rfftfreq(N, 1.0 / fs)

        self.set_interface("O-List-XY", {
            "type": "spectrum",
            "data": {
                "x": freqs.tolist(),
                "y": mag.tolist(),
                "meta": {
                    "fs": fs,
                    "df": fs / N,
                    "window_sec": meta.get("window_sec"),
                    "domain": "frequency"
                }
            }
        })


class SpectralAverager(Block):
    """
    工业级频谱统计模块
    """
    def __init__(self):
        super().__init__("SpectralAverager", category="Analysis")

        self.add_input("I-Spectrum-List")
        self.add_output("O-Spectrum")

        self.add_select_option(
            "平均方式",
            items=["线性", "RMS", "峰值保持"],
            default="线性"
        )

    def on_compute(self):
        i_data = self.get_interface("I-Spectrum-List")
        if not i_data:
            return

        specs = i_data["data"]["spectra"]
        meta = i_data["data"].get("meta", {})

        Y = np.array([s["y"] for s in specs])
        X = np.array(specs[0]["x"])

        mode = self.get_option("平均方式")

        if mode == "线性":
            y_avg = np.mean(Y, axis=0)
        elif mode == "RMS":
            y_avg = np.sqrt(np.mean(Y ** 2, axis=0))
        else:
            y_avg = np.max(Y, axis=0)

        self.set_interface("O-Spectrum", {
            "type": "spectrum",
            "data": {
                "x": X.tolist(),
                "y": y_avg.tolist(),
                "meta": {
                    **meta,
                    "average": mode
                }
            }
        })

class RPMTrackedFFT(Block):
    """
    转速跟踪 FFT（工业级）
    """
    def __init__(self):
        super().__init__("RPMTrackedFFT", category="Advanced")

        self.add_input("I-Signal-XY")
        self.add_input("I-Speed-XY")
        self.add_output("O-Order-Spectrum")

        self.add_number_option("转速中心 (RPM)", default=3000)
        self.add_number_option("转速带宽 (RPM)", default=50)
        self.add_number_option("窗口转数", default=10)

    def on_compute(self):
        sig = self.get_interface("I-Signal-XY")
        spd = self.get_interface("I-Speed-XY")
        if not sig or not spd:
            return

        sx = np.array(sig["data"]["x"])
        sy = np.array(sig["data"]["y"])

        rx = np.array(spd["data"]["x"])
        ry = np.array(spd["data"]["y"])

        rpm_center = self.get_option("转速中心 (RPM)")
        rpm_bw = self.get_option("转速带宽 (RPM)")
        revs = self.get_option("窗口转数")

        mask = (ry > rpm_center - rpm_bw) & (ry < rpm_center + rpm_bw)
        if not np.any(mask):
            return

        t_start = rx[mask][0]
        t_end = rx[mask][-1]

        sig_mask = (sx >= t_start) & (sx <= t_end)
        sig_y = sy[sig_mask]

        # 每转采样点
        fs = 1 / np.mean(np.diff(sx))
        rps = rpm_center / 60.0
        samples_per_rev = int(fs / rps)
        N = samples_per_rev * revs

        if len(sig_y) < N:
            return

        sig_y = sig_y[:N]

        fft = np.fft.rfft(sig_y)
        mag = np.abs(fft) / N * 2
        orders = np.fft.rfftfreq(N, 1 / samples_per_rev)

        self.set_interface("O-Order-Spectrum", {
            "type": "order_spectrum",
            "data": {
                "x": orders.tolist(),
                "y": mag.tolist(),
                "meta": {
                    "rpm": rpm_center,
                    "revs": revs
                }
            }
        })


class OrderMap(Block):
    """
    阶次瀑布图（Order Map）
    """
    def __init__(self):
        super().__init__("OrderMap", category="Advanced")

        self.add_input("I-Signal-XY")
        self.add_input("I-Speed-XY")
        self.add_output("O-OrderMap")

        self.add_number_option("阶次上限", default=10)
        self.add_number_option("每转采样点", default=1024)

    def on_compute(self):
        sig = self.get_interface("I-Signal-XY")
        spd = self.get_interface("I-Speed-XY")
        if not sig or not spd:
            return

        sx = np.array(sig["data"]["x"])
        sy = np.array(sig["data"]["y"])

        rx = np.array(spd["data"]["x"])
        ry = np.array(spd["data"]["y"])

        orders = self.get_option("阶次上限")
        pts = self.get_option("每转采样点")

        maps = []

        for i in range(len(rx) - 1):
            rpm = ry[i]
            if rpm <= 0:
                continue

            rps = rpm / 60.0
            fs = 1 / np.mean(np.diff(sx))
            samples_per_rev = int(fs / rps)

            start = int((rx[i] - sx[0]) * fs)
            N = pts

            if start + N >= len(sy):
                continue

            seg = sy[start:start + N]
            fft = np.fft.rfft(seg)
            mag = np.abs(fft)

            maps.append({
                "rpm": rpm,
                "order": np.linspace(0, orders, len(mag)).tolist(),
                "mag": mag.tolist()
            })

        self.set_interface("O-OrderMap", {
            "type": "order_map",
            "data": maps
        })




class TachoToRPM(Block):
    """
    键相转速提取模块

    输出的是：
    - 每转 / 多转平均转速
    - 非瞬时量
    """
    def __init__(self):
        super().__init__("TachoToRPM", category="Order Analysis")

        self.add_input("I-Pulse-XY")
        self.add_output("O-RPM-XY")

        self.add_integer_option("每转脉冲数 (PPR)", default=1, min_val=1)
        self.add_number_option("脉冲阈值 (V)", default=2.5)
        self.add_integer_option("滑动脉冲数", default=1, min_val=1)

    def on_compute(self):
        import numpy as np

        i_data = self.get_interface("I-Pulse-XY")
        if not i_data: return

        x = np.array(i_data["data"]["x"])
        y = np.array(i_data["data"]["y"])

        ppr = self.get_option("每转脉冲数 (PPR)")
        threshold = self.get_option("脉冲阈值 (V)")
        win = self.get_option("滑动脉冲数")

        # === 1. 上升沿检测 + 线性内插 ===
        idx = np.where((y[:-1] < threshold) & (y[1:] >= threshold))[0]
        if len(idx) < win + 1:
            return

        t_edge = []
        for i in idx:
            t0, t1 = x[i], x[i+1]
            y0, y1 = y[i], y[i+1]
            t_edge.append(t0 + (threshold - y0) * (t1 - t0) / (y1 - y0))
        t_edge = np.array(t_edge)

        # === 2. 多脉冲平均转速 ===
        t_start = t_edge[:-win]
        t_end = t_edge[win:]
        dt = t_end - t_start

        rpm = (60.0 * win / ppr) / dt
        t_mid = (t_start + t_end) / 2.0

        # === 3. 输出 ===
        self.set_interface("O-RPM-XY", {
            "type": "rpm",
            "data": {
                "x": t_mid.tolist(),
                "y": rpm.tolist()
            }
        })



class AngularResampler(Block):
    """
    角域重采样模块：基于键相脉冲精确时刻，将时间轴信号映射到等角度空间。
    适用于消除非稳态过程（升降速）中的阶次模糊。
    """
    def __init__(self):
        super().__init__("AngularResampler", category="Order Analysis")
        # 输入：振动原始信号(Time-Domain) 和 键相脉冲信号(Pulse)
        self.add_input("I-Vibration-XY")
        self.add_input("I-Pulse-XY")
        self.add_output("O-List-XY")
        
        # 配置参数
        self.add_integer_option("每转脉冲数 (PPR)", default=1, min_val=1)
        self.add_integer_option("每转采样点数", default=1024, min_val=16, max_val=4096)
        self.add_number_option("脉冲触发阈值 (V)", default=2.5)

    def on_compute(self):
        vib_data = self.get_interface("I-Vibration-XY")
        pulse_data = self.get_interface("I-Pulse-XY")
        
        if not (vib_data and pulse_data):
            return

        # 1. 获取数据
        t_vib = np.array(vib_data["data"]["x"])
        v_vib = np.array(vib_data["data"]["y"])
        t_pulse = np.array(pulse_data["data"]["x"])
        v_pulse = np.array(pulse_data["data"]["y"])
        
        ppr = self.get_option("每转脉冲数 (PPR)")
        res_per_rev = self.get_option("每转采样点数")
        threshold = self.get_option("脉冲触发阈值 (V)")

        # 2. 精确提取脉冲边沿时刻（亚采样插值）
        # 寻找上升沿
        rising_idx = np.where((v_pulse[:-1] < threshold) & (v_pulse[1:] >= threshold))[0]
        if len(rising_idx) < 2:
            return

        t_edge = []
        for idx in rising_idx:
            # 线性内插求出精确时刻
            t0, t1 = t_pulse[idx], t_pulse[idx+1]
            v0, v1 = v_pulse[idx], v_pulse[idx+1]
            t_acc = t0 + (threshold - v0) * (t1 - t0) / (v1 - v0)
            t_edge.append(t_acc)
        t_edge = np.array(t_edge)

        # 3. 计算每个脉冲时刻对应的累计角度 (弧度)
        # 每个脉冲间隔的角度增量 = 2 * PI / PPR
        angle_increment = 2 * np.pi / ppr
        cumulative_angles = np.arange(len(t_edge)) * angle_increment

        # 4. 构建 时间-角度 映射函数
        # 这一步建立的是：给定一个时刻，它对应转子的哪个角度
        # 使用三次样条(cubic)能更平滑地处理加减速过程
        time_to_angle_func = interp1d(t_edge, cumulative_angles, kind='cubic', 
                                      bounds_error=False, fill_value="extrapolate")

        # 5. 计算原始振动信号每个采样点对应的角度
        vib_angles = time_to_angle_func(t_vib)

        # 6. 等角度重采样
        # 确定角域轴的起止范围（只取有脉冲覆盖的部分，避免边界失真）
        min_angle = cumulative_angles[0]
        max_angle = cumulative_angles[-1]
        
        total_revs = (max_angle - min_angle) / (2 * np.pi)
        num_target_points = int(total_revs * res_per_rev)
        
        if num_target_points < 2:
            return

        # 生成均匀的角度序列（角域时间轴）
        target_angle_axis = np.linspace(min_angle, max_angle, num_target_points)

        # 7. 将振动幅值插值到等角度轴上
        # 角度-幅值映射
        angle_to_vib_func = interp1d(vib_angles, v_vib, kind='linear', 
                                     bounds_error=False, fill_value=0)
        resampled_vibration = angle_to_vib_func(target_angle_axis)

        # 8. 输出
        # 为了方便后续FFT计算，我们将角度轴归一化或转换为转数
        self.set_interface("O-List-XY", {
            "type": "angular_domain",
            "data": {
                "x": target_angle_axis.tolist(), # 单位：rad
                "y": resampled_vibration.tolist(),
                "info": {
                    "ppr": ppr,
                    "points_per_rev": res_per_rev,
                    "total_revs": total_revs
                }
            }
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
    TimeWindow(),
    FFT(),
    SpectralAverager(),
    RPMTrackedFFT(),
    OrderMap(),
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