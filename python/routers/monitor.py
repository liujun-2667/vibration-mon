from datetime import datetime
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, status

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import CommandResponse

router = APIRouter()

device_state_cache: dict[int, dict] = {}


def _compute_status(online: bool, health_index: Optional[float]) -> str:
    if not online:
        return "offline"
    if health_index is not None and health_index < 60:
        return "alarm"
    return "online"


def _latest_analysis_for(device_id: int):
    try:
        from .analysis import analysis_results_db
        device_results = [r for r in analysis_results_db if r.device_id == device_id]
        if not device_results:
            return None
        return max(device_results, key=lambda r: r.timestamp)
    except Exception:
        return None


def init_cache_from_devices() -> None:
    try:
        from .devices import devices_db
    except Exception:
        return

    for device in devices_db:
        if device.id in device_state_cache:
            continue

        latest = _latest_analysis_for(device.id)
        online = device.status.value != "offline"
        health_index = latest.health_index if latest else None
        rms = latest.time_domain.rms if latest else None
        dominant_frequency = latest.frequency_domain.dominant_frequency if latest else None
        last_ts = latest.timestamp if latest else device.updated_at

        device_state_cache[device.id] = {
            "device_id": device.id,
            "device_name": device.name,
            "device_code": device.code,
            "online": online,
            "status": _compute_status(online, health_index),
            "health_index": health_index,
            "rms": rms,
            "dominant_frequency": dominant_frequency,
            "last_updated": last_ts.isoformat() if last_ts else None,
            "latest_waveform": None,
        }


def update_device_cache(
    device_id: int,
    *,
    online: Optional[bool] = None,
    waveform: Optional[dict] = None,
    rms: Optional[float] = None,
    dominant_frequency: Optional[float] = None,
    health_index: Optional[float] = None,
    status: Optional[str] = None,
) -> Optional[dict]:
    init_cache_from_devices()
    entry = device_state_cache.get(device_id)
    if entry is None:
        return None

    if online is not None:
        entry["online"] = online
    if waveform is not None:
        entry["latest_waveform"] = waveform
    if rms is not None:
        entry["rms"] = rms
    if dominant_frequency is not None:
        entry["dominant_frequency"] = dominant_frequency
    if health_index is not None:
        entry["health_index"] = health_index

    entry["last_updated"] = datetime.now().isoformat()

    if status is not None:
        entry["status"] = status
    else:
        entry["status"] = _compute_status(entry.get("online", False), entry.get("health_index"))

    return entry


def get_device_cache(device_id: int) -> Optional[dict]:
    init_cache_from_devices()
    return device_state_cache.get(device_id)


@router.get("/realtime-summary", response_model=CommandResponse)
async def get_realtime_summary():
    """
    获取当前所有设备的实时摘要信息(数据来源:内存缓存)
    """
    init_cache_from_devices()

    items = []
    for device_id in sorted(device_state_cache.keys()):
        entry = device_state_cache[device_id]
        items.append({
            "device_id": entry["device_id"],
            "device_name": entry["device_name"],
            "device_code": entry.get("device_code"),
            "online": entry.get("online", False),
            "status": entry.get("status", "offline"),
            "health_index": entry.get("health_index"),
            "rms": entry.get("rms"),
            "dominant_frequency": entry.get("dominant_frequency"),
            "last_updated": entry.get("last_updated"),
        })

    return CommandResponse(
        success=True,
        message="获取实时摘要成功",
        data={"devices": items, "total": len(items)},
    )


@router.get("/{device_id}/state", response_model=CommandResponse)
async def get_device_realtime_state(device_id: int):
    """
    获取单台设备的实时缓存状态
    """
    init_cache_from_devices()
    entry = device_state_cache.get(device_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )
    return CommandResponse(
        success=True,
        message="获取设备实时状态成功",
        data=entry,
    )
