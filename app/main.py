'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-07 14:28:11
LastEditors: zhai
LastEditTime: 2026-01-21 14:14:54
'''
'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-07 14:28:11
LastEditors: zhai
LastEditTime: 2026-01-12 19:40:30
'''
"""
主应用程序
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from flow.blocks_manager import register_static_blocks
from node.daq import DAQ_BLOCKS
from db import init_db, close_db, ensure_root_directory
from routes.vfs.views import router as vfs_router
from routes.engine.views import router as engine_router
from routes.flow.views import router as flow_router

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
    register_static_blocks("WAVE", DAQ_BLOCKS)


    uvicorn.run(app, host="0.0.0.0", port=8000)
