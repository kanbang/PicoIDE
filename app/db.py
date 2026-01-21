'''
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-08 09:32:18
LastEditors: zhai
LastEditTime: 2026-01-21 12:25:28
'''
"""
数据库模块
负责 Tortoise ORM 初始化与模型定义
"""
import time
import uuid
from tortoise import Tortoise, fields
from tortoise.models import Model


class File(Model):
    """文件模型"""
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user_id = fields.CharField(max_length=255)
    business = fields.CharField(max_length=50, default="")
    path = fields.CharField(max_length=1024)
    type = fields.IntField()  # 1=file, 2=dir
    content = fields.BinaryField(null=True)
    mtime = fields.BigIntField()

    class Meta:
        table = "files"
        unique_together = (("user_id", "business", "path"),)


class Flow(Model):
    """Flow 模型"""
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user_id = fields.CharField(max_length=255)
    business = fields.CharField(max_length=50, default="daq")
    name = fields.CharField(max_length=255)
    flow = fields.JSONField(null=True)
    mtime = fields.BigIntField()

    class Meta:
        table = "flows"
        unique_together = (("user_id", "business", "name"),)


class Execution(Model):
    """执行记录模型"""
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    execution_id = fields.CharField(max_length=64, unique=True, index=True)
    user_id = fields.CharField(max_length=255, index=True)

    # 执行来源
    source = fields.CharField(max_length=20)  # 'direct', 'saved', 'tag'
    flow_id = fields.UUIDField(null=True)
    tag = fields.CharField(max_length=128, null=True, index=True)

    # 脚本信息
    scripts_path = fields.CharField(max_length=512, null=True)
    scripts_hash = fields.CharField(max_length=64, null=True, index=True)

    # 执行状态
    status = fields.CharField(max_length=20, default="running")  # running, completed, failed, cancelled
    result = fields.TextField(null=True)

    # 执行统计
    total_nodes = fields.IntField(default=0)
    executed_nodes = fields.IntField(default=0)
    failed_nodes = fields.IntField(default=0)
    execution_time = fields.FloatField(default=0.0)

    # 时间戳
    start_time = fields.DatetimeField(auto_now_add=True)
    end_time = fields.DatetimeField(null=True)

    # 元数据
    metadata = fields.JSONField(null=True)

    class Meta:
        table = "executions"
        indexes = [
            ("user_id", "start_time"),
            ("status", "start_time"),
            ("user_id", "tag"),
            ("scripts_hash", "start_time"),
            ("flow_id", "scripts_hash"),
        ]


class Output(Model):
    """输出文件模型"""
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    file_id = fields.CharField(max_length=128, unique=True, index=True)
    execution_id = fields.CharField(max_length=64, index=True)

    # 文件信息
    filename = fields.CharField(max_length=512)
    file_path = fields.CharField(max_length=1024)
    file_type = fields.CharField(max_length=50)
    file_size = fields.BigIntField(default=0)

    # 生成者信息
    block_name = fields.CharField(max_length=255)
    block_id = fields.CharField(max_length=255)

    # 描述和元数据
    description = fields.TextField(null=True)
    metadata = fields.JSONField(null=True)

    # 状态
    is_deleted = fields.BooleanField(default=False)

    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "outputs"
        indexes = [
            ("execution_id", "created_at"),
            ("file_type", "created_at"),
            ("is_deleted", "created_at"),
        ]


async def init_db(db_path: str):
    """初始化数据库"""
    await Tortoise.init(
        db_url=f"sqlite://{db_path}",
        modules={"models": ["db"]},
    )
    await Tortoise.generate_schemas()


async def close_db():
    """关闭数据库"""
    await Tortoise.close_connections()


async def ensure_root_directory(user_id: str, business: str):
    """确保根目录存在"""
    if not await File.filter(user_id=user_id, business=business, path="/").exists():
        await File.create(
            user_id=user_id,
            business=business,
            path="/",
            type=2,
            mtime=int(time.time() * 1000),
        )
