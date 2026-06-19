from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    CommandResponse,
    PaginatedResponse,
    AlarmRule,
    AlarmRuleCreate,
    AlarmRecord,
    AlarmLevel,
    AlarmType,
)

router = APIRouter()

alarm_rules_db: List[AlarmRule] = []
alarm_records_db: List[AlarmRecord] = []
_rule_id_counter = 1
_record_id_counter = 1


def _init_sample_data():
    global _rule_id_counter, _record_id_counter

    rules = [
        AlarmRule(
            id=_rule_id_counter,
            device_id=1,
            name="RMS值超限警告",
            alarm_type=AlarmType.OVER_THRESHOLD,
            alarm_level=AlarmLevel.WARNING,
            parameter="rms",
            threshold=2.3,
            operator=">",
            duration=0,
            enabled=True,
            created_at=datetime(2024, 1, 15, 8, 0, 0),
        ),
        AlarmRule(
            id=_rule_id_counter + 1,
            device_id=1,
            name="峭度值超限报警",
            alarm_type=AlarmType.OVER_THRESHOLD,
            alarm_level=AlarmLevel.CRITICAL,
            parameter="kurtosis",
            threshold=7.0,
            operator=">",
            duration=2,
            enabled=True,
            created_at=datetime(2024, 1, 15, 8, 10, 0),
        ),
        AlarmRule(
            id=_rule_id_counter + 2,
            device_id=2,
            name="振动异常检测",
            alarm_type=AlarmType.SPECTRUM_ANOMALY,
            alarm_level=AlarmLevel.WARNING,
            parameter="spectrum",
            threshold=0.5,
            operator=">",
            duration=0,
            enabled=True,
            created_at=datetime(2024, 1, 15, 8, 15, 0),
        ),
    ]
    alarm_rules_db.extend(rules)
    _rule_id_counter += len(rules)

    now = datetime.now()
    records = [
        AlarmRecord(
            id=_record_id_counter,
            device_id=1,
            rule_id=1,
            alarm_type=AlarmType.OVER_THRESHOLD,
            alarm_level=AlarmLevel.WARNING,
            message="RMS值超过警告阈值",
            parameter="rms",
            actual_value=2.56,
            threshold=2.3,
            acknowledged=False,
            acknowledged_at=None,
            created_at=now - timedelta(hours=2),
        ),
        AlarmRecord(
            id=_record_id_counter + 1,
            device_id=1,
            rule_id=2,
            alarm_type=AlarmType.OVER_THRESHOLD,
            alarm_level=AlarmLevel.CRITICAL,
            message="峭度值严重超标",
            parameter="kurtosis",
            actual_value=8.32,
            threshold=7.0,
            acknowledged=True,
            acknowledged_at=now - timedelta(hours=1),
            created_at=now - timedelta(hours=1, minutes=30),
        ),
        AlarmRecord(
            id=_record_id_counter + 2,
            device_id=3,
            rule_id=None,
            alarm_type=AlarmType.TREND_ANOMALY,
            alarm_level=AlarmLevel.WARNING,
            message="振动值呈上升趋势",
            parameter="trend",
            actual_value=0.15,
            threshold=0.1,
            acknowledged=False,
            acknowledged_at=None,
            created_at=now - timedelta(minutes=45),
        ),
    ]
    alarm_records_db.extend(records)
    _record_id_counter += len(records)


_init_sample_data()


@router.get("/rules", response_model=PaginatedResponse)
async def get_alarm_rules(
    page: int = 1,
    page_size: int = 10,
    device_id: Optional[int] = None,
    enabled: Optional[bool] = None,
):
    """
    获取报警规则列表
    """
    filtered = alarm_rules_db

    if device_id:
        filtered = [r for r in filtered if r.device_id == device_id]

    if enabled is not None:
        filtered = [r for r in filtered if r.enabled == enabled]

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


@router.get("/rules/{rule_id}", response_model=CommandResponse)
async def get_alarm_rule(rule_id: int):
    """
    获取报警规则详情
    """
    rule = next((r for r in alarm_rules_db if r.id == rule_id), None)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报警规则ID {rule_id} 不存在"
        )
    return CommandResponse(
        success=True,
        message="获取报警规则成功",
        data=rule,
    )


@router.post("/rules", response_model=CommandResponse, status_code=201)
async def create_alarm_rule(rule: AlarmRuleCreate):
    """
    创建报警规则
    """
    global _rule_id_counter

    from .devices import devices_db

    device = next((d for d in devices_db if d.id == rule.device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {rule.device_id} 不存在"
        )

    if rule.threshold <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="阈值必须大于0"
        )

    if rule.operator not in [">", "<", ">=", "<=", "==", "!="]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的比较运算符，支持: >, <, >=, <=, ==, !="
        )

    now = datetime.now()
    new_rule = AlarmRule(
        id=_rule_id_counter,
        device_id=rule.device_id,
        name=rule.name,
        alarm_type=rule.alarm_type,
        alarm_level=rule.alarm_level,
        parameter=rule.parameter,
        threshold=rule.threshold,
        operator=rule.operator,
        duration=rule.duration,
        enabled=rule.enabled,
        created_at=now,
    )

    alarm_rules_db.append(new_rule)
    _rule_id_counter += 1

    return CommandResponse(
        success=True,
        message="创建报警规则成功",
        data=new_rule,
    )


@router.put("/rules/{rule_id}", response_model=CommandResponse)
async def update_alarm_rule(rule_id: int, rule: AlarmRuleCreate):
    """
    更新报警规则
    """
    existing = next((r for r in alarm_rules_db if r.id == rule_id), None)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报警规则ID {rule_id} 不存在"
        )

    if rule.threshold <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="阈值必须大于0"
        )

    if rule.operator not in [">", "<", ">=", "<=", "==", "!="]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的比较运算符"
        )

    update_data = rule.model_dump()
    for key, value in update_data.items():
        setattr(existing, key, value)

    return CommandResponse(
        success=True,
        message="更新报警规则成功",
        data=existing,
    )


@router.delete("/rules/{rule_id}", response_model=CommandResponse)
async def delete_alarm_rule(rule_id: int):
    """
    删除报警规则
    """
    global alarm_rules_db

    rule = next((r for r in alarm_rules_db if r.id == rule_id), None)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报警规则ID {rule_id} 不存在"
        )

    alarm_rules_db = [r for r in alarm_rules_db if r.id != rule_id]

    return CommandResponse(
        success=True,
        message="删除报警规则成功",
        data={"rule_id": rule_id},
    )


@router.patch("/rules/{rule_id}/toggle", response_model=CommandResponse)
async def toggle_alarm_rule(rule_id: int, enabled: Optional[bool] = None):
    """
    启用/禁用报警规则
    """
    existing = next((r for r in alarm_rules_db if r.id == rule_id), None)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报警规则ID {rule_id} 不存在"
        )

    if enabled is None:
        enabled = not existing.enabled

    existing.enabled = enabled

    return CommandResponse(
        success=True,
        message=f"报警规则已{'启用' if enabled else '禁用'}",
        data={"rule_id": rule_id, "enabled": enabled},
    )


@router.get("/records", response_model=PaginatedResponse)
async def get_alarm_records(
    page: int = 1,
    page_size: int = 10,
    device_id: Optional[int] = None,
    level: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    acknowledged: Optional[bool] = None,
):
    """
    获取报警记录
    """
    filtered = alarm_records_db

    if device_id:
        filtered = [r for r in filtered if r.device_id == device_id]

    if level:
        try:
            level_enum = AlarmLevel(level)
            filtered = [r for r in filtered if r.alarm_level == level_enum]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的报警级别: {level}"
            )

    if start_time:
        filtered = [r for r in filtered if r.created_at and r.created_at >= start_time]

    if end_time:
        filtered = [r for r in filtered if r.created_at and r.created_at <= end_time]

    if acknowledged is not None:
        filtered = [r for r in filtered if r.acknowledged == acknowledged]

    filtered.sort(key=lambda r: r.created_at or datetime.min, reverse=True)

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


@router.get("/records/{record_id}", response_model=CommandResponse)
async def get_alarm_record(record_id: int):
    """
    获取报警记录详情
    """
    record = next((r for r in alarm_records_db if r.id == record_id), None)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报警记录ID {record_id} 不存在"
        )
    return CommandResponse(
        success=True,
        message="获取报警记录成功",
        data=record,
    )


@router.put("/records/{record_id}/acknowledge", response_model=CommandResponse)
async def acknowledge_alarm(record_id: int):
    """
    确认报警
    """
    existing = next((r for r in alarm_records_db if r.id == record_id), None)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报警记录ID {record_id} 不存在"
        )

    if existing.acknowledged:
        return CommandResponse(
            success=True,
            message="报警已确认过",
            data=existing,
        )

    existing.acknowledged = True
    existing.acknowledged_at = datetime.now()

    return CommandResponse(
        success=True,
        message="报警确认成功",
        data=existing,
    )


@router.post("/records/batch-acknowledge", response_model=CommandResponse)
async def batch_acknowledge_alarms(record_ids: List[int]):
    """
    批量确认报警
    """
    now = datetime.now()
    updated_count = 0

    for record_id in record_ids:
        record = next((r for r in alarm_records_db if r.id == record_id), None)
        if record and not record.acknowledged:
            record.acknowledged = True
            record.acknowledged_at = now
            updated_count += 1

    return CommandResponse(
        success=True,
        message=f"已批量确认 {updated_count} 条报警记录",
        data={"updated_count": updated_count, "total_ids": len(record_ids)},
    )


@router.get("/records/summary", response_model=CommandResponse)
async def get_alarm_summary(
    device_id: Optional[int] = None,
    hours: int = 24,
):
    """
    获取报警统计摘要
    """
    start_time = datetime.now() - timedelta(hours=hours)

    filtered = alarm_records_db
    if device_id:
        filtered = [r for r in filtered if r.device_id == device_id]

    recent_alarms = [r for r in filtered if r.created_at and r.created_at >= start_time]

    level_counts = {
        "info": sum(1 for a in recent_alarms if a.alarm_level == AlarmLevel.INFO),
        "warning": sum(1 for a in recent_alarms if a.alarm_level == AlarmLevel.WARNING),
        "critical": sum(1 for a in recent_alarms if a.alarm_level == AlarmLevel.CRITICAL),
    }

    type_counts = {
        "over_threshold": sum(1 for a in recent_alarms if a.alarm_type == AlarmType.OVER_THRESHOLD),
        "spectrum_anomaly": sum(1 for a in recent_alarms if a.alarm_type == AlarmType.SPECTRUM_ANOMALY),
        "trend_anomaly": sum(1 for a in recent_alarms if a.alarm_type == AlarmType.TREND_ANOMALY),
        "connection_lost": sum(1 for a in recent_alarms if a.alarm_type == AlarmType.CONNECTION_LOST),
    }

    unacknowledged = sum(1 for a in recent_alarms if not a.acknowledged)

    return CommandResponse(
        success=True,
        message="获取报警统计成功",
        data={
            "time_window_hours": hours,
            "total_alarms": len(recent_alarms),
            "level_counts": level_counts,
            "type_counts": type_counts,
            "unacknowledged": unacknowledged,
        },
    )
