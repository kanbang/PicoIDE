

import math
import time
from flow import Block
from typing import List
import numpy as np

# from iot import NodeEngine
# from iot import Block

# from .node_engine import NodeEngine
# from .node_engine import Block


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
            x_data = [start_time + i * (1/fs) for i in range(count)]
            y_data = [
                math.sin(2 * math.pi * 50 * (i/fs) + channel) + # 50Hz 信号
                0.2 * math.sin(2 * math.pi * 120 * (i/fs))         # 120Hz 谐波
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


############################################################
# 傅里叶变换
def fourier_transform(signal, seconds=1):
    """
    计算信号的傅里叶变换频谱
    
    参数:
        signal (array_like): 输入的时域信号（1D数组）
        seconds (float): 信号的总时长（秒）
    
    返回:
        freqs (ndarray): 频率轴数组（Hz），只包含正频率
        magnitude (ndarray): 对应的幅值谱（已归一化）
    """
    N = len(signal)                     # 采样点数
    fs = N / seconds                    # 计算实际采样频率（Hz）
    
    # 计算FFT（返回复数数组）
    fft_result = np.fft.fft(signal)     
    
    # 计算幅值谱并归一化（对于实数信号）
    magnitude = np.abs(fft_result) / N * 2   # ×2 因为能量分布在正负频率
    magnitude = magnitude[:N//2]             # 取正频率部分
    
    # 计算频率轴（0 ~ fs/2）
    freqs = np.fft.fftfreq(N, 1/fs)[:N//2]  # 单位: Hz

    data = {"x": freqs.tolist(), "y": magnitude.tolist()}
    return data
                                

    # n = len(signal)
    # frq = np.arange(n)
    # half_x = frq[range(int(n / 2))]  # 取一半区间

    # fft_y = np.fft.fft(signal)
    # abs_y = np.abs(fft_y)  # 取复数的绝对值，即复数的模(双边频谱)
    # gui_y = abs_y / n  # 归一化处理（双边频谱）
    # gui_half_y = gui_y[range(int(n / 2))]  # 由于对称性，只取一半区间（单边频谱）

    # data = {"x": half_x.tolist(), "y": gui_half_y.tolist()}

    return data


##########################################################################################
# Channel
channel = Block(name="Channel")
channel.add_output("O-List-XY")
channel.add_option(name="启用", type="checkbox", value=True)
channel.add_option(
    name="通道",
    type="select",
    items=[
        "Channel 0",
        "Channel 1",
        "Channel 2",
        "Channel 3",
        "Channel 4",
        "Channel 5",
        "Channel 6",
        "Channel 7",
    ],
)

ChannelMap = {
    "Channel 0": 0,
    "Channel 1": 1,
    "Channel 2": 2,
    "Channel 3": 3,
    "Channel 4": 4,
    "Channel 5": 5,
    "Channel 6": 6,
    "Channel 7": 7,
}


def channel_func(self):
    # sensor = self.get_interface(name="I-Sensor")
    on = self.get_option("启用")
    if not on:
        return

    channel = ChannelMap[self.get_option("通道")]

    data = adlink_bridge_instance.get_channel_data(channel)

    self.set_interface(
        name="O-List-XY",
        value={"type": "channel", "data": data},
    )


channel.add_compute(channel_func)


##########################################################################################
# X, Y
list1d = Block(name="ToList1D")
list1d.add_input("I-List-XY")
list1d.add_output("O-List-V")
list1d.add_option(name="输出", type="select", items=["X", "Y"], value="Y")


def list1d_func(self):
    i_data_xy = self.get_interface(name="I-List-XY")
    vout = self.get_option("输出")
    if vout == "X":
        self.set_interface(
            name="O-List-V",
            value={"type": "list1d", "data": i_data_xy["data"]["x"]},
        )
    else:
        self.set_interface(
            name="O-List-V",
            value={"type": "list1d", "data": i_data_xy["data"]["y"]},
        )


list1d.add_compute(list1d_func)

list2d = Block(name="ToList2D")
list2d.add_input("I-List-X")
list2d.add_input("I-List-Y")
list2d.add_output("O-List-XY")


def list2d_func(self):
    i_data_x = self.get_interface(name="I-List-X")
    i_data_y = self.get_interface(name="I-List-Y")
    self.set_interface(
        name="O-List-XY",
        value={
            "type": "list2d",
            "data": {"x": i_data_x["data"], "y": i_data_y["data"]},
        },
    )


list2d.add_compute(list2d_func)

##########################################################################################
# FourierTransform
fourier = Block(name="FourierTransform")
fourier.add_input("I-List-V")
fourier.add_output("O-List-XY")
fourier.add_option(name="绝对值", type="checkbox", value=True)


def fourier_func(self):
    i_data = self.get_interface(name="I-List-V")
    data = i_data["data"]
    abs = self.get_option("绝对值")
    fdata = fourier_transform(data)

    self.set_interface(name="O-List-XY", value={"type": "fourier", "data": fdata})


fourier.add_compute(fourier_func)


##########################################################################################
# Result
result = Block(name="Result")
result.add_input("List-XY")
result.add_option(name="类型", type="select", items=["时域", "频域", "FREE"])
result.add_option(name="名称", type="input", value="")


def result_func(self):
    i_data = self.get_interface(name="List-XY")
    t = self.get_option("类型")
    name = self.get_option("名称")
    data = {"name": name, "value": i_data["data"]}
    if t == "时域":
        adlink_bridge_instance.add_data_t(data)
    elif t == "频域":
        adlink_bridge_instance.add_data_p(data)
    else:
        adlink_bridge_instance.add_data_xy(data)


result.add_compute(result_func)


##########################################################################################
##########################################################################################

daq_blocks=[channel, list1d, list2d, fourier, result]
