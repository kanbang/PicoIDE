'''
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-07 14:28:11
LastEditors: zhai
LastEditTime: 2026-04-28 14:19:54
'''

"""
主应用程序
"""
import multiprocessing
import sys
import asyncio
import platform
from pathlib import Path

# Windows 上使用 SelectorEventLoop 避免 zmq 警告（必须在任何 zmq 操作之前设置）
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from flow.blocks_manager import register_static_blocks
from db import init_db, close_db, ensure_root_directory
from routes.vfs.views import router as vfs_router
from routes.engine.views import router as engine_router
from routes.flow.views import router as flow_router
from node import IOT_BLOCKS_ALL, DAQ_BLOCKS_ALL, AI_LLM_BLOCKS_ALL

DB_PATH = "vfs.db"
USER_ID = "default"



def GetBaseDir():
    if getattr(sys, "frozen", False):
        # 如果是被打包的应用程序，使用 sys.executable 获取路径
        root_path = Path(sys.executable).resolve()
    else:
        # 如果是普通的脚本，使用 __file__
        root_path = Path(__file__).resolve()

    print("PROJECT_ROOT:", root_path)
    print("BASE_DIR:", root_path.parent)

    return root_path.parent


# 前端静态文件目录
WEB_DIST_DIR = GetBaseDir() / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(DB_PATH)
    print("Database initialized")
    yield
    await close_db()
    print("Database closed")


app = FastAPI(lifespan=lifespan)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(vfs_router)
app.include_router(engine_router)
app.include_router(flow_router)

# ==================== 前端静态文件托管 ====================

# 挂载 assets 目录（JS、CSS 等静态资源）
assets_dir = WEB_DIST_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# SPA 回退：所有非 API 路由返回 index.html
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """
    处理 SPA 路由：
    - 如果请求的是静态文件（存在），返回该文件
    - 否则返回 index.html（让前端路由处理）
    """
    # API 路由由各自的 router 处理，这里不会匹配
    file_path = WEB_DIST_DIR / full_path

    # 如果是文件且存在，直接返回
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))

    # 否则返回 index.html（SPA 路由）
    index_path = WEB_DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))

    return {"error": "Frontend not built. Run 'npm run build' in web/ directory"}


if __name__ == "__main__":

    # ==================== 初始化注册 ====================

    # 应用启动时注册所有预定义的业务类型
    register_static_blocks("WAVE", DAQ_BLOCKS_ALL)
    register_static_blocks("IOT", IOT_BLOCKS_ALL)
    register_static_blocks("AI", AI_LLM_BLOCKS_ALL)

    # Windows 上需要调用 freeze_support 来支持多进程（尤其是当使用 PyInstaller 打包时）
    multiprocessing.freeze_support()

    uvicorn.run(app, host="0.0.0.0", port=8000)
