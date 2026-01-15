"""
PicoIDE DAQ Node Module - Industrial Grade Data Acquisition and Processing

This module provides a comprehensive data acquisition and signal processing framework
for industrial applications, featuring:
- Unified data format with rich metadata
- Robust error handling and logging
- Type hints for better IDE support
- Configurable parameters with validation
- High-performance vectorized computations
- Extensible block architecture

Author: PicoIDE Team
Version: 2.0.0
License: MIT
"""

import math
import time
import logging
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.signal as signal
from scipy.interpolate import interp1d

from flow.block import Block


# ==================== 配置和日志系统 ====================

class DAQConfig:
    """全局配置管理类"""
    
    # 采样相关
    DEFAULT_SAMPLERATE = 51200.0
    MAX_SAMPLERATE = 200000.0
    MIN_SAMPLERATE = 100.0
    
    # 数据处理
    DEFAULT_WINDOW_TYPE = "hann"
    MAX_WINDOW_SIZE = 1048576  # 2^20
    MIN_WINDOW_SIZE = 64
    
    # 性能
    ENABLE_CACHE = True
    PARALLEL_THRESHOLD = 10000  # 数据点数超过此值时启用并行处理
    
    # 日志
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 文件
    DEFAULT_OUTPUT_DIR = Path("./output")
    TEMP_DIR = Path("./temp")


class DomainType(Enum):
    """数据域类型枚举"""
    TIME = "time"
    FREQUENCY = "frequency"
    ORDER = "order"
    ANGULAR = "angular"
    UNKNOWN = "unknown"


class DataType(Enum):
    """数据类型枚举"""
    WAVEFORM = "waveform"
    SPECTRUM = "spectrum"
    PULSE = "pulse"
    RPM = "rpm"
    VIBRATION = "vibration"
    TORSIONAL = "torsional"
    ENVELOPE = "envelope"
    FILTERED = "filtered"
    STATS = "stats"
    UNKNOWN = "unknown"


@dataclass
class SignalMetadata:
    """信号元数据类 - 工业级数据结构"""
    # 基础信息
    fs: float = 51200.0  # 采样率 (Hz)
    unit: str = "V"  # 物理单位
    domain: str = "time"  # 数据域
    data_type: str = "waveform"  # 数据类型
    
    # 时间信息
    start_time: Optional[float] = None  # 开始时间 (s)
    duration: Optional[float] = None  # 持续时间 (s)
    
    # 采集信息
    channel: Optional[int] = None  # 通道号
    sensor_type: Optional[str] = None  # 传感器类型
    
    # 处理信息
    window_type: Optional[str] = None  # 窗口类型
    window_sec: Optional[float] = None  # 窗口长度 (s)
    overlap: Optional[float] = None  # 重叠率
    
    # 频域信息
    df: Optional[float] = None  # 频率分辨率
    freq_range: Optional[Tuple[float, float]] = None  # 频率范围
    
    # 阶次信息
    rpm: Optional[float] = None  # 转速
    ppr: Optional[int] = None  # 每转脉冲数
    points_per_rev: Optional[int] = None  # 每转采样点
    total_revs: Optional[float] = None  # 总转数
    
    # 其他
    description: Optional[str] = None  # 描述
    tags: List[str] = field(default_factory=list)  # 标签
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    def validate(self) -> bool:
        """验证元数据有效性"""
        if self.fs <= 0:
            return False
        if self.domain not in [e.value for e in DomainType]:
            return False
        return True


@dataclass
class SignalData:
    """统一信号数据结构 - 核心数据格式"""
    # 数据
    x: List[float] = field(default_factory=list)
    y: List[float] = field(default_factory=list)
    
    # 元数据
    meta: SignalMetadata = field(default_factory=SignalMetadata)
    
    # 数据类型标识
    type: str = "time"
    
    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.meta, dict):
            self.meta = SignalMetadata(**self.meta)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            "type": self.type,
            "data": {
                "x": self.x,
                "y": self.y,
                "meta": self.meta.to_dict()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignalData':
        """从字典创建实例"""
        inner = data.get("data", {})
        meta = inner.get("meta", {})
        if isinstance(meta, dict):
            meta = SignalMetadata(**meta)
        return cls(
            x=inner.get("x", []),
            y=inner.get("y", []),
            meta=meta,
            type=data.get("type", "time")
        )
    
    def validate(self) -> Tuple[bool, str]:
        """验证数据有效性"""
        if len(self.x) != len(self.y):
            return False, f"X和Y长度不匹配: {len(self.x)} != {len(self.y)}"
        if len(self.x) == 0:
            return False, "数据为空"
        if not self.meta.validate():
            return False, "元数据无效"
        return True, "OK"
    
    def get_fs(self) -> float:
        """获取采样率"""
        return self.meta.fs
    
    def get_duration(self) -> float:
        """获取持续时间"""
        if len(self.x) >= 2:
            return self.x[-1] - self.x[0]
        return 0.0
    
    def get_nyquist(self) -> float:
        """获取奈奎斯特频率"""
        return self.meta.fs / 2.0


# 配置日志
logging.basicConfig(
    level=DAQConfig.LOG_LEVEL,
    format=DAQConfig.LOG_FORMAT
)
logger = logging.getLogger(__name__)


# ==================== 异常类 ====================

class DAQError(Exception):
    """DAQ基础异常类"""
    pass


class DataValidationError(DAQError):
    """数据验证错误"""
    pass


class ProcessingError(DAQError):
    """处理错误"""
    pass


class ConfigError(DAQError):
    """配置错误"""
    pass


# ==================== 工具函数 ====================

def validate_fs(fs: float) -> float:
    """验证并修正采样率"""
    if not isinstance(fs, (int, float)) or fs <= 0:
        raise ConfigError(f"无效的采样率: {fs}")
    if fs > DAQConfig.MAX_SAMPLERATE:
        logger.warning(f"采样率 {fs} 超过最大值，已限制为 {DAQConfig.MAX_SAMPLERATE}")
        return DAQConfig.MAX_SAMPLERATE
    if fs < DAQConfig.MIN_SAMPLERATE:
        logger.warning(f"采样率 {fs} 低于最小值，已提升为 {DAQConfig.MIN_SAMPLERATE}")
        return DAQConfig.MIN_SAMPLERATE
    return float(fs)


def calculate_fs_from_time_axis(t: np.ndarray) -> float:
    """从时间轴计算采样率"""
    if len(t) < 2:
        return 1.0
    dt = np.mean(np.diff(t))
    if dt <= 0:
        logger.warning("时间轴间隔无效，使用默认采样率")
        return DAQConfig.DEFAULT_SAMPLERATE
    return 1.0 / dt


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """安全除法"""
    if b == 0:
        logger.warning(f"除零错误: {a} / {b}，返回默认值 {default}")
        return default
    return a / b


# ==================== AdlinkBridge - 工业级采集卡桥接类 ====================

class AdlinkBridge:
    """
    工业级采集卡数据桥接类
    
    功能特性：
    - 支持真实采集卡和模拟数据生成
    - 完整的参数管理和验证
    - 统一的数据格式
    - 详细的错误处理和日志
    - 线程安全的数据收集
    
    Attributes:
        fSamplerate: 采样率 (Hz)
        channels: 已启用通道列表
        ch_data: 真实采集数据字典
    """
    
    def __init__(self) -> None:
        """初始化采集卡桥接"""
        # 采集卡参数
        self.fSamplerate: float = 0.0
        self.AdRange: float = 0.0
        self.channels: List[int] = []
        
        # 数据存储
        self.ch_data: Optional[Dict[int, SignalData]] = None
        
        # 结果数据（供前端显示）
        self.data_t: List[Dict[str, Any]] = []
        self.data_p: List[Dict[str, Any]] = []
        self.data_xy: List[Dict[str, Any]] = []
        
        # 状态
        self._initialized: bool = False
        self._lock = False
        
        logger.info("AdlinkBridge 已初始化")
    
    def set_fsamplerate(self, fSamplerate: float) -> None:
        """设置采样率"""
        try:
            self.fSamplerate = validate_fs(fSamplerate)
            logger.info(f"采样率已设置为: {self.fSamplerate} Hz")
        except ConfigError as e:
            logger.error(f"设置采样率失败: {e}")
            raise
    
    def set_adrange(self, AdRange: float) -> None:
        """设置量程"""
        if AdRange <= 0:
            raise ConfigError(f"无效的量程: {AdRange}")
        self.AdRange = AdRange
        logger.debug(f"量程已设置为: {self.AdRange}")
    
    def add_channel(self, channel: int) -> None:
        """添加启用通道"""
        if not isinstance(channel, int) or channel < 0:
            raise ConfigError(f"无效的通道号: {channel}")
        if channel not in self.channels:
            self.channels.append(channel)
            logger.debug(f"已添加通道: {channel}")
    
    def set_channels_data(self, ch_data: Dict[int, SignalData]) -> None:
        """设置真实采集数据"""
        self.ch_data = ch_data
        logger.info(f"已设置 {len(ch_data)} 个通道的真实数据")
    
    def get_channel_data(self, channel: int) -> Optional[SignalData]:
        """
        获取指定通道数据
        
        Args:
            channel: 通道号
            
        Returns:
            SignalData对象，如果无数据则返回None
        """
        if self.ch_data is not None and channel in self.ch_data:
            return self.ch_data[channel]
        
        # 生成模拟数据
        return self._generate_simulated_data(channel)
    
    def _generate_simulated_data(self, channel: int) -> SignalData:
        """
        生成模拟数据（用于调试和演示）
        
        Args:
            channel: 通道号
            
        Returns:
            模拟的SignalData对象
        """
        try:
            # 模拟参数
            count = 1000
            fs = self.fSamplerate if self.fSamplerate > 0 else DAQConfig.DEFAULT_SAMPLERATE
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
            
            # 根据通道类型生成数据
            if channel in [0, 1, 2, 3]:  # 振动通道
                y = self._generate_vibration_signal(
                    t, instantaneous_freq, torsional_phase, fs, count
                )
                data_type = DataType.VIBRATION.value
                unit = "um"
                
            elif channel == 4:  # 转速脉冲通道
                y = self._generate_pulse_signal(t, instantaneous_rpm, fs)
                data_type = DataType.PULSE.value
                unit = "V"
                
            elif channel == 5:  # 瞬时转速通道
                y = instantaneous_rpm
                data_type = DataType.RPM.value
                unit = "RPM"
                
            else:
                y = np.zeros(count)
                data_type = DataType.UNKNOWN.value
                unit = "V"
            
            # 创建元数据
            meta = SignalMetadata(
                fs=fs,
                unit=unit,
                domain=DomainType.TIME.value,
                data_type=data_type,
                channel=channel,
                duration=count / fs,
                description=f"模拟通道 {channel} 数据"
            )
            
            return SignalData(
                x=t.tolist(),
                y=y.tolist(),
                meta=meta,
                type="time"
            )
            
        except Exception as e:
            logger.error(f"生成模拟数据失败 (通道 {channel}): {e}")
            raise ProcessingError(f"模拟数据生成失败: {e}")
    
    def _generate_vibration_signal(
        self, 
        t: np.ndarray, 
        instantaneous_freq: np.ndarray,
        torsional_phase: np.ndarray,
        fs: float,
        count: int
    ) -> np.ndarray:
        """生成振动信号"""
        # 基础振动分量
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
        
        return y
    
    def _generate_pulse_signal(
        self,
        t: np.ndarray,
        instantaneous_rpm: np.ndarray,
        fs: float
    ) -> np.ndarray:
        """生成脉冲信号"""
        pulse_times = []
        current_angle = 0.0
        for i in range(len(t)):
            deg_per_sec = instantaneous_rpm[i] * 6
            current_angle += deg_per_sec / fs
            if current_angle >= 360:
                pulse_times.append(t[i])
                current_angle -= 360
        
        y = np.zeros(len(t))
        pulse_idx = [int(pt * fs) for pt in pulse_times if pt < t[-1]]
        y[pulse_idx] = 5.0
        
        return y
    
    def add_data_t(self, data_t: Dict[str, Any]) -> None:
        """收集时域结果"""
        self.data_t.append(data_t)
        logger.debug(f"已添加时域数据: {len(data_t)} 个数据点")
    
    def add_data_p(self, data_p: Dict[str, Any]) -> None:
        """收集频域结果"""
        self.data_p.append(data_p)
        logger.debug(f"已添加频域数据: {len(data_p)} 个数据点")
    
    def add_data_xy(self, data_xy: Dict[str, Any]) -> None:
        """收集其他结果（如阶次域）"""
        self.data_xy.append(data_xy)
        logger.debug(f"已添加XY数据: {len(data_xy)} 个数据点")
    
    def reset(self) -> None:
        """重置状态"""
        self._initialized = False
        self.fSamplerate = 0.0
        self.AdRange = 0.0
        self.channels = []
        self.ch_data = None
        self.data_t.clear()
        self.data_p.clear()
        self.data_xy.clear()
        logger.info("AdlinkBridge 已重置")
    
    def get_card_param(self) -> Dict[str, Any]:
        """获取采集参数"""
        return {
            "fSamplerate": self.fSamplerate,
            "channels": self.channels,
            "AdRange": self.AdRange
        }
    
    def get_result_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """获取并清空结果数据"""
        ret = {
            "t": self.data_t.copy(),
            "p": self.data_p.copy(),
            "xy": self.data_xy.copy()
        }
        self.data_t.clear()
        self.data_p.clear()
        self.data_xy.clear()
        return ret
    
    def init_card(self) -> None:
        """初始化采集卡（模拟）"""
        if self._initialized:
            logger.warning("采集卡已初始化，跳过重复初始化")
            return
        
        # 这里可以添加真实采集卡的初始化代码
        self._initialized = True
        logger.info("采集卡已初始化")


# 全局实例
adlink_bridge_instance = AdlinkBridge()


# ==================== BaseBlock - 基础Block类 ====================

class BaseBlock(Block):
    """
    所有Block的基类，提供通用功能
    
    功能：
    - 统一的错误处理
    - 日志记录
    - 数据验证
    - 性能监控
    """
    
    def __init__(self, name: str, category: str = "General"):
        super().__init__(name, category)
        self._logger = logging.getLogger(f"{logger.name}.{name}")
        self._compute_count = 0
        self._error_count = 0
        self._last_compute_time = 0.0
    
    def _log_compute_start(self) -> None:
        """记录计算开始"""
        self._last_compute_time = time.time()
        self._compute_count += 1
        self._logger.debug(f"开始计算 (第 {self._compute_count} 次)")
    
    def _log_compute_end(self) -> None:
        """记录计算结束"""
        elapsed = time.time() - self._last_compute_time
        self._logger.debug(f"计算完成，耗时: {elapsed:.3f}s")
    
    def _log_error(self, error: Exception, context: str = "") -> None:
        """记录错误"""
        self._error_count += 1
        self._logger.error(f"错误 (第 {self._error_count} 次): {context} - {error}")
    
    def _validate_input_data(self, data: Optional[Dict[str, Any]]) -> bool:
        """验证输入数据"""
        if data is None:
            self._logger.warning("输入数据为空")
            return False
        if "data" not in data:
            self._logger.warning("输入数据缺少 'data' 字段")
            return False
        return True
    
    def safe_compute(self) -> bool:
        """安全执行计算（带错误处理）"""
        self._log_compute_start()
        try:
            self.on_compute()
            self._log_compute_end()
            return True
        except Exception as e:
            self._log_error(e, "on_compute")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.name,
            "compute_count": self._compute_count,
            "error_count": self._error_count,
            "error_rate": safe_divide(self._error_count, self._compute_count, 0.0)
        }


# ==================== Source Blocks ====================

class ChannelSource(BaseBlock):
    """
    从模拟采集卡获取通道数据
    
    输入：无
    输出：通道信号数据
    """
    
    def __init__(self):
        super().__init__("ChannelSource", category="Source")
        self.add_output("O-List-XY")
        self.add_checkbox_option("启用", default=True)
        self.add_select_option(
            "通道",
            items=[f"Channel {i}" for i in range(8)],
            default="Channel 0"
        )
    
    def on_compute(self):
        """执行计算"""
        if not self.get_option("启用"):
            self._logger.debug("通道未启用，跳过计算")
            return
        
        try:
            channel_idx = int(self.get_option("通道").split(" ")[1])
            data = adlink_bridge_instance.get_channel_data(channel_idx)
            
            if data is None:
                self._logger.warning(f"通道 {channel_idx} 无数据")
                return
            
            # 验证数据
            is_valid, msg = data.validate()
            if not is_valid:
                raise DataValidationError(f"数据验证失败: {msg}")
            
            self.set_interface("O-List-XY", data.to_dict())
            self._logger.debug(f"成功获取通道 {channel_idx} 数据")
            
        except Exception as e:
            self._log_error(e, f"通道 {channel_idx}")
            raise

class TurbineSimulator(BaseBlock):
    """
    核电汽轮机高精度扭振模拟器 (V2.0 修正版)
    
    功能：
    - 模拟核电长轴系的多阶扭振模态 (12.5Hz SSR, 100Hz 电气波动)
    - 采用脉冲差分算法，使平均转速能够追踪瞬时趋势
    - 模拟径向振动与叶片通过频率 (BPF)
    """
    
    def __init__(self):
        super().__init__("TurbineSimulator", category="Source")
        
        # --- 基础运行参数 ---
        self.add_number_option("额定转速 (RPM)", default=1500.0, min_val=0.0)
        self.add_number_option("电网频率 (Hz)", default=50.0, min_val=40.0)
        self.add_number_option("采样率 (Hz)", default=12800.0, min_val=1000.0)
        self.add_number_option("模拟时长 (s)", default=5.0, min_val=0.1)
        
        # --- 扭振与稳定性参数 ---
        self.add_number_option("转速稳定性 (%)", default=99.98, min_val=0.0, max_val=100.0)
        self.add_number_option("扭振模态1频率 (Hz)", default=12.5, min_val=0.1)
        self.add_number_option("扭振阻尼比", default=0.01, min_val=0.001)
        self.add_number_option("电气激励占比 (%)", default=5.0, min_val=0.0)
        
        # --- 机械特征参数 ---
        self.add_integer_option("键相脉冲 PPR", default=64, min_val=1) # 推荐设为64以看清趋势
        self.add_number_option("1X 振幅 (μm)", default=25.0, min_val=0.0)
        self.add_integer_option("叶片数 (BPF)", default=50, min_val=1)
        
        # 输出
        self.add_output("O-Pulse-XY")        # 原始脉冲信号 (TTL)
        self.add_output("O-InstantRPM-XY")  # 物理真值转速
        self.add_output("O-AvgRPM-XY")      # 测速算法得出的平均转速 (每齿更新)
        self.add_output("O-Vibration-XY")   # 轴承径向振动
        self.add_output("O-Torsional-XY")   # 扭振交流分量
    
    def on_compute(self):
        try:
            # 1. 参数获取
            rpm_nom = self.get_option("额定转速 (RPM)")
            grid_freq = self.get_option("电网频率 (Hz)")
            fs = float(self.get_option("采样率 (Hz)"))
            T = self.get_option("模拟时长 (s)")
            stability = self.get_option("转速稳定性 (%)")
            f_mode1 = self.get_option("扭振模态1频率 (Hz)")
            damping = self.get_option("扭振阻尼比")
            elec_ratio = self.get_option("电气激励占比 (%)") / 100.0
            ppr = self.get_option("键相脉冲 PPR")
            amp_1x = self.get_option("1X 振幅 (μm)")
            bpf_num = self.get_option("叶片数 (BPF)")
            
            # 2. 时间轴生成
            dt = 1.0 / fs
            t = np.arange(0, T, dt)
            N = len(t)
            
            # ==========================================
            # 物理层级 1: 刚体转速与波动
            # ==========================================
            w_nom = 2 * np.pi * rpm_nom / 60.0
            # 模拟缓慢漂移 (稳定性)
            drift_amp = w_nom * (100.0 - stability) / 100.0
            w_drift = drift_amp * np.sin(2 * np.pi * 0.2 * t)
            
            # ==========================================
            # 物理层级 2: 扭振分量 (弹性模态)
            # ==========================================
            # A. 固有模态 (SSR) - 模拟 t=0.5s 时的电网扰动冲击
            t_impact = 0.5
            w_torsion_mode1 = np.zeros_like(t)
            mask = t >= t_impact
            # 阻尼简谐振动公式
            decay = np.exp(-damping * 2 * np.pi * f_mode1 * (t[mask] - t_impact))
            w_torsion_mode1[mask] = (w_nom * 0.005) * decay * np.sin(2 * np.pi * f_mode1 * (t[mask] - t_impact))
            
            # B. 电气二倍频纹波 (2 * 50Hz = 100Hz)
            w_torsion_elec = (w_nom * 0.001 * elec_ratio) * np.sin(2 * np.pi * (2 * grid_freq) * t)
            
            # 总瞬时角速度 (包含所有波动)
            w_total = w_nom + w_drift + w_torsion_mode1 + w_torsion_elec + np.random.normal(0, 0.01, N)
            
            # ==========================================
            # 物理层级 3: 相位积分与信号生成
            # ==========================================
            # 瞬时角位移（所有信号的物理根源）
            phase_accum = np.cumsum(w_total) * dt
            
            # 1. 生成键相脉冲 (PPR 决定齿数)
            # 利用相位生成 TTL 脉冲，脉冲宽度设为 1/4 齿宽
            pulse_phase = (phase_accum * ppr / (2 * np.pi)) % 1.0
            pulse = np.where(pulse_phase < 0.25, 5.0, 0.0)
            
            # 2. 计算瞬时 RPM 真值
            rpm_instant = w_total * 60.0 / (2 * np.pi)
            
            # 3. 计算【每齿平均转速】 O-AvgRPM-XY (关键修正)
            # 寻找上升沿索引
            rising_edges = np.where((pulse[:-1] < 2.5) & (pulse[1:] >= 2.5))[0]
            if len(rising_edges) > 1:
                t_edges = t[rising_edges]
                dt_edges = np.diff(t_edges) # 相邻齿通过的时间差
                # 每一齿转过的角度是 (1/PPR) 转
                rpm_avg_val = (60.0 / ppr) / dt_edges
                t_rpm_avg = t_edges[1:] # 采样时刻对齐
            else:
                t_rpm_avg, rpm_avg_val = [], []
            
            # 4. 生成径向振动信号
            vibration = (
                amp_1x * np.sin(phase_accum) + 
                (amp_1x * 0.3) * np.sin(2 * phase_accum) + 
                2.0 * np.sin(bpf_num * phase_accum) + 
                np.random.normal(0, 0.5, N)
            )
            
            # ==========================================
            # 数据封装输出 - 使用SignalData格式
            # ==========================================
            # 基础元数据
            base_meta = SignalMetadata(
                fs=fs,
                domain=DomainType.TIME.value,
                duration=T,
                description="Nuclear Turbine High-Precision Data"
            )
            
            # O-Pulse-XY
            pulse_meta = SignalMetadata(**base_meta.to_dict())
            pulse_meta.data_type = DataType.PULSE.value
            pulse_meta.unit = "V"
            pulse_meta.ppr = ppr
            self.set_interface("O-Pulse-XY", SignalData(
                x=t.tolist(),
                y=pulse.tolist(),
                meta=pulse_meta,
                type="pulse"
            ).to_dict())
            
            # O-InstantRPM-XY (物理真值，建议降采样显示以免卡顿)
            ds = 10 if fs > 5000 else 1
            rpm_meta = SignalMetadata(**base_meta.to_dict())
            rpm_meta.data_type = DataType.RPM.value
            rpm_meta.unit = "RPM"
            rpm_meta.fs = fs / ds  # 更新采样率
            self.set_interface("O-InstantRPM-XY", SignalData(
                x=t[::ds].tolist(),
                y=rpm_instant[::ds].tolist(),
                meta=rpm_meta,
                type="rpm"
            ).to_dict())
            
            # O-AvgRPM-XY (算法观测值)
            if len(t_rpm_avg) > 0:
                avg_rpm_meta = SignalMetadata(**base_meta.to_dict())
                avg_rpm_meta.data_type = DataType.RPM.value
                avg_rpm_meta.unit = "RPM"
                avg_rpm_meta.description = "Computed per tooth"
                self.set_interface("O-AvgRPM-XY", SignalData(
                    x=t_rpm_avg.tolist(),
                    y=rpm_avg_val.tolist(),
                    meta=avg_rpm_meta,
                    type="rpm"
                ).to_dict())
            
            # O-Vibration-XY
            vib_meta = SignalMetadata(**base_meta.to_dict())
            vib_meta.data_type = DataType.VIBRATION.value
            vib_meta.unit = "um"
            self.set_interface("O-Vibration-XY", SignalData(
                x=t.tolist(),
                y=vibration.tolist(),
                meta=vib_meta,
                type="vibration"
            ).to_dict())
            
            # O-Torsional-XY (交流扭振分量)
            torsional_ac = w_torsion_mode1 + w_torsion_elec
            tors_meta = SignalMetadata(**base_meta.to_dict())
            tors_meta.data_type = DataType.TORSIONAL.value
            tors_meta.unit = "rad/s"
            self.set_interface("O-Torsional-XY", SignalData(
                x=t.tolist(),
                y=torsional_ac.tolist(),
                meta=tors_meta,
                type="torsional"
            ).to_dict())
            
            self._logger.debug(f"Turbine simulation done. PPR={ppr}, AvgPoints={len(t_rpm_avg)}")
            
        except Exception as e:
            self._log_error(e, "TurbineSimulator")
            

class CSVReader(BaseBlock):
    """
    从CSV文件读取XY数据
    
    支持功能：
    - 自动检测表头
    - 指定列名读取
    - 数据验证
    """
    
    def __init__(self):
        super().__init__("CSVReader", category="Source")
        self.add_text_input_option("文件路径", default="data.csv")
        self.add_text_input_option("X列名 (可选)", default="")
        self.add_text_input_option("Y列名 (可选)", default="")
        self.add_checkbox_option("有表头", default=True)
        self.add_output("O-List-XY")
    
    def on_compute(self):
        """执行计算"""
        try:
            file_path = self.get_option("文件路径")
            x_col = self.get_option("X列名 (可选)").strip() or None
            y_col = self.get_option("Y列名 (可选)").strip() or None
            header = 0 if self.get_option("有表头") else None
            
            # 检查文件是否存在
            if not Path(file_path).exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 读取CSV
            df = pd.read_csv(file_path, header=header)
            
            if df.empty:
                raise DataValidationError("CSV文件为空")
            
            # 提取数据
            if x_col is None and y_col is None:
                if len(df.columns) >= 2:
                    x_data = df.iloc[:, 0].tolist()
                    y_data = df.iloc[:, 1].tolist()
                else:
                    raise DataValidationError("CSV文件至少需要2列数据")
            else:
                if x_col and x_col not in df.columns:
                    raise DataValidationError(f"X列 '{x_col}' 不存在")
                if y_col and y_col not in df.columns:
                    raise DataValidationError(f"Y列 '{y_col}' 不存在")
                
                x_data = df[x_col].tolist() if x_col else list(range(len(df)))
                y_data = df[y_col].tolist() if y_col else df.iloc[:, 0].tolist()
            
            # 计算采样率
            if len(x_data) >= 2:
                fs = calculate_fs_from_time_axis(np.array(x_data))
            else:
                fs = DAQConfig.DEFAULT_SAMPLERATE
            
            # 创建元数据
            meta = SignalMetadata(
                fs=fs,
                unit="V",
                domain=DomainType.TIME.value,
                data_type=DataType.WAVEFORM.value,
                description=f"从CSV文件读取: {file_path}"
            )
            
            # 输出
            self.set_interface("O-List-XY", SignalData(
                x=x_data,
                y=y_data,
                meta=meta,
                type="time"
            ).to_dict())
            
            self._logger.debug(f"成功读取CSV文件: {file_path}")
            
        except Exception as e:
            self._log_error(e, "CSV读取")
            raise


class ConstantSource(BaseBlock):
    """输出常量值（用于测试或参数注入）"""
    
    def __init__(self):
        super().__init__("ConstantSource", category="Source")
        self.add_text_input_option("常量值", default="0.0")
        self.add_output("O-Value")
    
    def on_compute(self):
        """执行计算"""
        try:
            value_str = self.get_option("常量值")
            try:
                value = float(value_str)
            except ValueError:
                value = value_str
            
            self.set_interface("O-Value", {
                "type": "constant",
                "data": value
            })
            self._logger.debug(f"输出常量: {value}")
            
        except Exception as e:
            self._log_error(e, "常量输出")
            raise


# ==================== Conversion Blocks ====================

class XYSplitter(BaseBlock):
    """
    将XY信号拆分为独立的X和Y向量
    
    输入：XY信号
    输出：X向量、Y向量
    """
    
    def __init__(self):
        super().__init__("XYSplitter", category="Conversion")
        self.add_input("I-List-XY")
        self.add_output("O-List-X")
        self.add_output("O-List-Y")
    
    def on_compute(self):
        """执行计算"""
        try:
            data_packet = self.get_interface("I-List-XY")
            
            if not self._validate_input_data(data_packet):
                return
            
            # 使用辅助方法提取数据
            x_data, y_data = self._get_xy_data(data_packet)
            
            self.set_interface("O-List-X", {"type": "list1d", "data": x_data})
            self.set_interface("O-List-Y", {"type": "list1d", "data": y_data})
            
            self._logger.debug(f"数据拆分完成: {len(x_data)} 点")
            
        except Exception as e:
            self._log_error(e, "XY拆分")
            raise


class XYMerger(BaseBlock):
    """
    将独立的X和Y向量合并为XY信号
    
    输入：X向量、Y向量
    输出：XY信号
    """
    
    def __init__(self):
        super().__init__("XYMerger", category="Conversion")
        self.add_input("I-List-X")
        self.add_input("I-List-Y")
        self.add_output("O-List-XY")
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data_x = self.get_interface("I-List-X")
            i_data_y = self.get_interface("I-List-Y")
            
            if not (i_data_x and i_data_y):
                self._logger.warning("输入数据不完整")
                return
            
            x_data = i_data_x.get("data", [])
            y_data = i_data_y.get("data", [])
            
            if len(x_data) != len(y_data):
                raise DataValidationError(f"X和Y长度不匹配: {len(x_data)} != {len(y_data)}")
            
            # 计算采样率
            if len(x_data) >= 2:
                fs = calculate_fs_from_time_axis(np.array(x_data))
            else:
                fs = DAQConfig.DEFAULT_SAMPLERATE
            
            # 创建元数据
            meta = SignalMetadata(
                fs=fs,
                unit="V",
                domain=DomainType.TIME.value,
                data_type=DataType.WAVEFORM.value
            )
            
            self.set_interface("O-List-XY", SignalData(
                x=x_data,
                y=y_data,
                meta=meta,
                type="time"
            ).to_dict())
            
            self._logger.debug(f"数据合并完成: {len(x_data)} 点")
            
        except Exception as e:
            self._log_error(e, "XY合并")
            raise


# ==================== Processing Blocks ====================

class TimeWindow(BaseBlock):
    """
    工业级时间窗口模块
    
    功能：
    - 时间窗口分割
    - 窗口函数应用
    - 重叠处理
    - 多窗口输出
    
    不负责：FFT
    """
    
    def __init__(self):
        super().__init__("TimeWindow", category="Processing")
        
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")
        
        self.add_number_option(
            "窗口长度 (s)",
            default=1.0,
            min_val=0.001,
            max_val=1000.0
        )
        self.add_number_option(
            "重叠率 (%)",
            default=0.0,
            min_val=0.0,
            max_val=90.0
        )
        self.add_select_option(
            "窗口函数",
            items=["rect", "hann", "hamming", "blackman", "flattop"],
            default="hann"
        )
        self.add_select_option(
            "输出模式",
            items=["首个窗口", "全部窗口"],
            default="首个窗口"
        )
    
    def _get_window(self, n: int, win_type: str) -> np.ndarray:
        """获取窗口函数"""
        if win_type == "hann":
            return np.hanning(n)
        elif win_type == "hamming":
            return np.hamming(n)
        elif win_type == "blackman":
            return np.blackman(n)
        elif win_type == "flattop":
            return signal.windows.flattop(n)
        else:
            return np.ones(n)
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data = self.get_interface("I-List-XY")
            
            if not self._validate_input_data(i_data):
                return
            
            data = i_data["data"]
            x = np.array(data["x"])
            y = np.array(data["y"])
            meta = data.get("meta", {})
            
            # 获取采样率
            fs = meta.get("fs")
            if fs is None:
                fs = calculate_fs_from_time_axis(x)
            
            # 参数获取
            win_sec = self.get_option("窗口长度 (s)")
            overlap = self.get_option("重叠率 (%)") / 100.0
            win_type = self.get_option("窗口函数")
            mode = self.get_option("输出模式")
            
            # 计算窗口参数
            win_len = int(win_sec * fs)
            if win_len <= 1 or win_len > len(y):
                raise ConfigError(f"无效的窗口长度: {win_len} (数据长度: {len(y)})")
            
            hop = int(win_len * (1.0 - overlap))
            if hop <= 0:
                hop = win_len
            
            # 获取窗口函数
            window = self._get_window(win_len, win_type)
            
            # 分割数据
            segments = []
            for start in range(0, len(y) - win_len + 1, hop):
                seg_y = y[start:start + win_len] * window
                seg_x = x[start:start + win_len]
                segments.append((seg_x, seg_y))
            
            if not segments:
                raise ProcessingError("无法生成有效窗口")
            
            # 输出
            if mode == "首个窗口":
                seg_x, seg_y = segments[0]
                new_meta = SignalMetadata(**meta) if isinstance(meta, dict) else meta
                new_meta.window_sec = win_sec
                new_meta.window_type = win_type
                
                self.set_interface("O-List-XY", SignalData(
                    x=seg_x.tolist(),
                    y=seg_y.tolist(),
                    meta=new_meta,
                    type="time_segment"
                ).to_dict())
            else:
                # 输出多段 - 使用SignalData列表格式
                segments_meta = SignalMetadata(**meta) if isinstance(meta, dict) else meta
                segments_meta.window_sec = win_sec
                segments_meta.window_type = win_type
                
                self.set_interface("O-List-XY", {
                    "type": "time_segments",
                    "data": {
                        "segments": [
                            {
                                "x": sx.tolist(),
                                "y": sy.tolist(),
                                "meta": segments_meta.to_dict()
                            }
                            for sx, sy in segments
                        ]
                    }
                })
            
            self._logger.debug(f"时间窗口完成: {len(segments)} 个窗口")
            
        except Exception as e:
            self._log_error(e, "时间窗口")
            raise


class SignalFilter(BaseBlock):
    """
    数字滤波器（Butterworth）
    
    支持类型：
    - lowpass: 低通
    - highpass: 高通
    - bandpass: 带通
    - bandstop: 带阻
    """
    
    def __init__(self):
        super().__init__("SignalFilter", category="Processing")
        
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")
        
        self.add_select_option(
            "类型",
            items=["lowpass", "highpass", "bandpass", "bandstop"],
            default="lowpass"
        )
        self.add_text_input_option(
            "截止频率 (Hz, 用逗号分隔带通)",
            default="1000"
        )
        self.add_integer_option(
            "阶数",
            default=4,
            min_val=1,
            max_val=12
        )
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data = self.get_interface("I-List-XY")
            
            if not self._validate_input_data(i_data):
                return
            
            data = i_data["data"]
            x = np.array(data["x"])
            y = np.array(data["y"])
            meta = data.get("meta", {})
            
            # 获取采样率
            fs = meta.get("fs")
            if fs is None:
                fs = calculate_fs_from_time_axis(x)
            
            # 解析参数
            freq_str = self.get_option("截止频率 (Hz, 用逗号分隔带通)")
            freqs = [float(f.strip()) for f in freq_str.split(",")]
            order = self.get_option("阶数")
            filter_type = self.get_option("类型")
            
            # 设计滤波器
            nyquist = fs / 2.0
            
            # 验证频率
            for f in freqs:
                if f <= 0 or f >= nyquist:
                    raise ConfigError(f"无效的截止频率: {f} (奈奎斯特频率: {nyquist})")
            
            # 归一化频率
            if filter_type in ["lowpass", "highpass"]:
                wn = freqs[0] / nyquist
            else:
                wn = [f / nyquist for f in freqs]
            
            # 设计滤波器
            b, a = signal.butter(order, wn, btype=filter_type)
            
            # 应用滤波器
            y_filtered = signal.filtfilt(b, a, y)
            
            # 创建元数据
            new_meta = SignalMetadata(**meta) if isinstance(meta, dict) else meta
            new_meta.data_type = DataType.FILTERED.value
            
            # 输出
            self.set_interface("O-List-XY", SignalData(
                x=x.tolist(),
                y=y_filtered.tolist(),
                meta=new_meta,
                type="filtered"
            ).to_dict())
            
            self._logger.debug(f"滤波完成: {filter_type}, {freq_str} Hz, {order}阶")
            
        except Exception as e:
            self._log_error(e, "信号滤波")
            raise


class EnvelopeDetector(BaseBlock):
    """
    希尔伯特包络解调（轴承故障诊断常用）
    
    功能：
    - 计算解析信号
    - 提取包络
    """
    
    def __init__(self):
        super().__init__("EnvelopeDetector", category="Processing")
        
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data = self.get_interface("I-List-XY")
            
            if not self._validate_input_data(i_data):
                return
            
            data = i_data["data"]
            x = np.array(data["x"])
            y = np.array(data["y"])
            meta = data.get("meta", {})
            
            # 计算解析信号
            analytic = signal.hilbert(y)
            envelope = np.abs(analytic)
            
            # 创建元数据
            new_meta = SignalMetadata(**meta) if isinstance(meta, dict) else meta
            new_meta.data_type = DataType.ENVELOPE.value
            
            # 输出
            self.set_interface("O-List-XY", SignalData(
                x=x.tolist(),
                y=envelope.tolist(),
                meta=new_meta,
                type="envelope"
            ).to_dict())
            
            self._logger.debug("包络检测完成")
            
        except Exception as e:
            self._log_error(e, "包络检测")
            raise


# ==================== Transform Blocks ====================

class FFT(BaseBlock):
    """
    工业级 FFT
    
    功能：
    - 单边幅值谱
    - 幅值修正
    - 频率分辨率计算
    
    输入：时域信号（建议已分段）
    输出：频域信号
    """
    
    def __init__(self):
        super().__init__("FFT", category="Transform")
        
        self.add_input("I-List-XY")
        self.add_output("O-List-XY")
        
        self.add_checkbox_option("幅值修正", default=True)
    
    def on_compute(self):
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
                domain=DomainType.FREQUENCY.value,
                data_type=DataType.SPECTRUM.value,
                df=fs / N,
                window_sec=meta.get("window_sec"),
                description="FFT频谱"
            )
            
            # 输出
            self.set_interface("O-List-XY", SignalData(
                x=freqs.tolist(),
                y=mag.tolist(),
                meta=new_meta,
                type="spectrum"
            ).to_dict())
            
            self._logger.debug(f"FFT完成: {N} 点, 频率分辨率 {fs/N:.2f} Hz")
            
        except Exception as e:
            self._log_error(e, "FFT")
            raise


# ==================== Analysis Blocks ====================

class SpectralAverager(BaseBlock):
    """
    工业级频谱统计模块
    
    功能：
    - 线性平均
    - RMS平均
    - 峰值保持
    
    输入：频谱列表
    输出：平均频谱
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
        """执行计算"""
        try:
            i_data = self.get_interface("I-Spectrum-List")
            
            if not self._validate_input_data(i_data):
                return
            
            specs = i_data["data"]["spectra"]
            meta = i_data["data"].get("meta", {})
            
            if len(specs) == 0:
                raise DataValidationError("频谱列表为空")
            
            # 提取数据
            Y = np.array([s["y"] for s in specs])
            X = np.array(specs[0]["x"])
            
            # 计算平均
            mode = self.get_option("平均方式")
            
            if mode == "线性":
                y_avg = np.mean(Y, axis=0)
            elif mode == "RMS":
                y_avg = np.sqrt(np.mean(Y ** 2, axis=0))
            else:  # 峰值保持
                y_avg = np.max(Y, axis=0)
            
            # 创建元数据
            new_meta = SignalMetadata(**meta) if isinstance(meta, dict) else meta
            new_meta.average = mode
            new_meta.average_count = len(specs)
            
            # 输出
            self.set_interface("O-Spectrum", SignalData(
                x=X.tolist(),
                y=y_avg.tolist(),
                meta=new_meta,
                type="spectrum"
            ).to_dict())
            
            self._logger.debug(f"频谱平均完成: {len(specs)} 个频谱, {mode} 平均")
            
        except Exception as e:
            self._log_error(e, "频谱平均")
            raise


class Stats(BaseBlock):
    """
    基本统计量计算
    
    功能：
    - 均值、标准差
    - 最小值、最大值
    - 数据点数
    """
    
    def __init__(self):
        super().__init__("Stats", category="Analysis")
        
        self.add_input("I-List-XY")
        self.add_output("O-Dict")
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data = self.get_interface("I-List-XY")
            
            if not self._validate_input_data(i_data):
                return
            
            y = np.array(i_data["data"].get("y", []))
            
            if len(y) == 0:
                raise DataValidationError("数据为空")
            
            # 计算统计量
            stats = {
                "count": int(len(y)),
                "mean": float(np.mean(y)),
                "std": float(np.std(y)),
                "min": float(np.min(y)),
                "max": float(np.max(y)),
                "rms": float(np.sqrt(np.mean(y ** 2))),
                "peak_to_peak": float(np.max(y) - np.min(y)),
                "timestamp": datetime.now().isoformat()
            }
            
            self.set_interface("O-Dict", {
                "type": "stats",
                "data": stats
            })
            
            self._logger.debug(f"统计完成: {len(y)} 个数据点")
            
        except Exception as e:
            self._log_error(e, "统计计算")
            raise


# ==================== Order Analysis Blocks ====================

class TachoToRPM(BaseBlock):
    """
    键相转速提取模块
    
    功能：
    - 脉冲上升沿检测
    - 线性内插精确时刻
    - 多脉冲平均转速
    
    输出：每转/多转平均转速（非瞬时量）
    """
    
    def __init__(self):
        super().__init__("TachoToRPM", category="Order Analysis")
        
        self.add_input("I-Pulse-XY")
        self.add_output("O-RPM-XY")
        
        self.add_integer_option("每转脉冲数 (PPR)", default=1, min_val=1)
        self.add_number_option("脉冲阈值 (V)", default=2.5)
        self.add_integer_option("滑动脉冲数", default=1, min_val=1)
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data = self.get_interface("I-Pulse-XY")
            
            if not self._validate_input_data(i_data):
                return
            
            x = np.array(i_data["data"]["x"])
            y = np.array(i_data["data"]["y"])
            
            ppr = self.get_option("每转脉冲数 (PPR)")
            threshold = self.get_option("脉冲阈值 (V)")
            win = self.get_option("滑动脉冲数")
            
            # 上升沿检测 + 线性内插
            idx = np.where((y[:-1] < threshold) & (y[1:] >= threshold))[0]
            
            if len(idx) < win + 1:
                raise DataValidationError(f"脉冲不足: {len(idx)} < {win + 1}")
            
            # 线性内插求精确时刻
            t_edge = []
            for i in idx:
                t0, t1 = x[i], x[i+1]
                y0, y1 = y[i], y[i+1]
                t_acc = t0 + (threshold - y0) * (t1 - t0) / (y1 - y0)
                t_edge.append(t_acc)
            t_edge = np.array(t_edge)
            
            # 多脉冲平均转速
            t_start = t_edge[:-win]
            t_end = t_edge[win:]
            dt = t_end - t_start
            
            rpm = (60.0 * win / ppr) / dt
            t_mid = (t_start + t_end) / 2.0
            
            # 创建元数据
            meta = SignalMetadata(
                fs=1.0 / np.mean(np.diff(t_mid)),
                unit="RPM",
                domain=DomainType.TIME.value,
                data_type=DataType.RPM.value,
                ppr=ppr,
                description=f"键相转速提取 (滑动窗口: {win} 脉冲)"
            )
            
            # 输出
            self.set_interface("O-RPM-XY", SignalData(
                x=t_mid.tolist(),
                y=rpm.tolist(),
                meta=meta,
                type="rpm"
            ).to_dict())
            
            self._logger.debug(f"转速提取完成: {len(rpm)} 个数据点")
            
        except Exception as e:
            self._log_error(e, "转速提取")
            raise


class AngularResampler(BaseBlock):
    """
    角域重采样模块
    
    功能：
    - 基于键相脉冲精确时刻
    - 将时间轴信号映射到等角度空间
    - 消除非稳态过程（升降速）中的阶次模糊
    
    输入：振动信号、键相脉冲
    输出：角域信号
    """
    
    def __init__(self):
        super().__init__("AngularResampler", category="Order Analysis")
        
        self.add_input("I-Vibration-XY")
        self.add_input("I-Pulse-XY")
        self.add_output("O-List-XY")
        
        self.add_integer_option("每转脉冲数 (PPR)", default=1, min_val=1)
        self.add_integer_option(
            "每转采样点数",
            default=1024,
            min_val=16,
            max_val=4096
        )
        self.add_number_option("脉冲触发阈值 (V)", default=2.5)
    
    def on_compute(self):
        """执行计算"""
        try:
            vib_data = self.get_interface("I-Vibration-XY")
            pulse_data = self.get_interface("I-Pulse-XY")
            
            if not (vib_data and pulse_data):
                self._logger.warning("输入数据不完整")
                return
            
            # 获取数据
            t_vib = np.array(vib_data["data"]["x"])
            v_vib = np.array(vib_data["data"]["y"])
            t_pulse = np.array(pulse_data["data"]["x"])
            v_pulse = np.array(pulse_data["data"]["y"])
            
            ppr = self.get_option("每转脉冲数 (PPR)")
            res_per_rev = self.get_option("每转采样点数")
            threshold = self.get_option("脉冲触发阈值 (V)")
            
            # 精确提取脉冲边沿时刻（亚采样插值）
            rising_idx = np.where((v_pulse[:-1] < threshold) & (v_pulse[1:] >= threshold))[0]
            
            if len(rising_idx) < 2:
                raise DataValidationError(f"脉冲不足: {len(rising_idx)} < 2")
            
            # 线性内插求精确时刻
            t_edge = []
            for idx in rising_idx:
                t0, t1 = t_pulse[idx], t_pulse[idx+1]
                v0, v1 = v_pulse[idx], v_pulse[idx+1]
                t_acc = t0 + (threshold - v0) * (t1 - t0) / (v1 - v0)
                t_edge.append(t_acc)
            t_edge = np.array(t_edge)
            
            # 计算每个脉冲时刻对应的累计角度
            angle_increment = 2 * np.pi / ppr
            cumulative_angles = np.arange(len(t_edge)) * angle_increment
            
            # 构建时间-角度映射函数
            time_to_angle_func = interp1d(
                t_edge, cumulative_angles,
                kind='cubic',
                bounds_error=False,
                fill_value="extrapolate"
            )
            
            # 计算原始振动信号每个采样点对应的角度
            vib_angles = time_to_angle_func(t_vib)
            
            # 等角度重采样
            min_angle = cumulative_angles[0]
            max_angle = cumulative_angles[-1]
            
            total_revs = (max_angle - min_angle) / (2 * np.pi)
            num_target_points = int(total_revs * res_per_rev)
            
            if num_target_points < 2:
                raise DataValidationError("目标采样点数不足")
            
            # 生成均匀的角度序列
            target_angle_axis = np.linspace(min_angle, max_angle, num_target_points)
            
            # 将振动幅值插值到等角度轴上
            angle_to_vib_func = interp1d(
                vib_angles, v_vib,
                kind='linear',
                bounds_error=False,
                fill_value=0
            )
            resampled_vibration = angle_to_vib_func(target_angle_axis)
            
            # 创建元数据
            meta = SignalMetadata(
                fs=res_per_rev,  # 每转采样点数
                unit="um",
                domain=DomainType.ANGULAR.value,
                data_type=DataType.WAVEFORM.value,
                ppr=ppr,
                points_per_rev=res_per_rev,
                total_revs=total_revs,
                description="角域重采样信号"
            )
            
            # 输出
            self.set_interface("O-List-XY", SignalData(
                x=target_angle_axis.tolist(),
                y=resampled_vibration.tolist(),
                meta=meta,
                type="angular_domain"
            ).to_dict())
            
            self._logger.debug(f"角域重采样完成: {total_revs:.2f} 转, {num_target_points} 点")
            
        except Exception as e:
            self._log_error(e, "角域重采样")
            raise


class RPMTrackedFFT(BaseBlock):
    """
    转速跟踪 FFT（工业级）
    
    功能：
    - 根据转速范围选择数据段
    - 计算阶次谱
    
    输入：振动信号、转速信号
    输出：阶次谱
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
        """执行计算"""
        try:
            sig = self.get_interface("I-Signal-XY")
            spd = self.get_interface("I-Speed-XY")
            
            if not (sig and spd):
                self._logger.warning("输入数据不完整")
                return
            
            sx = np.array(sig["data"]["x"])
            sy = np.array(sig["data"]["y"])
            
            rx = np.array(spd["data"]["x"])
            ry = np.array(spd["data"]["y"])
            
            rpm_center = self.get_option("转速中心 (RPM)")
            rpm_bw = self.get_option("转速带宽 (RPM)")
            revs = self.get_option("窗口转数")
            
            # 选择转速范围内的数据
            mask = (ry > rpm_center - rpm_bw) & (ry < rpm_center + rpm_bw)
            
            if not np.any(mask):
                raise DataValidationError(f"转速范围内无数据: {rpm_center} ± {rpm_bw} RPM")
            
            t_start = rx[mask][0]
            t_end = rx[mask][-1]
            
            sig_mask = (sx >= t_start) & (sx <= t_end)
            sig_y = sy[sig_mask]
            
            # 计算每转采样点
            fs = 1 / np.mean(np.diff(sx))
            rps = rpm_center / 60.0
            samples_per_rev = int(fs / rps)
            N = samples_per_rev * revs
            
            if len(sig_y) < N:
                raise DataValidationError(f"数据长度不足: {len(sig_y)} < {N}")
            
            sig_y = sig_y[:N]
            
            # 计算FFT
            fft_vals = np.fft.rfft(sig_y)
            mag = np.abs(fft_vals) / N * 2
            orders = np.fft.rfftfreq(N, 1 / samples_per_rev)
            
            # 创建元数据
            meta = SignalMetadata(
                fs=samples_per_rev,
                unit="V",
                domain=DomainType.ORDER.value,
                data_type=DataType.SPECTRUM.value,
                rpm=rpm_center,
                total_revs=revs,
                points_per_rev=samples_per_rev,
                description=f"转速跟踪FFT: {rpm_center} RPM"
            )
            
            # 输出
            self.set_interface("O-Order-Spectrum", SignalData(
                x=orders.tolist(),
                y=mag.tolist(),
                meta=meta,
                type="order_spectrum"
            ).to_dict())
            
            self._logger.debug(f"转速跟踪FFT完成: {rpm_center} RPM, {revs} 转")
            
        except Exception as e:
            self._log_error(e, "转速跟踪FFT")
            raise


class OrderMap(BaseBlock):
    """
    阶次瀑布图（Order Map）
    
    功能：
    - 生成阶次-转速-幅值三维图
    - 适合分析变速过程
    
    输入：振动信号、转速信号
    输出：阶次图数据
    """
    
    def __init__(self):
        super().__init__("OrderMap", category="Advanced")
        
        self.add_input("I-Signal-XY")
        self.add_input("I-Speed-XY")
        self.add_output("O-OrderMap")
        
        self.add_number_option("阶次上限", default=10)
        self.add_integer_option("每转采样点", default=1024)
    
    def on_compute(self):
        """执行计算"""
        try:
            sig = self.get_interface("I-Signal-XY")
            spd = self.get_interface("I-Speed-XY")
            
            if not (sig and spd):
                self._logger.warning("输入数据不完整")
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
            
            if len(maps) == 0:
                raise ProcessingError("无法生成阶次图")
            
            # 输出
            self.set_interface("O-OrderMap", {
                "type": "order_map",
                "data": maps
            })
            
            self._logger.debug(f"阶次图完成: {len(maps)} 帧")
            
        except Exception as e:
            self._log_error(e, "阶次图")
            raise


# ==================== Sink Blocks ====================

class ResultSink(BaseBlock):
    """
    结果收集器
    
    功能：
    - 将数据送入AdlinkBridge供前端显示
    - 支持时域、频域、其他类型分类
    """
    
    def __init__(self):
        super().__init__("ResultSink", category="Sink")
        
        self.add_input("List-XY")
        self.add_select_option(
            "类型",
            items=["时域", "频域", "FREE"],
            default="时域"
        )
        self.add_text_input_option("名称", default="New Plot")
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data = self.get_interface("List-XY")
            
            if not self._validate_input_data(i_data):
                return
            
            t = self.get_option("类型")
            name = self.get_option("名称")
            
            # 提取数据（支持SignalData格式）
            data_value = self._extract_data(i_data)
            payload = {"name": name, "value": data_value}
            
            if t == "时域":
                adlink_bridge_instance.add_data_t(payload)
                self._logger.debug(f"已添加时域数据: {name}")
            elif t == "频域":
                adlink_bridge_instance.add_data_p(payload)
                self._logger.debug(f"已添加频域数据: {name}")
            else:
                adlink_bridge_instance.add_data_xy(payload)
                self._logger.debug(f"已添加XY数据: {name}")
                
        except Exception as e:
            self._log_error(e, "结果收集")
            raise


class CSVSink(BaseBlock):
    """
    CSV文件保存器
    
    功能：
    - 将数据保存为CSV文件
    - 支持追加模式
    - 支持表头控制
    """
    
    def __init__(self):
        super().__init__("CSVSink", category="Sink")
        
        self.add_input("I-List-XY")
        self.add_text_input_option("文件路径", default="output.csv")
        self.add_checkbox_option("追加模式", default=False)
        self.add_checkbox_option("包含表头", default=True)
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data = self.get_interface("I-List-XY")
            
            if not self._validate_input_data(i_data):
                return
            
            file_path = self.get_option("文件路径")
            mode = 'a' if self.get_option("追加模式") else 'w'
            header = self.get_option("包含表头") and mode == 'w'
            
            # 使用辅助方法提取数据
            data = self._extract_data(i_data)
            x = data.get("x", [])
            y = data.get("y", [])
            
            if not x:
                x = list(range(len(y)))
            
            df = pd.DataFrame({"x": x, "y": y})
            
            # 确保输出目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            df.to_csv(file_path, mode=mode, header=header, index=False)
            
            self._logger.debug(f"数据已保存: {file_path}")
            
        except Exception as e:
            self._log_error(e, "CSV保存")
            raise


# ==================== Chart Viewer Blocks ====================

class BaseChartViewer(BaseBlock):
    """
    图表查看器基类
    
    功能：
    - 生成交互式HTML图表
    - 支持多种图表类型
    - 可配置样式和交互
    """
    
    def __init__(self, name: str, category: str = "Sink", default_type: str = "line"):
        super().__init__(name, category=category)
        
        self.add_input("I-List-XY")
        self.add_text_input_option(
            "文件路径",
            default=f"{name.lower().replace('viewer', '')}_chart.html"
        )
        self.add_text_input_option("标题", default=f"{name.replace('Viewer', '')} Chart")
        self.add_integer_option("宽度 (px)", default=1200, min_val=800, max_val=2000)
        self.add_integer_option("高度 (px)", default=700, min_val=500, max_val=1200)
        self.add_checkbox_option("显示网格", default=True)
        self.add_checkbox_option("显示图例", default=True)
        self.add_checkbox_option("启用滚轮缩放", default=True)
        self.add_checkbox_option("启用拖拽平移", default=True)
        
        self.chart_type = default_type
    
    def _generate_chart(self):
        """生成图表"""
        try:
            i_data = self.get_interface("I-List-XY")
            
            if not self._validate_input_data(i_data):
                return
            
            # 使用辅助方法提取数据
            raw_data = self._extract_data(i_data)
            x_raw = raw_data.get("x", [])
            y_raw = raw_data.get("y", [])
            
            if len(y_raw) == 0:
                self._logger.warning("Y数据为空")
                return
            
            # 根据图表类型处理数据
            if self.chart_type == 'bar':
                if len(x_raw) == 0 or len(x_raw) != len(y_raw):
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
                    self._logger.warning("Scatter图需要完整的X/Y坐标")
                    return
                x_data = x_raw
                y_data = y_raw
                border_color = 'rgba(59, 130, 246, 0.4)'
                background_color = '#3b82f6'
                tension = 0
                point_radius = 5
                
            else:  # line
                if len(x_raw) == 0 or len(x_raw) != len(y_raw):
                    x_data = list(range(len(y_raw)))
                else:
                    x_data = x_raw
                y_data = y_raw
                border_color = '#3b82f6'
                background_color = 'rgba(59, 130, 246, 0.05)'
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
                "Time (s)" if typ in ["channel", "filtered", "envelope"] else
                "Frequency (Hz)" if typ == "fourier" else
                "Order" if typ == "order" else "X"
            )
            
            # 生成HTML
            html_content = self._generate_html(
                title, width, height, x_label,
                x_json, y_json, border_color, background_color,
                tension, point_radius, show_grid, show_legend,
                enable_wheel, enable_drag
            )
            
            # 确保输出目录存在
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self._logger.info(f"图表已生成: {file_path}")
            
        except Exception as e:
            self._log_error(e, "图表生成")
            raise
    
    def _generate_html(
        self, title, width, height, x_label,
        x_json, y_json, border_color, background_color,
        tension, point_radius, show_grid, show_legend,
        enable_wheel, enable_drag
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


class LineChartViewer(BaseChartViewer):
    """交互式折线图查看器"""
    
    def __init__(self):
        super().__init__("LineChartViewer", default_type="line")
    
    def on_compute(self):
        self._generate_chart()


class BarChartViewer(BaseChartViewer):
    """交互式柱状图查看器"""
    
    def __init__(self):
        super().__init__("BarChartViewer", default_type="bar")
    
    def on_compute(self):
        self._generate_chart()


class ScatterChartViewer(BaseChartViewer):
    """交互式散点图查看器"""
    
    def __init__(self):
        super().__init__("ScatterChartViewer", default_type="scatter")
    
    def on_compute(self):
        self._generate_chart()


# ==================== Communication Blocks ====================

class MQTTPublisher(BaseBlock):
    """
    MQTT数据发布（当前为模拟打印）
    
    功能：
    - 连接MQTT Broker
    - 发布数据到指定主题
    """
    
    def __init__(self):
        super().__init__("MQTTPublisher", category="Communication")
        
        self.add_input("I-Any")
        self.add_text_input_option("Broker地址", default="broker.hivemq.com")
        self.add_text_input_option("端口", default="1883")
        self.add_text_input_option("主题", default="daq/data")
        self.add_text_input_option("用户名 (可选)", default="")
        self.add_text_input_option("密码 (可选)", default="")
    
    def on_compute(self):
        """执行计算"""
        try:
            i_data = self.get_interface("I-Any")
            
            if i_data is None:
                return
            
            broker = self.get_option("Broker地址")
            port = int(self.get_option("端口"))
            topic = self.get_option("主题")
            username = self.get_option("用户名 (可选)") or None
            password = self.get_option("密码 (可选)") or None
            
            # 模拟发布
            payload = json.dumps(i_data)
            self._logger.info(f"MQTT 已模拟发布: {payload[:200]}")
            
            # TODO: 实现真实的MQTT发布
            # import paho.mqtt.client as mqtt
            # client = mqtt.Client()
            # if username:
            #     client.username_pw_set(username, password)
            # client.connect(broker, port)
            # client.publish(topic, payload)
            # client.disconnect()
            
        except Exception as e:
            self._log_error(e, "MQTT发布")
            raise


class Logger(BaseBlock):
    """
    控制台日志输出（调试用）
    
    功能：
    - 输出数据到控制台
    - 支持自定义前缀
    """
    
    def __init__(self):
        super().__init__("Logger", category="Debug")
        
        self.add_input("I-Any")
        self.add_text_input_option("前缀", default="LOG:")
    
    def on_compute(self):
        """执行计算"""
        try:
            data = self.get_interface("I-Any")
            prefix = self.get_option("前缀")
            self._logger.info(f"{prefix} {data}")
            
        except Exception as e:
            self._log_error(e, "日志输出")
            raise


# ==================== 注册列表 ====================

daq_blocks = [
    # Source
    ChannelSource(),
    TurbineSimulator(),
    CSVReader(),
    ConstantSource(),
    
    # Conversion
    XYSplitter(),
    XYMerger(),
    
    # Processing
    SignalFilter(),
    EnvelopeDetector(),
    TimeWindow(),
    
    # Transform
    FFT(),
    
    # Analysis
    SpectralAverager(),
    Stats(),
    
    # Order Analysis
    RPMTrackedFFT(),
    OrderMap(),
    TachoToRPM(),
    AngularResampler(),
    
    # Sink
    ResultSink(),
    CSVSink(),
    
    # Chart Viewers
    LineChartViewer(),
    BarChartViewer(),
    ScatterChartViewer(),
    
    # Communication
    MQTTPublisher(),
    
    # Debug
    Logger(),
]


# ==================== 导出接口 ====================

__all__ = [
    "DAQConfig",
    "SignalMetadata",
    "SignalData",
    "DomainType",
    "DataType",
    "DAQError",
    "DataValidationError",
    "ProcessingError",
    "ConfigError",
    "AdlinkBridge",
    "BaseBlock",
    "daq_blocks",
]