"""
输出文件管理器 - 工业级文件管理系统

功能：
- 统一的输出目录管理
- 执行ID关联的文件追踪
- 文件生命周期管理
- 自动清理机制

Author: PicoIDE Team
Version: 1.0.0
"""

import logging
import uuid
import json
from typing import Any, Dict, List, Optional, Set
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from threading import Lock
import time


logger = logging.getLogger(__name__)


# ==================== 配置 ====================


class OutputConfig:
    """输出配置"""
    
    # 统一的输出目录
    OUTPUT_DIR = Path("./output")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 临时目录
    TEMP_DIR = Path("./temp")
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # 文件类型映射
    FILE_TYPE_MAP = {
        ".html": "html",
        ".csv": "csv",
        ".json": "json",
        ".txt": "text",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".pdf": "pdf",
        ".xlsx": "excel",
        ".xls": "excel",
    }
    
    # 浏览器可打开的文件类型
    BROWSER_OPENABLE = {"html", "json", "txt"}
    
    # 文件保留时间（小时）
    FILE_RETENTION_HOURS = 24
    
    # 最大文件数量
    MAX_FILES_PER_EXECUTION = 100


@dataclass
class OutputFileInfo:
    """输出文件信息"""
    
    file_id: str  # 唯一ID
    execution_id: str  # 关联的执行ID
    filename: str  # 文件名
    file_path: Path  # 完整路径
    file_type: str  # 文件类型
    file_size: int  # 文件大小（字节）
    created_at: str  # 创建时间
    block_name: str  # 生成此文件的Block名称
    block_id: str  # Block ID
    description: Optional[str] = None  # 描述
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_id": self.file_id,
            "execution_id": self.execution_id,
            "filename": self.filename,
            "file_path": str(self.file_path),
            "file_type": self.file_type,
            "file_size": self.file_size,
            "created_at": self.created_at,
            "block_name": self.block_name,
            "block_id": self.block_id,
            "description": self.description,
            "metadata": self.metadata,
            "can_open": self.file_type in OutputConfig.BROWSER_OPENABLE,
            "can_download": True,
        }


@dataclass
class ExecutionInfo:
    """执行信息"""
    
    execution_id: str  # 执行ID
    start_time: str  # 开始时间
    end_time: Optional[str] = None  # 结束时间
    duration: Optional[float] = None  # 执行时长（秒）
    file_ids: List[str] = field(default_factory=list)  # 生成的文件ID列表
    status: str = "running"  # 状态
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


# ==================== 输出文件管理器 ====================


class OutputFileManager:
    """
    输出文件管理器
    
    功能：
    - 管理执行ID和文件的关联
    - 提供文件注册接口
    - 自动清理机制
    - 线程安全
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化管理器"""
        self._executions: Dict[str, ExecutionInfo] = {}
        self._files: Dict[str, OutputFileInfo] = {}
        self._lock = Lock()
        
        # 确保目录存在
        OutputConfig.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        OutputConfig.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.info("输出文件管理器已初始化")
        
        # 启动清理任务
        self._start_cleanup_task()
    
    @classmethod
    def get_instance(cls) -> 'OutputFileManager':
        """获取单例实例"""
        return cls()
    
    def create_execution_id(self) -> str:
        """
        创建新的执行ID
        
        Returns:
            执行ID
        """
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        
        with self._lock:
            execution_info = ExecutionInfo(
                execution_id=execution_id,
                start_time=datetime.now().isoformat(),
                status="running"
            )
            self._executions[execution_id] = execution_info
        
        logger.info(f"创建执行ID: {execution_id}")
        return execution_id
    
    def register_file(
        self,
        execution_id: str,
        filename: str,
        block_name: str,
        block_id: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        注册输出文件
        
        Args:
            execution_id: 执行ID
            filename: 文件名
            block_name: Block名称
            block_id: Block ID
            description: 描述
            metadata: 元数据
            
        Returns:
            文件ID
        """
        # 生成文件ID
        file_id = f"{execution_id}_{uuid.uuid4().hex[:8]}"
        
        # 构建完整文件路径
        file_path = OutputConfig.OUTPUT_DIR / filename
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 获取文件类型
        file_type = OutputConfig.FILE_TYPE_MAP.get(
            file_path.suffix.lower(), "unknown"
        )
        
        # 创建文件信息
        file_info = OutputFileInfo(
            file_id=file_id,
            execution_id=execution_id,
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            file_size=0,  # 文件大小在文件写入后更新
            created_at=datetime.now().isoformat(),
            block_name=block_name,
            block_id=block_id,
            description=description,
            metadata=metadata or {}
        )
        
        with self._lock:
            # 保存文件信息
            self._files[file_id] = file_info
            
            # 关联到执行
            if execution_id in self._executions:
                self._executions[execution_id].file_ids.append(file_id)
        
        logger.info(f"注册文件: {filename} (ID: {file_id}, 执行: {execution_id})")
        return file_id
    
    def update_file_size(self, file_id: str, file_size: int) -> None:
        """
        更新文件大小
        
        Args:
            file_id: 文件ID
            file_size: 文件大小
        """
        with self._lock:
            if file_id in self._files:
                self._files[file_id].file_size = file_size
    
    def get_execution_files(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        获取执行关联的所有文件
        
        Args:
            execution_id: 执行ID
            
        Returns:
            文件信息列表
        """
        with self._lock:
            if execution_id not in self._executions:
                return []
            
            file_ids = self._executions[execution_id].file_ids
            return [
                self._files[fid].to_dict()
                for fid in file_ids
                if fid in self._files
            ]
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """
        获取所有文件
        
        Returns:
            文件信息列表
        """
        with self._lock:
            return [
                f.to_dict()
                for f in self._files.values()
            ]
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件信息，如果不存在则返回None
        """
        with self._lock:
            if file_id in self._files:
                return self._files[file_id].to_dict()
            return None
    
    def get_file_path(self, file_id: str) -> Optional[Path]:
        """
        获取文件路径
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件路径，如果不存在则返回None
        """
        with self._lock:
            if file_id in self._files:
                return self._files[file_id].file_path
            return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            是否删除成功
        """
        with self._lock:
            if file_id not in self._files:
                return False
            
            file_info = self._files[file_id]
            
            # 删除物理文件
            try:
                if file_info.file_path.exists():
                    file_info.file_path.unlink()
                    logger.info(f"已删除文件: {file_info.filename}")
            except Exception as e:
                logger.error(f"删除文件失败: {file_info.filename}, {e}")
                return False
            
            # 从执行关联中移除
            execution_id = file_info.execution_id
            if execution_id in self._executions:
                if file_id in self._executions[execution_id].file_ids:
                    self._executions[execution_id].file_ids.remove(file_id)
            
            # 删除文件信息
            del self._files[file_id]
            
            return True
    
    def cleanup_old_files(self, max_age_hours: int = None) -> Dict[str, Any]:
        """
        清理旧文件
        
        Args:
            max_age_hours: 最大文件年龄（小时），None表示使用默认值
            
        Returns:
            清理结果
        """
        if max_age_hours is None:
            max_age_hours = OutputConfig.FILE_RETENTION_HOURS
        
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0
        
        with self._lock:
            # 收集要删除的文件ID
            file_ids_to_delete = []
            
            for file_id, file_info in self._files.items():
                file_age = current_time - datetime.fromisoformat(
                    file_info.created_at
                ).timestamp()
                
                if file_age > max_age_seconds:
                    file_ids_to_delete.append(file_id)
            
            # 删除文件
            for file_id in file_ids_to_delete:
                if self.delete_file(file_id):
                    deleted_count += 1
        
        logger.info(f"清理完成，删除了 {deleted_count} 个文件")
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "max_age_hours": max_age_hours,
        }
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        import threading
        
        def cleanup_task():
            while True:
                try:
                    time.sleep(3600)  # 每小时清理一次
                    self.cleanup_old_files()
                except Exception as e:
                    logger.error(f"清理任务失败: {e}")
        
        thread = threading.Thread(target=cleanup_task, daemon=True)
        thread.start()
        logger.info("清理任务已启动")


# 全局实例
output_file_manager = OutputFileManager.get_instance()