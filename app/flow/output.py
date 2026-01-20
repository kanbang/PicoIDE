"""
输出文件管理器 - 工业级文件管理系统

功能：
- 统一的输出目录管理
- 执行ID关联的文件追踪
- 文件生命周期管理
- 自动清理机制
- 数据库持久化

Author: PicoIDE Team
Version: 2.1.0
"""

import logging
import uuid
import asyncio
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock
from flow.setting import settings
import time


logger = logging.getLogger(__name__)


# ==================== 输出文件管理器 ====================


class OutputFileManager:
    """
    输出文件管理器（数据库版本）

    功能：
    - 管理执行ID和文件的关联
    - 提供文件注册接口
    - 自动清理机制
    - 数据库持久化
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
        self._lock = Lock()

        # 导入全局配置
        self.settings = settings

        logger.info("输出文件管理器已初始化（数据库版本）")

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
        logger.info(f"创建执行ID: {execution_id}")
        return execution_id

    async def register_file(
        self,
        execution_id: str,
        filename: str,
        block_name: str,
        block_id: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        注册输出文件（保存到数据库）

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
        from db import Output

        # 生成文件ID
        file_id = f"{execution_id}_{uuid.uuid4().hex[:8]}"

        # 构建完整文件路径
        file_path = self.settings.OUTPUT_DIR / filename

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 获取文件类型
        file_type = self.settings.FILE_TYPE_MAP.get(
            file_path.suffix.lower(), "unknown"
        )

        # 保存到数据库
        await Output.create(
            file_id=file_id,
            execution_id=execution_id,
            filename=filename,
            file_path=str(file_path),
            file_type=file_type,
            file_size=0,  # 文件大小在文件写入后更新
            block_name=block_name,
            block_id=block_id,
            description=description,
            metadata=metadata or {},
            is_deleted=False,
        )

        logger.info(f"注册文件: {filename} (ID: {file_id}, 执行: {execution_id})")
        return file_id

    async def update_file_size(self, file_id: str, file_size: int) -> None:
        """
        更新文件大小

        Args:
            file_id: 文件ID
            file_size: 文件大小
        """
        from db import Output

        await Output.filter(file_id=file_id).update(file_size=file_size)

    async def get_execution_files(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        获取执行关联的所有文件

        Args:
            execution_id: 执行ID

        Returns:
            文件信息列表
        """
        from db import Output

        outputs = await Output.filter(
            execution_id=execution_id,
            is_deleted=False
        ).all()

        return [
            {
                "file_id": o.file_id,
                "execution_id": o.execution_id,
                "filename": o.filename,
                "file_path": o.file_path,
                "file_type": o.file_type,
                "file_size": o.file_size,
                "created_at": o.created_at.isoformat(),
                "block_name": o.block_name,
                "block_id": o.block_id,
                "description": o.description,
                "metadata": o.metadata,
                "can_open": o.file_type in self.settings.BROWSER_OPENABLE,
                "can_download": True,
            }
            for o in outputs
        ]

    async def get_all_files(
        self,
        execution_id: Optional[str] = None,
        file_type: Optional[str] = None,
        is_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取所有文件（支持过滤和分页）

        Args:
            execution_id: 执行ID过滤
            file_type: 文件类型过滤
            is_deleted: 是否包含已删除文件
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            文件信息列表
        """
        from db import Output

        query = Output.filter(is_deleted=is_deleted)

        if execution_id:
            query = query.filter(execution_id=execution_id)

        if file_type:
            query = query.filter(file_type=file_type)

        outputs = await query.order_by("-created_at").limit(limit).offset(offset).all()

        return [
            {
                "file_id": o.file_id,
                "execution_id": o.execution_id,
                "filename": o.filename,
                "file_path": o.file_path,
                "file_type": o.file_type,
                "file_size": o.file_size,
                "created_at": o.created_at.isoformat(),
                "block_name": o.block_name,
                "block_id": o.block_id,
                "description": o.description,
                "metadata": o.metadata,
                "can_open": o.file_type in self.settings.BROWSER_OPENABLE,
                "can_download": True,
            }
            for o in outputs
        ]

    async def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息

        Args:
            file_id: 文件ID

        Returns:
            文件信息，如果不存在则返回None
        """
        from db import Output

        output = await Output.filter(file_id=file_id).first()

        if not output:
            return None

        return {
            "file_id": output.file_id,
            "execution_id": output.execution_id,
            "filename": output.filename,
            "file_path": output.file_path,
            "file_type": output.file_type,
            "file_size": output.file_size,
            "created_at": output.created_at.isoformat(),
            "block_name": output.block_name,
            "block_id": output.block_id,
            "description": output.description,
            "metadata": output.metadata,
            "can_open": output.file_type in self.settings.BROWSER_OPENABLE,
            "can_download": True,
        }

    async def get_file_path(self, file_id: str) -> Optional[Path]:
        """
        获取文件路径

        Args:
            file_id: 文件ID

        Returns:
            文件路径，如果不存在则返回None
        """
        from db import Output

        output = await Output.filter(file_id=file_id).first()

        if not output:
            return None

        return Path(output.file_path)

    async def delete_file(self, file_id: str, soft_delete: bool = True) -> bool:
        """
        删除文件

        Args:
            file_id: 文件ID
            soft_delete: 是否软删除（默认True）

        Returns:
            是否删除成功
        """
        from db import Output

        output = await Output.filter(file_id=file_id).first()

        if not output:
            return False

        if soft_delete:
            # 软删除：只标记
            await Output.filter(file_id=file_id).update(
                is_deleted=True,
                deleted_at=datetime.now()
            )
            logger.info(f"软删除文件: {output.filename}")
        else:
            # 物理删除
            file_path = Path(output.file_path)
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"物理删除文件: {output.filename}")
            except Exception as e:
                logger.error(f"删除文件失败: {output.filename}, {e}")
                return False

            # 删除数据库记录
            await output.delete()

        return True

    async def cleanup_old_files(self, max_age_hours: int = None) -> Dict[str, Any]:
        """
        清理旧文件（软删除）

        Args:
            max_age_hours: 最大文件年龄（小时），None表示使用默认值

        Returns:
            清理结果
        """
        from db import Output

        if max_age_hours is None:
            max_age_hours = self.settings.FILE_RETENTION_HOURS

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        # 软删除超过保留时间的文件
        deleted_count = await Output.filter(
            created_at__lt=cutoff_time,
            is_deleted=False
        ).update(
            is_deleted=True,
            deleted_at=datetime.now()
        )

        logger.info(f"清理完成，软删除了 {deleted_count} 个文件")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "max_age_hours": max_age_hours,
        }

    async def cleanup_soft_deleted_files(self, max_age_days: int = None) -> Dict[str, Any]:
        """
        物理清理已软删除的文件

        Args:
            max_age_days: 软删除文件保留天数，None表示使用默认值

        Returns:
            清理结果
        """
        from db import Output

        if max_age_days is None:
            max_age_days = self.settings.SOFT_DELETE_RETENTION_DAYS

        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        # 获取需要物理删除的文件
        outputs_to_delete = await Output.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_time
        ).all()

        deleted_count = 0
        for output in outputs_to_delete:
            file_path = Path(output.file_path)
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"物理删除文件: {output.filename}")
            except Exception as e:
                logger.error(f"物理删除文件失败: {output.filename}, {e}")
                continue

            # 删除数据库记录
            await output.delete()
            deleted_count += 1

        logger.info(f"物理清理完成，删除了 {deleted_count} 个软删除文件")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "max_age_days": max_age_days,
        }

    async def cleanup_old_executions(self, max_age_days: int = None) -> Dict[str, Any]:
        """
        清理旧执行记录

        Args:
            max_age_days: 执行记录保留天数，None表示使用默认值

        Returns:
            清理结果
        """
        from db import Execution

        if max_age_days is None:
            max_age_days = self.settings.EXECUTION_RETENTION_DAYS

        cutoff_time = datetime.now() - timedelta(days=max_age_days)

        # 删除超过保留时间的执行记录
        deleted_count = await Execution.filter(
            start_time__lt=cutoff_time
        ).delete()

        logger.info(f"清理完成，删除了 {deleted_count} 个旧执行记录")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "max_age_days": max_age_days,
        }

    def _start_cleanup_task(self):
        """启动清理任务"""
        import threading

        def cleanup_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            while True:
                try:
                    time.sleep(self.settings.CLEANUP_INTERVAL_HOURS * 3600)

                    # 运行清理任务
                    loop.run_until_complete(self._run_cleanup_tasks())
                except Exception as e:
                    logger.error(f"清理任务失败: {e}")

        thread = threading.Thread(target=cleanup_task, daemon=True)
        thread.start()
        logger.info("清理任务已启动")

    async def _run_cleanup_tasks(self):
        """运行所有清理任务"""
        try:
            # 1. 软删除旧文件
            await self.cleanup_old_files()

            # 2. 物理删除软删除文件
            await self.cleanup_soft_deleted_files()

            # 3. 清理旧执行记录
            await self.cleanup_old_executions()
        except Exception as e:
            logger.error(f"清理任务执行失败: {e}")


# 全局实例
output_file_manager = OutputFileManager.get_instance()