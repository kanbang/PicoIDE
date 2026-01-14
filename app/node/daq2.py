
import json
from flow.block import Block
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

# ==========================================
#  硬件中转与信号处理 Blocks
# ==========================================


adlink_bridge = type("AdlinkBridge", (object,), {
    "data_t": [], "data_p": [], "data_xy": [],
    "add_data_t": lambda self, d: self.data_t.append(d),
    "add_data_p": lambda self, d: self.data_p.append(d),
    "add_data_xy": lambda self, d: self.data_xy.append(d)
})()

class ChannelBlock(Block):
    def __init__(self):
        super().__init__("Channel")
        self.add_output("O-List-XY")
        self.add_select_option("通道", [f"CH {i}" for i in range(8)], "CH 0")
    def on_compute(self):
        t = np.linspace(0, 1, 1000)
        y = np.sin(2 * np.pi * 50 * t) + 0.5 * np.random.randn(1000)
        self.set_interface("O-List-XY", {"type": "raw", "data": {"x": t.tolist(), "y": y.tolist()}})

class SignalSplitterBlock(Block):
    def __init__(self):
        super().__init__("SignalSplitter")
        self.add_input("I-Signal")
        self.add_output("O-X")
        self.add_output("O-Y")
    def on_compute(self):
        pkg = self.get_interface("I-Signal")
        if pkg:
            self.set_interface("O-X", {"data": pkg["data"]["x"]})
            self.set_interface("O-Y", {"data": pkg["data"]["y"]})

class FFTAdvancedBlock(Block):
    def __init__(self):
        super().__init__("FFTAdvanced")
        self.add_input("I-Vector")
        self.add_output("O-Spectrum")
        self.add_select_option("窗函数", ["None", "Hanning", "Hamming"], "Hanning")
    def on_compute(self):
        v = self.get_interface("I-Vector")
        if not v: return
        y = np.array(v["data"])
        if self.get_option("窗函数") == "Hanning": y *= np.hanning(len(y))
        n = len(y)
        mag = np.abs(np.fft.rfft(y)) * (2.0/n)
        freq = np.fft.rfftfreq(n, d=1/1000.0).tolist()
        self.set_interface("O-Spectrum", {"type": "fft", "data": {"x": freq, "y": mag.tolist()}})

class AngleResampleBlock(Block):
    def __init__(self):
        super().__init__("AngleResample")
        self.add_input("I-Y")
        self.add_input("I-Tacho")
        self.add_output("O-Angle")
    def on_compute(self):
        iy, it = self.get_interface("I-Y"), self.get_interface("I-Tacho")
        if not (iy and it): return
        y, t = np.array(iy["data"]), np.array(it["data"])
        new_t = np.linspace(t[0], t[-1], len(t))
        new_y = interp1d(t, y, kind='cubic')(new_t)
        self.set_interface("O-Angle", {"data": {"x": new_t.tolist(), "y": new_y.tolist()}})

class SignalMergerBlock(Block):
    def __init__(self):
        super().__init__("SignalMerger")
        self.add_input("I-X")
        self.add_input("I-Y")
        self.add_output("O-XY")
    def on_compute(self):
        ix, iy = self.get_interface("I-X"), self.get_interface("I-Y")
        if ix and iy:
            self.set_interface("O-XY", {"data": {"x": ix["data"], "y": iy["data"]}})

# ==========================================
# 4. IO 与 可视化 Blocks
# ==========================================

class CSVWriterBlock(Block):
    def __init__(self):
        super().__init__("CSVWriter")
        self.add_input("I-XY")
        self.add_text_input_option("路径", "data.csv")
    def on_compute(self):
        d = self.get_interface("I-XY")
        if d: pd.DataFrame(d["data"]).to_csv(self.get_option("路径"), index=False)

class MQTTPublishBlock(Block):
    def __init__(self):
        super().__init__("MQTTPublish")
        self.add_input("I-Data")
        self.add_text_input_option("Topic", "sensor/data")
    def on_compute(self):
        pass
        # d = self.get_interface("I-Data")
        # if d:
        #     c = mqtt.Client()
        #     c.connect("broker.emqx.io")
        #     c.publish(self.get_option("Topic"), json.dumps(d))
        #     c.disconnect()

class HTMLChartBlock(Block):
    def __init__(self):
        super().__init__("HTMLChart")
        self.add_input("I-XY")
        self.add_output("O-HTML")
    def on_compute(self):
        d = self.get_interface("I-XY")
        if d:
            cfg = {"xAxis": {"data": d["data"]["x"]}, "series": [{"type": "line", "data": d["data"]["y"]}]}
            self.set_interface("O-HTML", json.dumps(cfg))

class ResultBlock(Block):
    def __init__(self):
        super().__init__("Result")
        self.add_input("I-XY")
        self.add_select_option("类型", ["时域", "频域"], "时域")
    def on_compute(self):
        d = self.get_interface("I-XY")
        if not d: return
        if self.get_option("类型") == "时域": adlink_bridge.add_data_t(d["data"])
        else: adlink_bridge.add_data_p(d["data"])


daq_blocks = [
    ChannelBlock(),
    SignalSplitterBlock(),
    AngleResampleBlock(),
    FFTAdvancedBlock(),
    SignalMergerBlock(),
    CSVWriterBlock(),
    HTMLChartBlock(),
    ResultBlock(),
]