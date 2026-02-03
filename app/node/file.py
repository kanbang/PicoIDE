import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
from flow.block import BaseBlock


class CsvDictWriterBlock(BaseBlock):
    """
    通用 CSV 字典写入块（支持追加模式）

    功能：
    - 将输入数据（字符串或字典）记录到 CSV 文件
    - 支持自动添加时间戳
    - 支持追加模式（append_mode）
    - 支持表头控制（include_header）
    """

    NAME = "CsvDictWriter"
    CATEGORY = "输出"

    def __init__(self):
        super().__init__()
        # 配置项
        self.add_text_input_option("file_path", "data_log.csv")
        self.add_checkbox_option("auto_timestamp", True)
        self.add_checkbox_option("append_mode", False)      # 新增
        self.add_checkbox_option("include_header", True)    # 新增

        # 输入接口
        self.add_input("data")
        self._fieldnames: Optional[list] = None

    async def on_compute(self, execution_id: Optional[str] = None):
        data = self.get_interface("data")
        if data is None:
            self._logger.debug("No data to write, skipping.")
            return

        # 统一转换为字典
        row: Dict[str, Any] = data if isinstance(data, dict) else {"value": data}

        # 自动添加时间戳
        if self.get_option("auto_timestamp"):
            row["_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # 更新表头（动态扩展）
        if self._fieldnames is None:
            self._fieldnames = list(row.keys())
        else:
            new_fields = [k for k in row if k not in self._fieldnames]
            if new_fields:
                self._fieldnames.extend(new_fields)
                self._logger.debug(f"Added new fields: {new_fields}")

        filename = self.get_option("file_path")
        append_mode = self.get_option("append_mode")
        write_mode = "a" if append_mode else "w"
        include_header = self.get_option("include_header")

        def write_csv(full_path: Path, mode: str):
            # 是否需要写表头
            header_needed = (
                include_header
                and (mode == "w" or not full_path.exists())
            )

            with open(full_path, mode, newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self._fieldnames)
                if header_needed:
                    writer.writeheader()
                writer.writerow(row)

        try:
            self._write_file(
                filename=filename,
                write_func=write_csv,
                execution_id=execution_id,
                description="CSV data file",
                unique=False,
                mode=write_mode,
            )
        except Exception as e:
            self._log_error(e, "CSV dict write")
            raise


class CsvXyWriterBlock(BaseBlock):
    """
    X-Y 数据 CSV 写入块（支持追加模式）

    功能：
    - 将 SignalData 格式的 x-y 数据保存为 CSV
    - 支持追加模式（append_mode）
    - 支持表头控制（include_header）
    """

    NAME = "CsvXyWriter"
    CATEGORY = "输出"

    def __init__(self):
        super().__init__()
        # 输入
        self.add_input("xy_data")

        # 配置项
        self.add_text_input_option("file_path", "output.csv")
        self.add_checkbox_option("append_mode", False)
        self.add_checkbox_option("include_header", True)

    def _validate_input_data(self, data: Optional[Dict[str, Any]]) -> bool:
        if data is None:
            self._logger.debug("No input data, skipping.")
            return False
        inner = data.get("data", {})
        if not isinstance(inner.get("x"), list) or not isinstance(inner.get("y"), list):
            self._logger.warning("Invalid xy_data format: x and y must be lists.")
            return False
        return True

    async def on_compute(self, execution_id: Optional[str] = None):
        data = self.get_interface("xy_data")
        if not self._validate_input_data(data):
            return

        filename = self.get_option("file_path")
        append_mode = self.get_option("append_mode")
        write_mode = "a" if append_mode else "w"
        include_header = self.get_option("include_header")

        # 提取 x/y
        inner = data.get("data", {})
        x = inner.get("x", [])
        y = inner.get("y", [])
        if not x and y:
            x = list(range(len(y)))

        df = pd.DataFrame({"x": x, "y": y})

        def write_csv(full_path: Path, mode: str):
            # Pandas 的 header 逻辑与 append 一致
            header = include_header and mode == "w"
            df.to_csv(
                full_path,
                mode=mode,
                header=header,
                index=False,
                encoding="utf-8",
            )
            self._logger.debug(f"Data saved to: {full_path}")

        try:
            self._write_file(
                filename=filename,
                write_func=write_csv,
                execution_id=execution_id,
                description="XY CSV data file",
                unique=False,
                mode=write_mode,
            )
        except Exception as e:
            self._log_error(e, "XY CSV write")
            raise