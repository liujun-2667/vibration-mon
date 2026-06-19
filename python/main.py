import os
import sys
import asyncio
import logging
import random
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

push_tasks: dict[int, asyncio.Task] = {}


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
                "monitor": "/api/v1/monitor",
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


async def _ws_sender(websocket: WebSocket, queue: asyncio.Queue):
    """统一负责向某个 WebSocket 发送消息,避免并发 send 导致帧错乱。"""
    try:
        while True:
            message = await queue.get()
            if message is None:
                break
            await websocket.send_json(message)
    except Exception as e:
        logger.debug(f"ws_sender 退出: {e}")


def _device_simulator(device_id: int):
    from signal_simulator import SignalSimulator, SampleRate, FaultType, Severity

    fault_map = {
        1: FaultType.NORMAL,
        2: FaultType.MISALIGNMENT,
        3: FaultType.BEARING_FAULT,
        4: FaultType.GEAR_FAULT,
    }
    fault = fault_map.get(device_id, FaultType.BEARING_FAULT)
    return SignalSimulator(
        sample_rate=SampleRate.SR_10240,
        fault_type=fault,
        severity=Severity.MILD,
        rpm=3000,
        snr_db=30.0,
    )


async def _push_device_data(device_id: int, queue: asyncio.Queue):
    """连接建立后持续生成振动采集数据并推送到客户端,同时更新设备状态缓存。"""
    from signal_simulator import Severity
    from routers.monitor import update_device_cache, _compute_vibration_level, _compute_data_quality
    from routers.analysis import (
        _extract_time_domain_features,
        _extract_frequency_domain_features,
    )

    sim = _device_simulator(device_id)
    sample_rate = sim.sample_rate.value
    severity_cycle = [
        Severity.MILD,
        Severity.MILD,
        Severity.MODERATE,
        Severity.MODERATE,
        Severity.SEVERE,
    ]
    severity_base = {
        Severity.MILD: 90.0,
        Severity.MODERATE: 74.0,
        Severity.SEVERE: 50.0,
    }
    tick = 0

    try:
        while True:
            await asyncio.sleep(1.0)
            tick += 1
            current_severity = severity_cycle[tick % len(severity_cycle)]
            sim.set_severity(current_severity)

            _, signal = sim.generate(duration=0.2)
            ts = datetime.now()

            td = _extract_time_domain_features(signal)
            fd = _extract_frequency_domain_features(signal, sample_rate)

            # 健康指数:以严重度等级为基线(SEVERE 会跌破 60 触发告警),
            # 并叠加少量随机扰动与 RMS 超标惩罚,使曲线在等级切换时穿越 60。
            health = severity_base[current_severity] + random.uniform(-4.0, 4.0)
            health -= max(0.0, td.rms - 1.5) * 5.0
            health = max(35.0, min(100.0, round(health, 1)))

            vibration_level = _compute_vibration_level(td.rms)
            data_quality = _compute_data_quality(device_id)

            data_list = signal.tolist()
            payload = {
                "type": "vibration_data",
                "device_id": device_id,
                "timestamp": ts.isoformat(),
                "data": data_list,
                "sample_rate": sample_rate,
                "rms": round(td.rms, 4),
                "dominant_frequency": round(fd.dominant_frequency, 2),
                "health_index": health,
                "vibration_level": vibration_level,
                "data_quality": round(data_quality, 1) if data_quality is not None else None,
            }
            await queue.put(payload)
            update_device_cache(
                device_id,
                online=True,
                waveform={"timestamp": ts.isoformat(), "data": data_list, "sample_rate": sample_rate},
                rms=round(td.rms, 4),
                dominant_frequency=round(fd.dominant_frequency, 2),
                health_index=health,
                timestamp=ts,
            )
    except asyncio.CancelledError:
        logger.info(f"设备 {device_id} 推送任务已取消")
        raise
    except Exception as e:
        logger.error(f"设备 {device_id} 推送任务异常: {e}")


@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    """
    WebSocket实时数据传输接口,连接后持续推送该设备的振动采集数据
    (JSON包含 timestamp 和 data 字段,data 为浮点数组)。
    """
    await manager.connect(device_id, websocket)
    from routers.monitor import update_device_cache
    update_device_cache(device_id, online=True)

    send_queue: asyncio.Queue = asyncio.Queue()
    sender_task = asyncio.create_task(_ws_sender(websocket, send_queue))

    existing = push_tasks.get(device_id)
    if existing and not existing.done():
        existing.cancel()
    push_task = asyncio.create_task(_push_device_data(device_id, send_queue))
    push_tasks[device_id] = push_task

    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"收到设备 {device_id} 数据: {data.get('type', 'unknown')}")
            await send_queue.put({
                "type": "ack",
                "timestamp": datetime.now().isoformat(),
                "device_id": device_id,
                "status": "received",
            })
    except WebSocketDisconnect:
        manager.disconnect(device_id)
    except Exception as e:
        logger.error(f"设备 {device_id} WebSocket错误: {e}")
        manager.disconnect(device_id)
    finally:
        push_task.cancel()
        await send_queue.put(None)
        try:
            await asyncio.wait_for(sender_task, timeout=2)
        except Exception:
            sender_task.cancel()
        push_tasks.pop(device_id, None)
        update_device_cache(device_id, online=False)


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
