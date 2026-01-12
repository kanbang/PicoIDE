'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-07 14:28:11
LastEditors: zhai
LastEditTime: 2026-01-12 18:17:59
'''
"""
主应用程序
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
import uvicorn

from db import init_db, close_db, ensure_root_directory
from services import (
    normalize_path,
    stat_file,
    list_dir,
    read_file,
    write_file,
    mkdir,
    delete_path,
)

DB_PATH = "vfs.db"
USER_ID = "default"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(DB_PATH)
    await ensure_root_directory(USER_ID)
    print("Database initialized")
    yield
    await close_db()
    print("Database closed")


app = FastAPI(lifespan=lifespan)


@app.get("/api/vfs/stat")
async def stat(path: str):
    path = normalize_path(path)
    try:
        return await stat_file(USER_ID, path)
    except Exception:
        raise HTTPException(404, "File not found")


@app.get("/api/vfs/readdir")
async def readdir(path: str):
    path = normalize_path(path)
    return await list_dir(USER_ID, path)


@app.get("/api/vfs/read")
async def read(path: str):
    path = normalize_path(path)
    try:
        content = await read_file(USER_ID, path)
        return Response(content=content, media_type="application/octet-stream")
    except Exception:
        raise HTTPException(404, "Not a file")


@app.post("/api/vfs/write")
async def write(path: str, request: Request):
    path = normalize_path(path)
    content = await request.body()
    await write_file(USER_ID, path, content)
    return {"ok": True}


@app.post("/api/vfs/mkdir")
async def mkdir_api(path: str):
    path = normalize_path(path)
    await mkdir(USER_ID, path)
    return {"ok": True}


@app.delete("/api/vfs/delete")
async def delete(path: str):
    path = normalize_path(path)
    await delete_path(USER_ID, path)
    return {"ok": True}


app.mount("/", StaticFiles(directory="web-code", html=True), name="web")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
