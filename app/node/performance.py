"""
PicoIDE DAQ Performance Optimization Module

功能：
- 计算结果缓存
- 向量化计算优化
- 并行处理
- 内存管理
- 性能监控

使用方法：
    from performance import PerformanceCache, VectorizedOperations
    
    # 使用缓存
    cache = PerformanceCache()
    result = cache.get_or_compute("key", lambda: expensive_computation())
    
    # 使用向量化操作
    ops = VectorizedOperations()
    result = ops.apply_filter(signal, filter_coeffs)
"""

import time
import hashlib
import logging
import threading
from functools import wraps, lru_cache
from typing import Callable, Any, Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


logger = logging.getLogger(__name__)


# ==================== 性能监控 ====================

@dataclass
class PerformanceMetrics:
    """性能指标"""
    compute_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    total_calls: int = 0
    
    def get_cache_hit_rate(self) -> float:
        """获取缓存命中率"""
        if self.total_calls == 0:
            return 0.0
        return self.cache_hits / self.total_calls
    
    def get_avg_compute_time(self) -> float:
        """获取平均计算时间"""
        if self.cache_misses == 0:
            return 0.0
        return self.compute_time / self.cache_misses
    
    def reset(self) -> None:
        """重置指标"""
        self.compute_time = 0.0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_calls = 0


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self, name: str = "PerformanceMonitor"):
        self.name = name
        self.metrics = PerformanceMetrics()
        self._lock = threading.Lock()
    
    def record_compute(self, duration: float) -> None:
        """记录计算"""
        with self._lock:
            self.metrics.compute_time += duration
            self.metrics.cache_misses += 1
            self.metrics.total_calls += 1
    
    def record_cache_hit(self) -> None:
        """记录缓存命中"""
        with self._lock:
            self.metrics.cache_hits += 1
            self.metrics.total_calls += 1
    
    def get_metrics(self) -> PerformanceMetrics:
        """获取指标"""
        with self._lock:
            return PerformanceMetrics(
                compute_time=self.metrics.compute_time,
                cache_hits=self.metrics.cache_hits,
                cache_misses=self.metrics.cache_misses,
                total_calls=self.metrics.total_calls
            )
    
    def log_summary(self) -> None:
        """记录摘要"""
        metrics = self.get_metrics()
        logger.info(f"[{self.name}] 性能摘要:")
        logger.info(f"  总调用次数: {metrics.total_calls}")
        logger.info(f"  缓存命中: {metrics.cache_hits}")
        logger.info(f"  缓存未命中: {metrics.cache_misses}")
        logger.info(f"  缓存命中率: {metrics.get_cache_hit_rate():.2%}")
        logger.info(f"  平均计算时间: {metrics.get_avg_compute_time():.4f}s")


def monitor_performance(monitor: PerformanceMonitor):
    """
    性能监控装饰器
    
    Args:
        monitor: 性能监控器实例
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.record_compute(duration)
                return result
            except Exception as e:
                logger.error(f"函数 {func.__name__} 执行失败: {e}")
                raise
        return wrapper
    return decorator


# ==================== 缓存系统 ====================

class PerformanceCache:
    """
    性能缓存
    
    功能：
    - 基于键值对的缓存
    - 自动过期
    - 内存限制
    - 缓存统计
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        ttl: float = 3600.0,
        enable: bool = True
    ):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数
            ttl: 生存时间（秒）
            enable: 是否启用缓存
        """
        self.max_size = max_size
        self.ttl = ttl
        self.enable = enable
        
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._monitor = PerformanceMonitor("PerformanceCache")
        
        logger.info(f"性能缓存已初始化: max_size={max_size}, ttl={ttl}s")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        # 简单的哈希方法
        key_str = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或过期则返回None
        """
        if not self.enable:
            return None
        
        with self._lock:
            if key not in self._cache:
                return None
            
            value, timestamp = self._cache[key]
            
            # 检查是否过期
            if time.time() - timestamp > self.ttl:
                del self._cache[key]
                return None
            
            self._monitor.record_cache_hit()
            return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        if not self.enable:
            return
        
        with self._lock:
            # 检查缓存大小
            if len(self._cache) >= self.max_size:
                # 删除最旧的条目
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            
            self._cache[key] = (value, time.time())
    
    def get_or_compute(self, key: str, compute_func: Callable[[], Any]) -> Any:
        """
        获取缓存值或计算新值
        
        Args:
            key: 缓存键
            compute_func: 计算函数
            
        Returns:
            缓存值或计算结果
        """
        # 尝试从缓存获取
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        
        # 计算新值
        start_time = time.time()
        try:
            value = compute_func()
            duration = time.time() - start_time
            
            # 存入缓存
            self.set(key, value)
            self._monitor.record_compute(duration)
            
            return value
        except Exception as e:
            logger.error(f"计算函数执行失败: {e}")
            raise
    
    def compute_with_args(
        self,
        compute_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        使用参数计算并缓存结果
        
        Args:
            compute_func: 计算函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            计算结果
        """
        key = self._generate_key(*args, **kwargs)
        return self.get_or_compute(key, lambda: compute_func(*args, **kwargs))
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            logger.info("缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl": self.ttl,
                "enabled": self.enable,
                **self._monitor.get_metrics().__dict__
            }
    
    def log_stats(self) -> None:
        """记录缓存统计"""
        stats = self.get_stats()
        logger.info(f"缓存统计:")
        logger.info(f"  大小: {stats['size']}/{stats['max_size']}")
        logger.info(f"  TTL: {stats['ttl']}s")
        logger.info(f"  启用: {stats['enabled']}")
        self._monitor.log_summary()


# ==================== 向量化操作 ====================

class VectorizedOperations:
    """
    向量化操作
    
    功能：
    - 高效的信号处理
    - 批量计算
    - 内存优化
    """
    
    def __init__(self):
        self._monitor = PerformanceMonitor("VectorizedOperations")
    
    @monitor_performance
    def apply_filter(
        self,
        signal: np.ndarray,
        b: np.ndarray,
        a: np.ndarray = np.array([1.0])
    ) -> np.ndarray:
        """
        应用滤波器（向量化）
        
        Args:
            signal: 输入信号
            b: 分子系数
            a: 分母系数
            
        Returns:
            滤波后的信号
        """
        from scipy import signal as sp_signal
        
        # 使用filtfilt进行零相位滤波
        return sp_signal.filtfilt(b, a, signal)
    
    @monitor_performance
    def compute_fft(
        self,
        signal: np.ndarray,
        fs: float,
        window: Optional[np.ndarray] = None,
        normalize: bool = True
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算FFT（向量化）
        
        Args:
            signal: 输入信号
            fs: 采样率
            window: 窗口函数
            normalize: 是否归一化
            
        Returns:
            (频率, 幅值)
        """
        # 应用窗口
        if window is not None:
            signal = signal * window
        
        # 计算FFT
        N = len(signal)
        fft_vals = np.fft.rfft(signal)
        
        # 归一化
        if normalize:
            mag = np.abs(fft_vals) / N * 2.0
        else:
            mag = np.abs(fft_vals)
        
        # 频率轴
        freqs = np.fft.rfftfreq(N, 1.0 / fs)
        
        return freqs, mag
    
    @monitor_performance
    def compute_rms(
        self,
        signal: np.ndarray,
        axis: Optional[int] = None
    ) -> Union[float, np.ndarray]:
        """
        计算RMS（向量化）
        
        Args:
            signal: 输入信号
            axis: 计算轴
            
        Returns:
            RMS值
        """
        return np.sqrt(np.mean(signal ** 2, axis=axis))
    
    @monitor_performance
    def compute_peak_to_peak(
        self,
        signal: np.ndarray,
        axis: Optional[int] = None
    ) -> Union[float, np.ndarray]:
        """
        计算峰峰值（向量化）
        
        Args:
            signal: 输入信号
            axis: 计算轴
            
        Returns:
            峰峰值
        """
        return np.ptp(signal, axis=axis)
    
    @monitor_performance
    def compute_statistics(
        self,
        signal: np.ndarray
    ) -> Dict[str, float]:
        """
        计算统计量（向量化）
        
        Args:
            signal: 输入信号
            
        Returns:
            统计量字典
        """
        return {
            "mean": float(np.mean(signal)),
            "std": float(np.std(signal)),
            "min": float(np.min(signal)),
            "max": float(np.max(signal)),
            "rms": float(np.sqrt(np.mean(signal ** 2))),
            "peak_to_peak": float(np.ptp(signal)),
            "skewness": float(self._compute_skewness(signal)),
            "kurtosis": float(self._compute_kurtosis(signal)),
        }
    
    def _compute_skewness(self, signal: np.ndarray) -> float:
        """计算偏度"""
        from scipy import stats
        return float(stats.skew(signal))
    
    def _compute_kurtosis(self, signal: np.ndarray) -> float:
        """计算峰度"""
        from scipy import stats
        return float(stats.kurtosis(signal))
    
    @monitor_performance
    def resample_signal(
        self,
        signal: np.ndarray,
        old_fs: float,
        new_fs: float
    ) -> np.ndarray:
        """
        重采样信号（向量化）
        
        Args:
            signal: 输入信号
            old_fs: 原采样率
            new_fs: 新采样率
            
        Returns:
            重采样后的信号
        """
        from scipy import signal as sp_signal
        
        # 计算重采样比例
        num = int(len(signal) * new_fs / old_fs)
        
        # 使用抗混叠重采样
        return sp_signal.resample(signal, num)
    
    @monitor_performance
    def apply_window(
        self,
        signal: np.ndarray,
        window_type: str = "hann"
    ) -> np.ndarray:
        """
        应用窗口函数（向量化）
        
        Args:
            signal: 输入信号
            window_type: 窗口类型
            
        Returns:
            加窗后的信号
        """
        n = len(signal)
        
        if window_type == "hann":
            window = np.hanning(n)
        elif window_type == "hamming":
            window = np.hamming(n)
        elif window_type == "blackman":
            window = np.blackman(n)
        elif window_type == "flattop":
            from scipy.signal import windows
            window = windows.flattop(n)
        else:
            window = np.ones(n)
        
        return signal * window
    
    @monitor_performance
    def compute_envelope(
        self,
        signal: np.ndarray
    ) -> np.ndarray:
        """
        计算包络（向量化）
        
        Args:
            signal: 输入信号
            
        Returns:
            包络信号
        """
        from scipy.signal import hilbert
        
        analytic = hilbert(signal)
        envelope = np.abs(analytic)
        
        return envelope
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return self._monitor.get_metrics().__dict__


# ==================== 并行处理 ====================

class ParallelProcessor:
    """
    并行处理器
    
    功能：
    - 多线程/多进程处理
    - 任务队列
    - 结果收集
    """
    
    def __init__(self, max_workers: int = 4):
        """
        初始化并行处理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.max_workers = max_workers
        self._monitor = PerformanceMonitor("ParallelProcessor")
        
        logger.info(f"并行处理器已初始化: max_workers={max_workers}")
    
    def map_parallel(
        self,
        func: Callable,
        items: List[Any],
        use_threads: bool = True
    ) -> List[Any]:
        """
        并行映射
        
        Args:
            func: 处理函数
            items: 数据项列表
            use_threads: 是否使用线程（否则使用进程）
            
        Returns:
            处理结果列表
        """
        from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
        
        start_time = time.time()
        
        try:
            Executor = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
            
            with Executor(max_workers=self.max_workers) as executor:
                results = list(executor.map(func, items))
            
            duration = time.time() - start_time
            self._monitor.record_compute(duration)
            
            return results
            
        except Exception as e:
            logger.error(f"并行处理失败: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        return self._monitor.get_metrics().__dict__


# ==================== 内存管理 ====================

class MemoryManager:
    """
    内存管理器
    
    功能：
    - 内存使用监控
    - 大数组优化
    - 内存池
    """
    
    def __init__(self):
        self._monitor = PerformanceMonitor("MemoryManager")
    
    def get_memory_usage(self) -> Dict[str, float]:
        """
        获取内存使用情况
        
        Returns:
            内存使用字典（MB）
        """
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        return {
            "rss": mem_info.rss / 1024 / 1024,  # 常驻集大小
            "vms": mem_info.vms / 1024 / 1024,  # 虚拟内存大小
            "percent": process.memory_percent(),  # 内存使用百分比
        }
    
    def optimize_array(
        self,
        arr: np.ndarray,
        dtype: Optional[np.dtype] = None
    ) -> np.ndarray:
        """
        优化数组内存
        
        Args:
            arr: 输入数组
            dtype: 目标数据类型
            
        Returns:
            优化后的数组
        """
        if dtype is not None:
            arr = arr.astype(dtype)
        
        # 确保数组是连续的
        if not arr.flags['C_CONTIGUOUS']:
            arr = np.ascontiguousarray(arr)
        
        return arr
    
    def log_memory_usage(self) -> None:
        """记录内存使用"""
        mem = self.get_memory_usage()
        logger.info(f"内存使用:")
        logger.info(f"  RSS: {mem['rss']:.2f} MB")
        logger.info(f"  VMS: {mem['vms']:.2f} MB")
        logger.info(f"  百分比: {mem['percent']:.2f}%")


# ==================== 全局实例 ====================

_global_cache: Optional[PerformanceCache] = None
_global_vectorized: Optional[VectorizedOperations] = None
_global_memory: Optional[MemoryManager] = None


def get_cache() -> PerformanceCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = PerformanceCache()
    return _global_cache


def get_vectorized_ops() -> VectorizedOperations:
    """获取全局向量化操作实例"""
    global _global_vectorized
    if _global_vectorized is None:
        _global_vectorized = VectorizedOperations()
    return _global_vectorized


def get_memory_manager() -> MemoryManager:
    """获取全局内存管理器实例"""
    global _global_memory
    if _global_memory is None:
        _global_memory = MemoryManager()
    return _global_memory


# ==================== 导出接口 ====================

__all__ = [
    "PerformanceMetrics",
    "PerformanceMonitor",
    "monitor_performance",
    "PerformanceCache",
    "VectorizedOperations",
    "ParallelProcessor",
    "MemoryManager",
    "get_cache",
    "get_vectorized_ops",
    "get_memory_manager",
]