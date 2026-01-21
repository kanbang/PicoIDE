"""
VFS 业务逻辑（最终稳定版）
"""
import time
from typing import Optional, Dict, List
from tortoise.exceptions import DoesNotExist
from db import File


# ---------- utils ----------

def normalize_path(path: str) -> str:
    p = "/" + path.strip("/")
    return "/" if p == "//" else p


async def ensure_root_directory_exists(user_id: str, business: str):
    """确保根目录存在（按需创建）"""
    if not await File.filter(user_id=user_id, business=business, path="/").exists():
        await File.create(
            user_id=user_id,
            business=business,
            path="/",
            type=2,
            mtime=int(time.time() * 1000),
        )


# ---------- query ----------

async def get_file(user_id: str, path: str, business: str) -> Optional[File]:
    """
    只用于读取，不用于 save
    """
    return await File.filter(user_id=user_id, path=path, business=business).first()


async def stat_file(user_id: str, path: str, business: str) -> dict:
    # 确保根目录存在
    if path == "/":
        await ensure_root_directory_exists(user_id, business)

    file = await get_file(user_id, path, business)
    if not file:
        raise DoesNotExist

    return {
        "type": file.type,
        "mtime": file.mtime,
        "ctime": file.mtime,
        "size": len(file.content) if file.content else 0,
    }


async def list_dir(user_id: str, path: str, business: str) -> List[list]:
    # 确保根目录存在
    await ensure_root_directory_exists(user_id, business)

    search_prefix = path if path.endswith("/") else path + "/"

    files = await File.filter(
        user_id=user_id,
        path__startswith=search_prefix,
        business=business,
    ).exclude(path=path)

    direct_children: Dict[str, int] = {}

    for file in files:
        relative = file.path[len(search_prefix):]
        if "/" not in relative and relative:
            if relative not in direct_children or file.type > direct_children[relative]:
                direct_children[relative] = file.type

    return [[name, t] for name, t in direct_children.items()]


async def read_file(user_id: str, path: str, business: str) -> bytes:
    file = await get_file(user_id, path, business)
    if not file:
        return b""
    if file.type != 1:
        raise DoesNotExist
    return file.content or b""


# ---------- write ----------

async def write_file(user_id: str, path: str, content: bytes, business: str):
    """
    写文件：禁止使用 save()
    """
    # 确保根目录存在
    await ensure_root_directory_exists(user_id, business)

    now = int(time.time() * 1000)

    updated = await File.filter(
        user_id=user_id,
        path=path,
        business=business,
    ).update(
        type=1,
        content=content,
        mtime=now,
    )

    if not updated:
        await File.create(
            user_id=user_id,
            path=path,
            type=1,
            content=content,
            mtime=now,
            business=business,
        )


async def mkdir(user_id: str, path: str, business: str):
    """
    创建目录：禁止使用 save()
    """
    # 确保根目录存在
    await ensure_root_directory_exists(user_id, business)

    now = int(time.time() * 1000)

    updated = await File.filter(
        user_id=user_id,
        path=path,
        business=business,
    ).update(
        type=2,
        content=None,
        mtime=now,
    )

    if not updated:
        await File.create(
            user_id=user_id,
            path=path,
            type=2,
            mtime=now,
            business=business,
        )


async def delete_path(user_id: str, path: str, business: str):
    """
    删除文件 / 目录
    """
    await File.filter(
        user_id=user_id,
        path__startswith=path + "/",
        business=business,
    ).delete()

    await File.filter(
        user_id=user_id,
        path=path,
        business=business,
    ).delete()
