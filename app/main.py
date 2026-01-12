'''
Descripttion: 
version: 0.x
Author: zhai
Date: 2026-01-07 14:28:11
LastEditors: zhai
LastEditTime: 2026-01-12 19:41:34
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
from fastapi.staticfiles import StaticFiles
import uvicorn

from db import init_db, close_db, ensure_root_directory
from routes.vfs import router as vfs_router
from routes.blocks import router as blocks_router
from routes.schemas import router as schemas_router

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

# 注册路由
app.include_router(vfs_router)
app.include_router(blocks_router)
app.include_router(schemas_router)


app.mount("/", StaticFiles(directory="../web-code", html=True), name="web")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
