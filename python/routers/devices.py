from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    CommandResponse,
    PaginatedResponse,
    Device,
    DeviceCreate,
    DeviceUpdate,
    DeviceStatus,
)

router = APIRouter()

devices_db: List[Device] = []
_device_id_counter = 1


def _init_sample_devices():
    global _device_id_counter
    samples = [
        Device(
            id=_device_id_counter,
            name="电机-001",
            code="MOT-001",
            location="A车间-1号线",
            status=DeviceStatus.ONLINE,
            ip_address="192.168.1.101",
            sensor_count=2,
            description="主传动电机，55kW",
            created_at=datetime(2024, 1, 15, 8, 0, 0),
            updated_at=datetime(2024, 6, 1, 10, 30, 0),
        ),
        Device(
            id=_device_id_counter + 1,
            name="齿轮箱-001",
            code="GEAR-001",
            location="A车间-1号线",
            status=DeviceStatus.ONLINE,
            ip_address="192.168.1.102",
            sensor_count=3,
            description="减速机，速比1:25",
            created_at=datetime(2024, 1, 15, 8, 5, 0),
            updated_at=datetime(2024, 6, 1, 10, 35, 0),
        ),
        Device(
            id=_device_id_counter + 2,
            name="泵组-001",
            code="PUMP-001",
            location="B车间-2号线",
            status=DeviceStatus.WARNING,
            ip_address="192.168.1.103",
            sensor_count=1,
            description="冷却水泵，30kW",
            created_at=datetime(2024, 2, 10, 9, 0, 0),
            updated_at=datetime(2024, 6, 15, 14, 20, 0),
        ),
        Device(
            id=_device_id_counter + 3,
            name="风机-001",
            code="FAN-001",
            location="C车间-3号线",
            status=DeviceStatus.OFFLINE,
            ip_address=None,
            sensor_count=2,
            description="引风机，75kW",
            created_at=datetime(2024, 3, 20, 10, 0, 0),
            updated_at=datetime(2024, 5, 10, 16, 45, 0),
        ),
    ]
    devices_db.extend(samples)
    _device_id_counter += len(samples)


_init_sample_devices()


@router.get("", response_model=PaginatedResponse)
async def get_devices(
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """
    获取设备列表，支持分页和条件查询
    """
    filtered = devices_db

    if status:
        try:
            status_enum = DeviceStatus(status)
            filtered = [d for d in filtered if d.status == status_enum]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的设备状态: {status}"
            )

    if keyword:
        keyword_lower = keyword.lower()
        filtered = [
            d for d in filtered
            if keyword_lower in d.name.lower()
            or keyword_lower in d.code.lower()
            or keyword_lower in d.location.lower()
        ]

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


@router.get("/{device_id}", response_model=CommandResponse)
async def get_device(device_id: int):
    """
    获取设备详情
    """
    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )
    return CommandResponse(
        success=True,
        message="获取设备信息成功",
        data=device,
    )


@router.post("", response_model=CommandResponse, status_code=201)
async def create_device(device: DeviceCreate):
    """
    创建设备
    """
    global _device_id_counter

    existing = next((d for d in devices_db if d.code == device.code), None)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"设备编码 {device.code} 已存在"
        )

    now = datetime.now()
    new_device = Device(
        id=_device_id_counter,
        name=device.name,
        code=device.code,
        location=device.location,
        status=DeviceStatus.OFFLINE,
        ip_address=device.ip_address,
        sensor_count=device.sensor_count,
        description=device.description,
        created_at=now,
        updated_at=now,
    )

    devices_db.append(new_device)
    _device_id_counter += 1

    return CommandResponse(
        success=True,
        message="创建设备成功",
        data=new_device,
    )


@router.put("/{device_id}", response_model=CommandResponse)
async def update_device(device_id: int, device: DeviceUpdate):
    """
    更新设备信息
    """
    existing = next((d for d in devices_db if d.id == device_id), None)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    update_data = device.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(existing, key, value)

    existing.updated_at = datetime.now()

    return CommandResponse(
        success=True,
        message="更新设备信息成功",
        data=existing,
    )


@router.delete("/{device_id}", response_model=CommandResponse)
async def delete_device(device_id: int):
    """
    删除设备
    """
    global devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    devices_db = [d for d in devices_db if d.id != device_id]

    return CommandResponse(
        success=True,
        message="删除设备成功",
        data={"device_id": device_id},
    )


@router.patch("/{device_id}/status", response_model=CommandResponse)
async def update_device_status(device_id: int, new_status: DeviceStatus):
    """
    更新设备状态
    """
    existing = next((d for d in devices_db if d.id == device_id), None)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    existing.status = new_status
    existing.updated_at = datetime.now()

    return CommandResponse(
        success=True,
        message=f"设备状态已更新为 {new_status.value}",
        data={"device_id": device_id, "status": new_status.value},
    )


@router.get("/{device_id}/summary", response_model=CommandResponse)
async def get_device_summary(device_id: int):
    """
    获取设备统计摘要
    """
    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    from .data import vibration_data_db
    from .analysis import analysis_results_db
    from .alarms import alarm_records_db

    device_data = [d for d in vibration_data_db if d.device_id == device_id]
    device_analysis = [a for a in analysis_results_db if a.device_id == device_id]
    device_alarms = [a for a in alarm_records_db if a.device_id == device_id]

    unacknowledged_alarms = sum(1 for a in device_alarms if not a.acknowledged)

    latest_health = None
    if device_analysis:
        latest_health = device_analysis[-1].health_index

    return CommandResponse(
        success=True,
        message="获取设备统计摘要成功",
        data={
            "device": device,
            "data_count": len(device_data),
            "analysis_count": len(device_analysis),
            "alarm_count": len(device_alarms),
            "unacknowledged_alarms": unacknowledged_alarms,
            "latest_health_index": latest_health,
        },
    )
