from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
import numpy as np

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    CommandResponse,
    PaginatedResponse,
    VibrationData,
    VibrationDataCreate,
)

router = APIRouter()

vibration_data_db: List[VibrationData] = []
_data_id_counter = 1


def _init_sample_data():
    global _data_id_counter

    from signal_simulator import SignalSimulator, SampleRate, FaultType, Severity

    simulator = SignalSimulator(
        sample_rate=SampleRate.SR_10240,
        fault_type=FaultType.BEARING_FAULT,
        severity=Severity.MILD,
        rpm=3000,
    )

    now = datetime.now()
    for i in range(10):
        base_time = now - timedelta(minutes=60 - i * 6)
        _, signal = simulator.generate(duration=0.5)

        data = VibrationData(
            id=_data_id_counter + i,
            device_id=1,
            channel=0,
            timestamp=base_time,
            sample_rate=10240,
            data=signal.tolist(),
            created_at=base_time,
        )
        vibration_data_db.append(data)

    _data_id_counter += 10


_init_sample_data()


@router.get("", response_model=PaginatedResponse)
async def get_vibration_data(
    page: int = 1,
    page_size: int = 10,
    device_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    channel: Optional[int] = None,
):
    """
    查询振动数据历史
    """
    filtered = vibration_data_db

    if device_id:
        filtered = [d for d in filtered if d.device_id == device_id]

    if channel is not None:
        filtered = [d for d in filtered if d.channel == channel]

    if start_time:
        filtered = [d for d in filtered if d.timestamp >= start_time]

    if end_time:
        filtered = [d for d in filtered if d.timestamp <= end_time]

    filtered.sort(key=lambda d: d.timestamp, reverse=True)

    total = len(filtered)
    total_pages = (total + page_size - 1) // page_size

    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=CommandResponse, status_code=201)
async def upload_vibration_data(data: VibrationDataCreate):
    """
    上传振动数据
    """
    global _data_id_counter

    from .devices import devices_db

    device = next((d for d in devices_db if d.id == data.device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {data.device_id} 不存在"
        )

    if len(data.data) < 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="振动数据长度不足，至少需要256个采样点"
        )

    if data.sample_rate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="采样率必须大于0"
        )

    now = datetime.now()
    new_data = VibrationData(
        id=_data_id_counter,
        device_id=data.device_id,
        channel=data.channel,
        timestamp=data.timestamp,
        sample_rate=data.sample_rate,
        data=data.data,
        created_at=now,
    )

    vibration_data_db.append(new_data)
    _data_id_counter += 1

    if len(vibration_data_db) > 10000:
        vibration_data_db[:] = vibration_data_db[-10000:]

    return CommandResponse(
        success=True,
        message="振动数据上传成功",
        data={"id": new_data.id, "sample_count": len(data.data)},
    )


@router.get("/{data_id}", response_model=CommandResponse)
async def get_vibration_data_detail(data_id: int):
    """
    获取单条振动数据详情
    """
    data = next((d for d in vibration_data_db if d.id == data_id), None)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"振动数据ID {data_id} 不存在"
        )

    signal = np.array(data.data)
    stats = {
        "sample_count": len(signal),
        "duration": len(signal) / data.sample_rate,
        "min": float(np.min(signal)),
        "max": float(np.max(signal)),
        "mean": float(np.mean(signal)),
        "rms": float(np.sqrt(np.mean(signal ** 2))),
        "peak": float(np.max(np.abs(signal))),
    }

    return CommandResponse(
        success=True,
        message="获取振动数据成功",
        data={
            "vibration_data": data,
            "statistics": stats,
        },
    )


@router.delete("/{data_id}", response_model=CommandResponse)
async def delete_vibration_data(data_id: int):
    """
    删除振动数据
    """
    global vibration_data_db

    data = next((d for d in vibration_data_db if d.id == data_id), None)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"振动数据ID {data_id} 不存在"
        )

    vibration_data_db = [d for d in vibration_data_db if d.id != data_id]

    return CommandResponse(
        success=True,
        message="删除振动数据成功",
        data={"data_id": data_id},
    )


@router.get("/{device_id}/latest", response_model=CommandResponse)
async def get_latest_data(
    device_id: int,
    channel: int = 0,
    count: int = 1,
):
    """
    获取设备最新的振动数据
    """
    from .devices import devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    if count < 1 or count > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="获取数量必须在1-100之间"
        )

    device_data = [
        d for d in vibration_data_db
        if d.device_id == device_id and d.channel == channel
    ]
    device_data.sort(key=lambda d: d.timestamp, reverse=True)

    if not device_data:
        return CommandResponse(
            success=True,
            message="设备暂无振动数据",
            data=[],
        )

    latest_data = device_data[:count]

    return CommandResponse(
        success=True,
        message="获取最新振动数据成功",
        data=latest_data,
    )


@router.post("/batch", response_model=CommandResponse, status_code=201)
async def batch_upload_data(data_list: List[VibrationDataCreate]):
    """
    批量上传振动数据
    """
    if len(data_list) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="批量上传最多支持1000条数据"
        )

    from .devices import devices_db

    now = datetime.now()
    success_count = 0
    errors = []

    for idx, data in enumerate(data_list):
        try:
            device = next((d for d in devices_db if d.id == data.device_id), None)
            if not device:
                errors.append(f"第{idx+1}条: 设备ID {data.device_id} 不存在")
                continue

            if len(data.data) < 256:
                errors.append(f"第{idx+1}条: 数据长度不足256点")
                continue

            global _data_id_counter
            new_data = VibrationData(
                id=_data_id_counter,
                device_id=data.device_id,
                channel=data.channel,
                timestamp=data.timestamp,
                sample_rate=data.sample_rate,
                data=data.data,
                created_at=now,
            )
            vibration_data_db.append(new_data)
            _data_id_counter += 1
            success_count += 1
        except Exception as e:
            errors.append(f"第{idx+1}条: {str(e)}")

    if len(vibration_data_db) > 10000:
        vibration_data_db[:] = vibration_data_db[-10000:]

    return CommandResponse(
        success=True,
        message=f"批量上传完成，成功 {success_count} 条，失败 {len(errors)} 条",
        data={
            "success_count": success_count,
            "error_count": len(errors),
            "errors": errors if errors else None,
        },
    )


@router.get("/{device_id}/export", response_model=CommandResponse)
async def export_data(
    device_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    format: str = "json",
):
    """
    导出振动数据
    """
    from .devices import devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    filtered = [d for d in vibration_data_db if d.device_id == device_id]

    if start_time:
        filtered = [d for d in filtered if d.timestamp >= start_time]

    if end_time:
        filtered = [d for d in filtered if d.timestamp <= end_time]

    filtered.sort(key=lambda d: d.timestamp)

    if format not in ["json", "csv"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的导出格式，仅支持 json 和 csv"
        )

    if format == "csv":
        csv_lines = ["id,device_id,channel,timestamp,sample_rate,data_length"]
        for d in filtered:
            csv_lines.append(
                f"{d.id},{d.device_id},{d.channel},{d.timestamp.isoformat()},{d.sample_rate},{len(d.data)}"
            )
        export_data = "\n".join(csv_lines)
    else:
        export_data = [
            {
                "id": d.id,
                "device_id": d.device_id,
                "channel": d.channel,
                "timestamp": d.timestamp.isoformat(),
                "sample_rate": d.sample_rate,
                "data_length": len(d.data),
                "data": d.data,
            }
            for d in filtered
        ]

    return CommandResponse(
        success=True,
        message=f"导出 {len(filtered)} 条振动数据成功",
        data={
            "format": format,
            "count": len(filtered),
            "export_data": export_data,
        },
    )


@router.get("/{device_id}/statistics", response_model=CommandResponse)
async def get_data_statistics(
    device_id: int,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """
    获取振动数据统计信息
    """
    from .devices import devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    filtered = [d for d in vibration_data_db if d.device_id == device_id]

    if start_time:
        filtered = [d for d in filtered if d.timestamp >= start_time]

    if end_time:
        filtered = [d for d in filtered if d.timestamp <= end_time]

    if not filtered:
        return CommandResponse(
            success=True,
            message="暂无数据统计",
            data={
                "total_records": 0,
                "time_range": None,
                "statistics": None,
            },
        )

    all_signals = np.concatenate([np.array(d.data) for d in filtered])

    timestamps = [d.timestamp for d in filtered]
    time_start = min(timestamps)
    time_end = max(timestamps)

    stats = {
        "total_records": len(filtered),
        "total_samples": len(all_signals),
        "total_duration_hours": (time_end - time_start).total_seconds() / 3600,
        "time_range": {
            "start": time_start.isoformat(),
            "end": time_end.isoformat(),
        },
        "sample_rates": list(set(d.sample_rate for d in filtered)),
        "channels": list(set(d.channel for d in filtered)),
        "signal_statistics": {
            "min": float(np.min(all_signals)),
            "max": float(np.max(all_signals)),
            "mean": float(np.mean(all_signals)),
            "std": float(np.std(all_signals)),
            "rms": float(np.sqrt(np.mean(all_signals ** 2))),
            "peak": float(np.max(np.abs(all_signals))),
        },
    }

    return CommandResponse(
        success=True,
        message="获取数据统计成功",
        data=stats,
    )


@router.delete("/{device_id}/cleanup", response_model=CommandResponse)
async def cleanup_old_data(
    device_id: int,
    days_to_keep: int = 30,
):
    """
    清理历史数据
    """
    global vibration_data_db

    from .devices import devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    if days_to_keep < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="保留天数必须大于0"
        )

    cutoff_time = datetime.now() - timedelta(days=days_to_keep)

    device_data_count_before = sum(1 for d in vibration_data_db if d.device_id == device_id)

    vibration_data_db = [
        d for d in vibration_data_db
        if d.device_id != device_id or d.timestamp >= cutoff_time
    ]

    device_data_count_after = sum(1 for d in vibration_data_db if d.device_id == device_id)
    deleted_count = device_data_count_before - device_data_count_after

    return CommandResponse(
        success=True,
        message=f"清理完成，删除 {deleted_count} 条旧数据",
        data={
            "device_id": device_id,
            "days_to_keep": days_to_keep,
            "deleted_count": deleted_count,
            "remaining_count": device_data_count_after,
        },
    )
