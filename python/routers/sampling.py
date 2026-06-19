from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    CommandResponse,
    PaginatedResponse,
    SamplingParams,
    SamplingParamsCreate,
)

router = APIRouter()

sampling_params_db: List[SamplingParams] = []
_sampling_id_counter = 1


def _init_sample_params():
    global _sampling_id_counter
    samples = [
        SamplingParams(
            id=_sampling_id_counter,
            device_id=1,
            sample_rate=1000,
            sample_length=1024,
            channel_count=2,
            acquisition_interval=1000,
            is_continuous=True,
            created_at=datetime(2024, 1, 15, 8, 0, 0),
        ),
        SamplingParams(
            id=_sampling_id_counter + 1,
            device_id=2,
            sample_rate=2000,
            sample_length=2048,
            channel_count=3,
            acquisition_interval=500,
            is_continuous=True,
            created_at=datetime(2024, 1, 15, 8, 5, 0),
        ),
        SamplingParams(
            id=_sampling_id_counter + 2,
            device_id=3,
            sample_rate=1000,
            sample_length=1024,
            channel_count=1,
            acquisition_interval=2000,
            is_continuous=False,
            created_at=datetime(2024, 2, 10, 9, 0, 0),
        ),
    ]
    sampling_params_db.extend(samples)
    _sampling_id_counter += len(samples)


_init_sample_params()


@router.get("/{device_id}", response_model=CommandResponse)
async def get_sampling_params(device_id: int):
    """
    获取设备采样参数
    """
    from .devices import devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    params = next((p for p in sampling_params_db if p.device_id == device_id), None)
    if not params:
        return CommandResponse(
            success=True,
            message="设备暂无采样参数配置",
            data=None,
        )

    return CommandResponse(
        success=True,
        message="获取采样参数成功",
        data=params,
    )


@router.get("", response_model=PaginatedResponse)
async def list_sampling_params(
    page: int = 1,
    page_size: int = 10,
    device_id: Optional[int] = None,
):
    """
    获取采样参数列表
    """
    filtered = sampling_params_db

    if device_id:
        filtered = [p for p in filtered if p.device_id == device_id]

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
async def create_sampling_params(params: SamplingParamsCreate):
    """
    创建设备采样参数
    """
    global _sampling_id_counter

    from .devices import devices_db

    device = next((d for d in devices_db if d.id == params.device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {params.device_id} 不存在"
        )

    existing = next((p for p in sampling_params_db if p.device_id == params.device_id), None)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"设备ID {params.device_id} 已存在采样参数配置"
        )

    if params.sample_rate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="采样率必须大于0"
        )

    if params.sample_length not in [256, 512, 1024, 2048, 4096, 8192]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="采样点数必须为2的幂次方(256, 512, 1024, 2048, 4096, 8192)"
        )

    if params.channel_count <= 0 or params.channel_count > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="通道数必须在1-8之间"
        )

    if params.acquisition_interval <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="采集间隔必须大于0"
        )

    now = datetime.now()
    new_params = SamplingParams(
        id=_sampling_id_counter,
        device_id=params.device_id,
        sample_rate=params.sample_rate,
        sample_length=params.sample_length,
        channel_count=params.channel_count,
        acquisition_interval=params.acquisition_interval,
        is_continuous=params.is_continuous,
        created_at=now,
    )

    sampling_params_db.append(new_params)
    _sampling_id_counter += 1

    return CommandResponse(
        success=True,
        message="创建采样参数成功",
        data=new_params,
    )


@router.put("/{params_id}", response_model=CommandResponse)
async def update_sampling_params(params_id: int, params: SamplingParamsCreate):
    """
    更新采样参数
    """
    existing = next((p for p in sampling_params_db if p.id == params_id), None)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"采样参数ID {params_id} 不存在"
        )

    if params.sample_rate <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="采样率必须大于0"
        )

    if params.sample_length not in [256, 512, 1024, 2048, 4096, 8192]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="采样点数必须为2的幂次方(256, 512, 1024, 2048, 4096, 8192)"
        )

    if params.channel_count <= 0 or params.channel_count > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="通道数必须在1-8之间"
        )

    if params.acquisition_interval <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="采集间隔必须大于0"
        )

    update_data = params.model_dump()
    for key, value in update_data.items():
        setattr(existing, key, value)

    return CommandResponse(
        success=True,
        message="更新采样参数成功",
        data=existing,
    )


@router.delete("/{params_id}", response_model=CommandResponse)
async def delete_sampling_params(params_id: int):
    """
    删除采样参数
    """
    global sampling_params_db

    params = next((p for p in sampling_params_db if p.id == params_id), None)
    if not params:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"采样参数ID {params_id} 不存在"
        )

    sampling_params_db = [p for p in sampling_params_db if p.id != params_id]

    return CommandResponse(
        success=True,
        message="删除采样参数成功",
        data={"params_id": params_id},
    )


@router.post("/{device_id}/apply", response_model=CommandResponse)
async def apply_sampling_params(device_id: int):
    """
    应用采样参数到设备（下发到硬件）
    """
    from .devices import devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    params = next((p for p in sampling_params_db if p.device_id == device_id), None)
    if not params:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 暂无采样参数配置"
        )

    return CommandResponse(
        success=True,
        message="采样参数已应用到设备",
        data={
            "device_id": device_id,
            "params_id": params.id,
            "applied_at": datetime.now().isoformat(),
        },
    )


@router.get("/supported-rates", response_model=CommandResponse)
async def get_supported_sample_rates():
    """
    获取支持的采样率列表
    """
    return CommandResponse(
        success=True,
        message="获取支持的采样率成功",
        data={
            "sample_rates": [500, 1000, 2000, 5000, 10000, 20000, 50000],
            "sample_lengths": [256, 512, 1024, 2048, 4096, 8192],
            "max_channels": 8,
        },
    )
