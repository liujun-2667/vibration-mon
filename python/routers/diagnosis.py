from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    CommandResponse,
    PaginatedResponse,
    DiagnosisTask,
    DiagnosisTaskCreate,
    DiagnosisStatus,
    FaultModeKnowledge,
    FaultModeKnowledgeCreate,
    SeverityLevel,
    DiagnosisReport,
)
from database import get_database
from fault_matcher import get_fault_matcher

router = APIRouter()

db = get_database()
matcher = get_fault_matcher()


def _get_device_name(device_id: int) -> Optional[str]:
    try:
        from routers.devices import devices_db
        device = next((d for d in devices_db if d.id == device_id), None)
        return device.name if device else None
    except Exception:
        return None


def _get_device_info(device_id: int) -> dict:
    try:
        from routers.devices import devices_db
        device = next((d for d in devices_db if d.id == device_id), None)
        if device:
            return device.model_dump(mode="json")
    except Exception:
        pass
    return {"id": device_id, "name": f"设备-{device_id}"}


@router.post("/tasks", response_model=CommandResponse, status_code=201)
async def create_diagnosis_task(task_create: DiagnosisTaskCreate, background_tasks: BackgroundTasks):
    """
    创建诊断任务
    """
    device_name = _get_device_name(task_create.device_id)

    task = db.create_diagnosis_task(
        device_id=task_create.device_id,
        device_name=device_name,
        start_time=task_create.start_time,
        end_time=task_create.end_time,
    )

    background_tasks.add_task(matcher.run_diagnosis, task.id)

    return CommandResponse(
        success=True,
        message="诊断任务创建成功，正在后台执行",
        data=task,
    )


@router.get("/tasks", response_model=PaginatedResponse)
async def get_diagnosis_tasks(
    page: int = 1,
    page_size: int = 10,
    device_id: Optional[int] = None,
    status: Optional[str] = None,
):
    """
    获取诊断任务列表
    """
    status_enum = None
    if status:
        try:
            status_enum = DiagnosisStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值: {status}"
            )

    tasks, total = db.get_diagnosis_tasks(
        page=page,
        page_size=page_size,
        device_id=device_id,
        status=status_enum,
    )

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=tasks,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/tasks/{task_id}", response_model=CommandResponse)
async def get_diagnosis_task(task_id: int):
    """
    获取诊断任务详情
    """
    task = db.get_diagnosis_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"诊断任务 {task_id} 不存在"
        )

    return CommandResponse(
        success=True,
        message="获取诊断任务成功",
        data=task,
    )


@router.post("/tasks/{task_id}/run", response_model=CommandResponse)
async def run_diagnosis_task(task_id: int, background_tasks: BackgroundTasks):
    """
    手动运行诊断任务
    """
    task = db.get_diagnosis_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"诊断任务 {task_id} 不存在"
        )

    if task.status == DiagnosisStatus.COMPLETED:
        return CommandResponse(
            success=True,
            message="诊断任务已完成，无需重新运行",
            data=task,
        )

    background_tasks.add_task(matcher.run_diagnosis, task_id)

    return CommandResponse(
        success=True,
        message="诊断任务已提交，正在后台执行",
        data=task,
    )


@router.get("/tasks/{task_id}/match-results", response_model=CommandResponse)
async def get_match_results(task_id: int):
    """
    获取诊断任务的故障匹配结果
    """
    task = db.get_diagnosis_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"诊断任务 {task_id} 不存在"
        )

    if task.status != DiagnosisStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"诊断任务尚未完成，当前状态: {task.status.value}"
        )

    return CommandResponse(
        success=True,
        message="获取故障匹配结果成功",
        data=task.match_results or [],
    )


@router.get("/tasks/{task_id}/report", response_model=CommandResponse)
async def get_diagnosis_report(task_id: int):
    """
    获取诊断报告
    """
    task = db.get_diagnosis_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"诊断任务 {task_id} 不存在"
        )

    if task.status != DiagnosisStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"诊断任务尚未完成，当前状态: {task.status.value}"
        )

    device_info = _get_device_info(task.device_id)
    report = matcher.generate_diagnosis_report(task, device_info)

    return CommandResponse(
        success=True,
        message="生成诊断报告成功",
        data=report,
    )


@router.get("/tasks/{task_id}/report/download")
async def download_diagnosis_report(task_id: int):
    """
    下载诊断报告为JSON文件
    """
    task = db.get_diagnosis_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"诊断任务 {task_id} 不存在"
        )

    if task.status != DiagnosisStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"诊断任务尚未完成，当前状态: {task.status.value}"
        )

    device_info = _get_device_info(task.device_id)
    report = matcher.generate_diagnosis_report(task, device_info)

    report_json = report.model_dump(mode="json")

    response = JSONResponse(
        content=report_json,
        media_type="application/json",
    )
    response.headers["Content-Disposition"] = f"attachment; filename=diagnosis_report_{task_id}.json"

    return response


@router.get("/knowledge", response_model=PaginatedResponse)
async def get_fault_knowledge(
    page: int = 1,
    page_size: int = 100,
):
    """
    获取故障模式知识库列表
    """
    knowledge_list, total = db.get_fault_knowledge(
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=knowledge_list,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/knowledge", response_model=CommandResponse, status_code=201)
async def create_fault_knowledge(knowledge_create: FaultModeKnowledgeCreate):
    """
    新增故障模式规则
    """
    try:
        knowledge = db.create_fault_knowledge(
            name=knowledge_create.name,
            description=knowledge_create.description,
            key_frequency_features=knowledge_create.key_frequency_features or "",
            severity_level=knowledge_create.severity_level or SeverityLevel.MEDIUM,
            maintenance_action=knowledge_create.maintenance_action or "专业检查",
        )

        return CommandResponse(
            success=True,
            message="新增故障模式规则成功",
            data=knowledge,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/knowledge/{knowledge_id}", response_model=CommandResponse)
async def delete_fault_knowledge(knowledge_id: int):
    """
    删除故障模式规则
    """
    success = db.delete_fault_knowledge(knowledge_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"故障模式规则 {knowledge_id} 不存在"
        )

    return CommandResponse(
        success=True,
        message="删除故障模式规则成功",
        data={"knowledge_id": knowledge_id},
    )
