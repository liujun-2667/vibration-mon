from datetime import datetime, timedelta
from typing import Optional, Any
from fastapi import APIRouter, HTTPException, status
from collections import deque

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import CommandResponse

router = APIRouter()

device_state_cache: dict[int, dict] = {}
packet_timestamps: dict[int, deque] = {}

DATA_QUALITY_WINDOW_SECONDS = 300
DATA_QUALITY_THEORETICAL_PACKETS = 300


def _compute_vibration_level(rms: Optional[float]) -> Optional[str]:
    if rms is None:
        return None
    if rms < 1.0:
        return "优"
    elif rms < 2.5:
        return "良"
    elif rms < 5.0:
        return "警"
    else:
        return "危"


def _compute_status(online: bool, health_index: Optional[float]) -> str:
    if not online:
        return "offline"
    if health_index is not None and health_index < 60:
        return "alarm"
    return "online"


def _compute_data_quality(device_id: int) -> Optional[float]:
    packets = packet_timestamps.get(device_id)
    if packets is None:
        return None
    cutoff = datetime.now() - timedelta(seconds=DATA_QUALITY_WINDOW_SECONDS)
    while packets and packets[0] < cutoff:
        packets.popleft()
    return min(100.0, len(packets) / DATA_QUALITY_THEORETICAL_PACKETS * 100.0)


def _latest_analysis_for(device_id: int):
    try:
        from .analysis import analysis_results_db
        device_results = [r for r in analysis_results_db if r.device_id == device_id]
        if not device_results:
            return None
        return max(device_results, key=lambda r: r.timestamp)
    except Exception:
        return None


def _find_last_alert_time(device_id: int) -> Optional[datetime]:
    try:
        from .analysis import analysis_results_db
        device_results = [r for r in analysis_results_db if r.device_id == device_id and r.health_index < 60]
        if not device_results:
            return None
        latest = max(device_results, key=lambda r: r.timestamp)
        return latest.timestamp
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
        last_alert_time = _find_last_alert_time(device.id)

        device_state_cache[device.id] = {
            "device_id": device.id,
            "device_name": device.name,
            "device_code": device.code,
            "online": online,
            "status": _compute_status(online, health_index),
            "health_index": health_index,
            "rms": rms,
            "dominant_frequency": dominant_frequency,
            "vibration_level": _compute_vibration_level(rms),
            "last_alert_time": last_alert_time.isoformat() if last_alert_time else None,
            "last_updated": last_ts.isoformat() if last_ts else None,
            "latest_waveform": None,
        }

        if device.id not in packet_timestamps:
            packet_timestamps[device.id] = deque()


def update_device_cache(
    device_id: int,
    *,
    online: Optional[bool] = None,
    waveform: Optional[dict] = None,
    rms: Optional[float] = None,
    dominant_frequency: Optional[float] = None,
    health_index: Optional[float] = None,
    status: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> Optional[dict]:
    init_cache_from_devices()
    entry = device_state_cache.get(device_id)
    if entry is None:
        return None

    if timestamp is None:
        timestamp = datetime.now()

    if device_id not in packet_timestamps:
        packet_timestamps[device_id] = deque()
    packet_timestamps[device_id].append(timestamp)

    cutoff = timestamp - timedelta(seconds=DATA_QUALITY_WINDOW_SECONDS)
    while packet_timestamps[device_id] and packet_timestamps[device_id][0] < cutoff:
        packet_timestamps[device_id].popleft()

    if online is not None:
        entry["online"] = online
    if waveform is not None:
        entry["latest_waveform"] = waveform
    if rms is not None:
        entry["rms"] = rms
        entry["vibration_level"] = _compute_vibration_level(rms)
    if dominant_frequency is not None:
        entry["dominant_frequency"] = dominant_frequency
    if health_index is not None:
        prev_health = entry.get("health_index")
        entry["health_index"] = health_index
        if prev_health is not None and prev_health >= 60 and health_index < 60:
            entry["last_alert_time"] = timestamp.isoformat()
        elif health_index < 60:
            if entry.get("last_alert_time") is None:
                entry["last_alert_time"] = timestamp.isoformat()

    entry["last_updated"] = timestamp.isoformat()

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
        data_quality = _compute_data_quality(device_id)
        items.append({
            "device_id": entry["device_id"],
            "device_name": entry["device_name"],
            "device_code": entry.get("device_code"),
            "online": entry.get("online", False),
            "status": entry.get("status", "offline"),
            "health_index": entry.get("health_index"),
            "rms": entry.get("rms"),
            "dominant_frequency": entry.get("dominant_frequency"),
            "vibration_level": entry.get("vibration_level"),
            "last_alert_time": entry.get("last_alert_time"),
            "data_quality": round(data_quality, 1) if data_quality is not None else None,
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

    data_quality = _compute_data_quality(device_id)
    result = {**entry, "data_quality": round(data_quality, 1) if data_quality is not None else None}

    return CommandResponse(
        success=True,
        message="获取设备实时状态成功",
        data=result,
    )


@router.get("/export-report", response_model=CommandResponse)
async def export_report(device_id: int, hours: int = 24):
    """
    导出指定设备的健康报告(默认最近24小时)
    """
    init_cache_from_devices()

    device_entry = device_state_cache.get(device_id)
    if device_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    try:
        from .analysis import analysis_results_db
    except Exception:
        analysis_results_db = []

    now = datetime.now()
    cutoff = now - timedelta(hours=hours)

    device_results = [
        r for r in analysis_results_db
        if r.device_id == device_id and r.timestamp >= cutoff
    ]
    device_results.sort(key=lambda r: r.timestamp)

    if not device_results:
        return CommandResponse(
            success=False,
            message="暂无足够数据生成报告",
            data=None,
        )

    health_values = [r.health_index for r in device_results if r.health_index is not None]
    rms_values = [r.time_domain.rms for r in device_results if r.time_domain and r.time_domain.rms is not None]

    import statistics

    health_stats = {
        "max": round(max(health_values), 1) if health_values else None,
        "min": round(min(health_values), 1) if health_values else None,
        "avg": round(statistics.mean(health_values), 1) if health_values else None,
        "stddev": round(statistics.stdev(health_values), 2) if len(health_values) > 1 else 0.0,
    }

    rms_stats = {
        "max": round(max(rms_values), 4) if rms_values else None,
        "min": round(min(rms_values), 4) if rms_values else None,
        "avg": round(statistics.mean(rms_values), 4) if rms_values else None,
        "stddev": round(statistics.stdev(rms_values), 4) if len(rms_values) > 1 else 0.0,
    }

    level_counts = {"优": 0, "良": 0, "警": 0, "危": 0}
    total = len(rms_values)
    for rms in rms_values:
        level = _compute_vibration_level(rms)
        if level in level_counts:
            level_counts[level] += 1

    vibration_distribution = {
        level: round(count / total * 100.0, 1) if total > 0 else 0.0
        for level, count in level_counts.items()
    }

    abnormal_events = [
        {
            "timestamp": r.timestamp.isoformat(),
            "health_index": r.health_index,
            "rms": r.time_domain.rms if r.time_domain else None,
        }
        for r in device_results
        if r.health_index is not None and r.health_index < 60
    ]

    report = {
        "device_info": {
            "device_id": device_entry.get("device_id"),
            "device_name": device_entry.get("device_name"),
            "device_code": device_entry.get("device_code"),
            "online": device_entry.get("online"),
            "status": device_entry.get("status"),
        },
        "report_period": {
            "start_time": cutoff.isoformat(),
            "end_time": now.isoformat(),
            "hours": hours,
            "data_points": len(device_results),
        },
        "health_index_stats": health_stats,
        "rms_stats": rms_stats,
        "vibration_level_distribution": vibration_distribution,
        "abnormal_events": abnormal_events,
    }

    return CommandResponse(
        success=True,
        message="报告生成成功",
        data=report,
    )
