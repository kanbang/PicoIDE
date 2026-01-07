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
        # 查询所有匹配前缀的文件
        cursor = conn.execute(
            "SELECT path, type FROM files WHERE user_id = ? AND path LIKE ? AND path != ?",
            (USER_ID, search_prefix + "%", path),
        )

        # 收集直接子项
        direct_children = {}  # {name: type}

        for row in cursor:
            full_path = row["path"]
            relative_path = full_path[len(search_prefix):]

            # 只处理直接子项（不包含额外的 /）
            if "/" not in relative_path:
                name = relative_path
                if name:
                    file_type = int(row["type"])
                    # 如果已存在，优先保留目录类型
                    if name not in direct_children or file_type > direct_children[name]:
                        direct_children[name] = file_type

        # 转换为列表格式
        return [[name, file_type] for name, file_type in direct_children.items()]


@api.get("/read")
async def read(path: str):
    path = normalize_path(path)
    with get_db() as conn:
        row = conn.execute(
            "SELECT type, content FROM files WHERE user_id = ? AND path = ?",
            (USER_ID, path),
        ).fetchone()

        # 如果是 .vscode 或 .git 目录下的配置文件不存在，返回空内容
        if not row and ("/.vscode/" in path or "/.git/" in path):
            return Response(content=b"", media_type="application/octet-stream")

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
