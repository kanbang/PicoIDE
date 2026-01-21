'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-12 19:36:01
LastEditors: zhai
LastEditTime: 2026-01-21 11:22:08
'''
"""
VFS 虚拟文件系统路由
"""
from typing import Annotated
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import Response

from routes.dependencies import get_business
from services import (
    normalize_path,
    stat_file,
    list_dir,
    read_file,
    write_file,
    mkdir,
    delete_path,
)

USER_ID = "default"

router = APIRouter(prefix="/api/vfs", tags=["vfs"])


@router.get("/stat")
async def stat(path: str):
    path = normalize_path(path)
    try:
        return await stat_file(USER_ID, path)
    except Exception:
        raise HTTPException(404, "File not found")


@router.get("/readdir")
async def readdir(path: str, business: Annotated[str, Depends(get_business)]):
    print(f"[VFS] readdir called for business: {business}")
    path = normalize_path(path)
    return await list_dir(USER_ID, path)


@router.get("/read")
async def read(path: str):
    path = normalize_path(path)
    try:
        content = await read_file(USER_ID, path)
        return Response(content=content, media_type="application/octet-stream")
    except Exception:
        raise HTTPException(404, "Not a file")


@router.post("/write")
async def write(path: str, request: Request):
    path = normalize_path(path)
    content = await request.body()
    await write_file(USER_ID, path, content)
    return {"ok": True}


@router.post("/mkdir")
async def mkdir_api(path: str):
    path = normalize_path(path)
    await mkdir(USER_ID, path)
    return {"ok": True}


@router.delete("/delete")
async def delete(path: str):
    path = normalize_path(path)
    await delete_path(USER_ID, path)
    return {"ok": True}