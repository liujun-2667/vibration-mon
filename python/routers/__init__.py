from fastapi import APIRouter

from .devices import router as devices_router
from .sampling import router as sampling_router
from .alarms import router as alarms_router
from .analysis import router as analysis_router
from .data import router as data_router
from .reports import router as reports_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(devices_router, prefix="/devices", tags=["设备管理"])
api_router.include_router(sampling_router, prefix="/sampling", tags=["采样参数"])
api_router.include_router(alarms_router, prefix="/alarms", tags=["报警管理"])
api_router.include_router(analysis_router, prefix="/analysis", tags=["数据分析"])
api_router.include_router(data_router, prefix="/data", tags=["数据管理"])
api_router.include_router(reports_router, prefix="/reports", tags=["报告生成"])

__all__ = [
    "api_router",
    "devices_router",
    "sampling_router",
    "alarms_router",
    "analysis_router",
    "data_router",
    "reports_router",
]
