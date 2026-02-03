from .utils import SseLogger, ConsoleLogger, ConstantBlock
from .file import CsvDictWriterBlock, CsvXyWriterBlock
from .iot import IOT_BLOCKS
from .daq import DAQ_BLOCKS
from .chart import (
    LineChartViewer,
    BarChartViewer,
    ScatterChartViewer,
    TrajectoryChartViewer,
    OrderMapChartViewer,
)


file_blocks = [
    CsvDictWriterBlock,
    CsvXyWriterBlock,
]

utils_blocks = [
    ConstantBlock,
    SseLogger,
    ConsoleLogger,
]

chart_blocks = [
    LineChartViewer,
    BarChartViewer,
    ScatterChartViewer,
    TrajectoryChartViewer,
    OrderMapChartViewer,
]

# 数据采集相关 blocks
DAQ_BLOCKS_ALL = [
    *DAQ_BLOCKS,
    *utils_blocks,
    *file_blocks,
    *chart_blocks,
]

# 物联网相关 blocks
IOT_BLOCKS_ALL = [*IOT_BLOCKS, *utils_blocks, *file_blocks, LineChartViewer]


__all__ = [
    "DAQ_BLOCKS_ALL",
    "IOT_BLOCKS_ALL",
]
