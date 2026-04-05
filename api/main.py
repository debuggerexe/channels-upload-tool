"""
FastAPI 后端主入口
提供 REST API 和 WebSocket 服务
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 添加项目根目录到 Python 路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from api.routers import config, videos, upload
from api.websocket.log_handler import LogWebSocketManager

# WebSocket 管理器
ws_manager = LogWebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("🚀 FastAPI 服务启动")
    yield
    # 关闭时执行
    print("🛑 FastAPI 服务关闭")


app = FastAPI(
    title="微信视频号上传工具 API",
    description="为前端提供配置管理、视频扫描和上传控制接口",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js 开发服务器
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(config.router, prefix="/api/config", tags=["配置管理"])
app.include_router(videos.router, prefix="/api/videos", tags=["视频管理"])
app.include_router(upload.router, prefix="/api/upload", tags=["上传控制"])

# 静态文件服务 - 用于访问封面图
app.mount("/static", StaticFiles(directory=str(BASE_DIR)), name="static")


@app.get("/api/health")
async def health_check():
    """健康检查接口"""
    return {"status": "ok", "service": "wechat-video-uploader-api"}


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket 日志推送接口"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # 保持连接活跃，接收客户端心跳
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
