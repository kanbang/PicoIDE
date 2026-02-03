
from typing import Optional

import pandas as pd
from flow.block import BaseBlock


class CsvRecorderBlock(BaseBlock):
    NAME = "CsvRecorder"
    CATEGORY = "Output"

    def __init__(self):
        super().__init__()
        # 定义配置项
        self.add_text_input_option("file_path", "data_log.csv")
        self.add_checkbox_option("auto_timestamp", True)

        # 定义输入接口
        self.add_input("data")  # 接收要保存的字典或字符串
        self._fieldnames = None

    async def on_compute(self, execution_id: str = None):
        data = self.get_interface("data")
        if data is None:
            return

        filename = self.get_option("file_path")

        # 统一格式为字典
        if not isinstance(data, dict):
            row = {"value": data}
        else:
            row = data.copy()

        # 自动添加时间戳
        if self.get_option("auto_timestamp"):
            row["_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # 初始化表头（如果首次）
        if self._fieldnames is None:
            self._fieldnames = list(row.keys())

        # 定义写入函数（处理写或追加，包括header）
        def write_csv(full_path: Path, mode: str):
            if mode == "w":
                with open(full_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self._fieldnames)
                    writer.writeheader()
                    writer.writerow(row)
            else:  # "a"
                with open(full_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=self._fieldnames)
                    writer.writerow(row)

        # 使用基类方法（非唯一，追加模式）
        self._write_file(
            filename=filename,
            write_func=write_csv,
            execution_id=execution_id,
            description="CSV数据文件",
            unique=False,
            mode="a",
        )
        
class CSVSink(BaseBlock):
    """
    CSV文件保存器

    功能：
    - 将数据保存为CSV文件
    - 支持追加模式
    - 支持表头控制
    """

    NAME = "CSVSink"
    CATEGORY = "输出"

    def __init__(self):
        super().__init__()

        self.add_input("I-List-XY")
        self.add_text_input_option("文件路径", default="output.csv")
        self.add_checkbox_option("追加模式", default=False)
        self.add_checkbox_option("包含表头", default=True)

    async def on_compute(self, execution_id: Optional[str] = None):
        """执行计算"""
        try:
            i_data = self.get_interface("I-List-XY")

            if not self._validate_input_data(i_data):
                return

            file_path = self.get_option("文件路径")
            mode = "a" if self.get_option("追加模式") else "w"
            header = self.get_option("包含表头") and mode == "w"

            # 直接从SignalData格式中提取数据
            inner = i_data.get("data", {})
            x = inner.get("x", [])
            y = inner.get("y", [])

            # 如果x为空但y不为空，生成索引作为x
            if not x and y:
                x = list(range(len(y)))

            df = pd.DataFrame({"x": x, "y": y})

            # 使用通用文件写入方法
            def write_csv(full_path):
                df.to_csv(full_path, mode=mode, header=header, index=False)
                self._logger.debug(f"数据已保存: {full_path}")

            self._write_file(
                filename=file_path,
                write_func=write_csv,
                execution_id=execution_id,
                description="CSV数据文件",
            )

        except Exception as e:
            self._log_error(e, "CSV保存")
            raise

