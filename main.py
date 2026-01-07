'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-07 14:28:11
LastEditors: zhai
LastEditTime: 2026-01-07 14:38:33
'''
import os
import time
import sqlite3
from fastapi import FastAPI, Request, Response, HTTPException, APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()

# --- 数据库初始化 ---
DB_PATH = "vfs.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                user_id TEXT,
                path TEXT,
                type INTEGER, -- 1: File, 2: Directory
                content BLOB,
                mtime INTEGER,
                PRIMARY KEY (user_id, path)
            )
        """)
        conn.execute("INSERT OR IGNORE INTO files (user_id, path, type, mtime) VALUES ('default', '/', 2, ?)", (int(time.time()*1000),))

init_db()

# --- 文件系统 API ---
api = APIRouter(prefix="/api/vfs")

@api.get("/stat")
async def stat(user_id: str, path: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT type, mtime, length(content) FROM files WHERE user_id = ? AND path = ?", (user_id, path)).fetchone()
        if not row: raise HTTPException(status_code=404)
        return {"type": row[0], "mtime": row[1], "ctime": row[1], "size": row[2] or 0}

@api.get("/readdir")
async def readdir(user_id: str, path: str):
    with sqlite3.connect(DB_PATH) as conn:
        prefix = path if path.endswith('/') else path + '/'
        cursor = conn.execute("SELECT path, type FROM files WHERE user_id = ? AND path LIKE ? AND path != ?", (user_id, prefix + '%', path))
        items = [[p[len(prefix):].split('/')[0], t] for p, t in cursor if p[len(prefix):].split('/')[0]]
        return list(set(map(tuple, items)))

@api.get("/read")
async def read(user_id: str, path: str):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT content FROM files WHERE user_id = ? AND path = ?", (user_id, path)).fetchone()
        if not row: raise HTTPException(status_code=404)
        return Response(content=row[0] or b"", media_type="application/octet-stream")

@api.post("/write")
async def write(user_id: str, path: str, request: Request):
    content = await request.body()
    with sqlite3.connect(DB_PATH) as conn:
        now = int(time.time()*1000)
        conn.execute("""
            INSERT INTO files (user_id, path, type, content, mtime) VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(user_id, path) DO UPDATE SET content=excluded.content, mtime=excluded.mtime
        """, (user_id, path, content, now))
    return {"ok": True}

@api.post("/mkdir")
async def mkdir(user_id: str, path: str):
    with sqlite3.connect(DB_PATH) as conn:
        now = int(time.time()*1000)
        conn.execute("INSERT OR IGNORE INTO files (user_id, path, type, mtime) VALUES (?, ?, 2, ?)", (user_id, path, now))
    return {"ok": True}

@api.delete("/delete")
async def delete(user_id: str, path: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM files WHERE user_id = ? AND (path = ? OR path LIKE ?)", (user_id, path, path + '/%'))
    return {"ok": True}

app.include_router(api)

# --- 网页资源托管 ---

# 1. 挂载 vscode 核心库路径 (对应 web/vscode 文件夹)
app.mount("/vscode", StaticFiles(directory="web/vscode"), name="vscode")

# 2. 根目录返回 web/index.html
@app.get("/")
async def index():
    return FileResponse("web/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)