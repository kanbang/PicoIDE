import math
import time
import numpy as np
import asyncio
from types import MethodType

from node.block import Block

# 假设这是你的 bridge 实例
# from your_module import adlink_bridge_instance


class AdlinkBridge:
    def __init__(self) -> None:
        self.init = False
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
            # 模拟 100 个点，采样间隔 0.001s (1kHz)
            count = 100
            fs = 1000
            start_time = time.time()

            # 生成时间轴 x 和 振幅 y (简谐振动 + 噪声)
            x_data = [start_time + i * (1 / fs) for i in range(count)]
            y_data = [
                math.sin(2 * math.pi * 50 * (i / fs) + channel)  # 50Hz 信号
                + 0.2 * math.sin(2 * math.pi * 120 * (i / fs))  # 120Hz 谐波
                for i in range(count)
            ]

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
        param = {"fSamplerate": self.fSamplerate, "channels": self.channels}
        return param

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


class ChannelBlock(Block):
    def __init__(self):
        super().__init__("Channel")
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

        data = {
            "x": list(range(100)),
            "y": np.sin(np.linspace(0, 10, 100)).tolist(),
        }  # 模拟数据
        self.set_interface("O-List-XY", {"type": "channel", "data": data})


class ToList1DBlock(Block):
    def __init__(self):
        super().__init__("ToList1D")
        self.add_input("I-List-XY")
        self.add_output("O-List-V")
        self.add_select_option("输出", items=["X", "Y"], default="Y")

    def on_compute(self):
        i_data_xy = self.get_interface("I-List-XY")
        if not i_data_xy:
            return

        vout = self.get_option("输出").lower()  # 转为小写 x 或 y
        data_source = i_data_xy["data"].get(vout, [])
        self.set_interface("O-List-V", {"type": "list1d", "data": data_source})


class ToList2DBlock(Block):
    def __init__(self):
        super().__init__("ToList2D")
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


class FourierTransformBlock(Block):
    def __init__(self):
        super().__init__("FourierTransform")
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


class ResultBlock(Block):
    def __init__(self):
        super().__init__("Result")
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


daq_blocks = [
    ChannelBlock(),
    ToList1DBlock(),
    ToList2DBlock(),
    FourierTransformBlock(),
    ResultBlock(),
]
