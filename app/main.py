"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-21 09:59:22
LastEditors: zhai
LastEditTime: 2026-01-21 16:15:39
"""

"""
Descripttion:
version: 0.x
Author: zhai
Date: 2026-01-07 14:28:11
LastEditors: zhai
LastEditTime: 2026-01-21 14:23:20
"""

"""
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-07 14:28:11
LastEditors: zhai
LastEditTime: 2026-01-12 19:40:30
"""
"""
主应用程序
"""
import sys
import asyncio
import platform

# Windows 上使用 SelectorEventLoop 避免 zmq 警告（必须在任何 zmq 操作之前设置）
if platform.system() == "Windows":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from flow.blocks_manager import register_static_blocks
from db import init_db, close_db, ensure_root_directory
from routes.vfs.views import router as vfs_router
from routes.engine.views import router as engine_router
from routes.flow.views import router as flow_router
from node import IOT_BLOCKS_ALL, DAQ_BLOCKS_ALL

DB_PATH = "vfs.db"
USER_ID = "default"


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


if __name__ == "__main__":

    # ==================== 初始化注册 ====================

    # 应用启动时注册所有预定义的业务类型
    register_static_blocks("WAVE", DAQ_BLOCKS_ALL)
    register_static_blocks("IOT", IOT_BLOCKS_ALL)

    uvicorn.run(app, host="0.0.0.0", port=8000)
