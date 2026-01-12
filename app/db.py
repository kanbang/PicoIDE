'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-08 09:32:18
LastEditors: zhai
LastEditTime: 2026-01-08 09:53:01
'''
"""
数据库模块
负责 Tortoise ORM 初始化与模型定义
"""
import time
from tortoise import Tortoise, fields
from tortoise.models import Model


class File(Model):
    """文件模型"""
    user_id = fields.CharField(max_length=255)
    path = fields.CharField(max_length=1024)
    type = fields.IntField()  # 1=file, 2=dir
    content = fields.BinaryField(null=True)
    mtime = fields.BigIntField()

    class Meta:
        table = "files"
        unique_together = (("user_id", "path"),)


class Schema(Model):
    """Schema 模型"""
    user_id = fields.CharField(max_length=255)
    name = fields.CharField(max_length=255)
    schema_data = fields.JSONField(null=True)
    mtime = fields.BigIntField()

    class Meta:
        table = "schemas"


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


async def ensure_root_directory(user_id: str):
    """确保根目录存在"""
    if not await File.filter(user_id=user_id, path="/").exists():
        await File.create(
            user_id=user_id,
            path="/",
            type=2,
            mtime=int(time.time() * 1000),
        )
