import os
import time
import sqlite3
from fastapi import FastAPI, Request, Response, HTTPException, APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
DB_PATH = "vfs.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 初始化数据库
with get_db() as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS files (
            user_id TEXT, path TEXT, type INTEGER, 
            content BLOB, mtime INTEGER,
            PRIMARY KEY (user_id, path)
        )
    """)

api = APIRouter(prefix="/api/vfs")

# 核心：路径标准化函数
def normalize_path(path: str):
    p = "/" + path.strip("/")
    return "/" if p == "//" else p

@api.get("/stat")
async def stat(user_id: str, path: str):
    path = normalize_path(path)
    with get_db() as conn:
        row = conn.execute("SELECT type, mtime, length(content) as size FROM files WHERE user_id = ? AND path = ?", (user_id, path)).fetchone()
        
        # 根目录不存在则初始化
        if not row and path == "/":
            now = int(time.time()*1000)
            conn.execute("INSERT INTO files (user_id, path, type, mtime) VALUES (?, ?, 2, ?)", (user_id, "/", now))
            conn.commit()
            return {"type": 2, "mtime": now, "ctime": now, "size": 0}
            
        if not row: raise HTTPException(status_code=404)
        
        return {
            "type": int(row["type"]), 
            "mtime": int(row["mtime"]), 
            "ctime": int(row["mtime"]), 
            "size": int(row["size"] or 0)
        }

@api.get("/readdir")
async def readdir(user_id: str, path: str):
    path = normalize_path(path)
    # 搜索前缀：如果路径是 / 则匹配 /^/.* 
    search_prefix = path if path.endswith("/") else path + "/"
    
    with get_db() as conn:
        cursor = conn.execute("SELECT path, type FROM files WHERE user_id = ? AND path LIKE ? AND path != ?", 
                             (user_id, search_prefix + '%', path))
        res = []
        for row in cursor:
            full_path = row["path"]
            # 提取下一级名称
            name = full_path[len(search_prefix):].split('/')[0]
            if name:
                res.append([name, int(row["type"])])
        
        # 去重（防止路径深度匹配导致重复）
        unique_res = {tuple(x) for x in res}
        return [list(x) for x in unique_res]

@api.get("/read")
async def read(user_id: str, path: str):
    path = normalize_path(path)
    with get_db() as conn:
        row = conn.execute(
            "SELECT type, content FROM files WHERE user_id = ? AND path = ?",
            (user_id, path)
        ).fetchone()
        if not row or row["type"] != 1:
            raise HTTPException(status_code=404)
        return Response(
            content=row["content"] or b"",
            media_type="application/octet-stream"
        )
    
@api.post("/write")
async def write(user_id: str, path: str, request: Request):
    path = normalize_path(path)
    content = await request.body()
    with get_db() as conn:
        now = int(time.time()*1000)
        conn.execute("""
            INSERT INTO files (user_id, path, type, content, mtime) VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(user_id, path) DO UPDATE SET content=excluded.content, mtime=excluded.mtime
        """, (user_id, path, content, now))
        conn.commit()
    return {"ok": True}

@api.post("/mkdir")
async def mkdir(user_id: str, path: str):
    path = normalize_path(path)
    with get_db() as conn:
        now = int(time.time()*1000)
        conn.execute("INSERT OR IGNORE INTO files (user_id, path, type, mtime) VALUES (?, ?, 2, ?)", (user_id, path, now))
        conn.commit()
    return {"ok": True}

@api.delete("/delete")
async def delete(user_id: str, path: str):
    path = normalize_path(path)
    with get_db() as conn:
        # 递归删除
        conn.execute("DELETE FROM files WHERE user_id = ? AND (path = ? OR path LIKE ?)", (user_id, path, path + '/%'))
        conn.commit()
    return {"ok": True}

app.include_router(api)
app.mount("/vscode", StaticFiles(directory="web/vscode"), name="vscode")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open("web/index.html", "r", encoding="utf-8") as f:
        return f.read()


app.mount("/", StaticFiles(directory="web"), name="web")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)