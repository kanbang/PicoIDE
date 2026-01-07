import os
import time
import sqlite3
from fastapi import FastAPI, Request, Response, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
DB_PATH = "vfs.db"
USER_ID = "default"  # 单实例模式，固定用户


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# 初始化数据库
with get_db() as conn:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files (
            user_id TEXT, path TEXT, type INTEGER, 
            content BLOB, mtime INTEGER,
            PRIMARY KEY (user_id, path)
        )
    """
    )

api = APIRouter(prefix="/api/vfs")


def normalize_path(path: str):
    p = "/" + path.strip("/")
    return "/" if p == "//" else p


@api.get("/stat")
async def stat(path: str):
    path = normalize_path(path)
    with get_db() as conn:
        row = conn.execute(
            "SELECT type, mtime, length(content) as size FROM files WHERE user_id = ? AND path = ?",
            (USER_ID, path),
        ).fetchone()
        if not row and path == "/":
            now = int(time.time() * 1000)
            conn.execute(
                "INSERT INTO files (user_id, path, type, mtime) VALUES (?, ?, 2, ?)",
                (USER_ID, "/", now),
            )
            conn.commit()
            return {"type": 2, "mtime": now, "ctime": now, "size": 0}
        if not row:
            raise HTTPException(status_code=404)
        return {
            "type": int(row["type"]),
            "mtime": int(row["mtime"]),
            "ctime": int(row["mtime"]),
            "size": int(row["size"] or 0),
        }


@api.get("/readdir")
async def readdir(path: str):
    path = normalize_path(path)
    search_prefix = path if path.endswith("/") else path + "/"
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT path, type FROM files WHERE user_id = ? AND path LIKE ? AND path != ?",
            (USER_ID, search_prefix + "%", path),
        )
        res = []
        for row in cursor:
            full_path = row["path"]
            name = full_path[len(search_prefix) :].split("/")[0]
            if name:
                res.append([name, int(row["type"])])
        unique_res = {tuple(x) for x in res}
        return [list(x) for x in unique_res]


@api.get("/read")
async def read(path: str):
    path = normalize_path(path)
    with get_db() as conn:
        row = conn.execute(
            "SELECT type, content FROM files WHERE user_id = ? AND path = ?",
            (USER_ID, path),
        ).fetchone()
        if not row or row["type"] != 1:
            raise HTTPException(status_code=404)
        return Response(
            content=row["content"] or b"", media_type="application/octet-stream"
        )


@api.post("/write")
async def write(path: str, request: Request):
    path = normalize_path(path)
    content = await request.body()
    with get_db() as conn:
        now = int(time.time() * 1000)
        conn.execute(
            """
            INSERT INTO files (user_id, path, type, content, mtime) VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(user_id, path) DO UPDATE SET content=?, mtime=?
        """,
            (USER_ID, path, content, now, content, now),
        )
        conn.commit()
    return {"ok": True}


@api.post("/mkdir")
async def mkdir(path: str):
    path = normalize_path(path)
    with get_db() as conn:
        now = int(time.time() * 1000)
        conn.execute(
            "INSERT OR IGNORE INTO files (user_id, path, type, mtime) VALUES (?, ?, 2, ?)",
            (USER_ID, path, now),
        )
        conn.commit()
    return {"ok": True}


@api.delete("/delete")
async def delete(path: str):
    path = normalize_path(path)
    with get_db() as conn:
        conn.execute(
            "DELETE FROM files WHERE user_id = ? AND (path = ? OR path LIKE ?)",
            (USER_ID, path, path + "/%"),
        )
        conn.commit()
    return {"ok": True}


app.include_router(api)

# 挂载静态文件（包括 index.html 和 vfs-extension）
app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
