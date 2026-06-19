import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import (
    CommandResponse,
)
from routers import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("启动振动监测系统后端服务...")
    yield
    logger.info("关闭振动监测系统后端服务...")


app = FastAPI(
    title="振动监测系统API",
    description="基于FastAPI的工业设备振动监测与分析系统后端",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, device_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[device_id] = websocket
        logger.info(f"设备 {device_id} 已连接")

    def disconnect(self, device_id: int):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"设备 {device_id} 已断开连接")

    async def send_personal_message(self, message: dict, device_id: int):
        if device_id in self.active_connections:
            await self.active_connections[device_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)


manager = ConnectionManager()

app.include_router(api_router)


@app.get("/", tags=["系统"])
async def root():
    return CommandResponse(
        success=True,
        message="振动监测系统后端服务运行正常",
        data={
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "endpoints": {
                "devices": "/api/v1/devices",
                "sampling": "/api/v1/sampling",
                "alarms": "/api/v1/alarms",
                "analysis": "/api/v1/analysis",
                "reports": "/api/v1/reports",
                "data": "/api/v1/data",
                "diagnosis": "/api/v1/diagnosis",
            },
        },
    )


@app.get("/health", tags=["系统"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_connections": len(manager.active_connections),
    }


@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    """
    WebSocket实时数据传输接口
    """
    await manager.connect(device_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"收到设备 {device_id} 数据: {data.get('type', 'unknown')}")
            await websocket.send_json(
                {
                    "type": "ack",
                    "timestamp": datetime.now().isoformat(),
                    "device_id": device_id,
                    "status": "received",
                }
            )
    except WebSocketDisconnect:
        manager.disconnect(device_id)
    except Exception as e:
        logger.error(f"设备 {device_id} WebSocket错误: {e}")
        manager.disconnect(device_id)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "服务器内部错误",
            "data": None,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
