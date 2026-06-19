from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse
import io
import os
import tempfile

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    CommandResponse,
    PaginatedResponse,
    ReportRequest,
)

router = APIRouter()

reports_db: List[Dict[str, Any]] = []
_report_id_counter = 1


def _init_sample_reports():
    global _report_id_counter
    now = datetime.now()
    samples = [
        {
            "id": _report_id_counter,
            "device_id": 1,
            "report_type": "daily",
            "format": "pdf",
            "start_time": now - timedelta(days=1),
            "end_time": now,
            "status": "completed",
            "file_path": None,
            "created_at": now,
            "completed_at": now,
        },
        {
            "id": _report_id_counter + 1,
            "device_id": 1,
            "report_type": "weekly",
            "format": "pdf",
            "start_time": now - timedelta(days=7),
            "end_time": now,
            "status": "completed",
            "file_path": None,
            "created_at": now - timedelta(hours=2),
            "completed_at": now - timedelta(hours=1, minutes=58),
        },
    ]
    reports_db.extend(samples)
    _report_id_counter += len(samples)


_init_sample_reports()


@router.post("", response_model=CommandResponse, status_code=202)
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
):
    """
    生成分析报告（异步）
    """
    global _report_id_counter

    from .devices import devices_db

    device = next((d for d in devices_db if d.id == request.device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {request.device_id} 不存在"
        )

    if request.start_time >= request.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始时间必须早于结束时间"
        )

    if request.format not in ["pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="目前仅支持 PDF 格式报告"
        )

    now = datetime.now()
    report_info = {
        "id": _report_id_counter,
        "device_id": request.device_id,
        "report_type": request.report_type,
        "format": request.format,
        "start_time": request.start_time,
        "end_time": request.end_time,
        "status": "processing",
        "file_path": None,
        "file_size": None,
        "created_at": now,
        "completed_at": None,
        "error": None,
    }

    reports_db.append(report_info)
    _report_id_counter += 1

    background_tasks.add_task(
        _generate_report_task,
        report_info["id"],
        request,
        device,
    )

    return CommandResponse(
        success=True,
        message="报告生成任务已提交，正在处理中",
        data={
            "report_id": report_info["id"],
            "status": "processing",
        },
    )


async def _generate_report_task(
    report_id: int,
    request: ReportRequest,
    device,
):
    try:
        from .analysis import analysis_results_db
        from .data import vibration_data_db
        from .alarms import alarm_records_db
        from report_generator import ReportGenerator, ReportData as GenReportData
        from feature_frequency import BearingParameters

        device_analysis = [
            r for r in analysis_results_db
            if r.device_id == request.device_id
            and r.timestamp >= request.start_time
            and r.timestamp <= request.end_time
        ]

        device_data = [
            d for d in vibration_data_db
            if d.device_id == request.device_id
            and d.timestamp >= request.start_time
            and d.timestamp <= request.end_time
        ]

        device_alarms = [
            a for a in alarm_records_db
            if a.device_id == request.device_id
            and a.created_at
            and a.created_at >= request.start_time
            and a.created_at <= request.end_time
        ]

        bearing_params = BearingParameters(
            roller_count=10,
            pitch_diameter=80.0,
            roller_diameter=12.0,
            contact_angle_deg=0.0,
        )

        report_data = GenReportData(
            device=device,
            analysis_results=device_analysis,
            vibration_data=device_data,
            alarm_records=device_alarms,
            bearing_params=bearing_params,
            gear_params=None,
            rpm=3000.0,
            start_time=request.start_time,
            end_time=request.end_time,
        )

        generator = ReportGenerator()
        report_bytes = generator.generate_report_bytes(report_data)

        tmp_dir = tempfile.gettempdir()
        file_name = f"report_{report_id}_{request.device_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        file_path = os.path.join(tmp_dir, file_name)

        with open(file_path, "wb") as f:
            f.write(report_bytes)

        for r in reports_db:
            if r["id"] == report_id:
                r["status"] = "completed"
                r["file_path"] = file_path
                r["file_size"] = len(report_bytes)
                r["completed_at"] = datetime.now()
                break

    except Exception as e:
        for r in reports_db:
            if r["id"] == report_id:
                r["status"] = "failed"
                r["error"] = str(e)
                r["completed_at"] = datetime.now()
                break


@router.get("", response_model=PaginatedResponse)
async def get_reports(
    page: int = 1,
    page_size: int = 10,
    device_id: Optional[int] = None,
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """
    获取报告列表
    """
    filtered = reports_db

    if device_id:
        filtered = [r for r in filtered if r["device_id"] == device_id]

    if report_type:
        filtered = [r for r in filtered if r["report_type"] == report_type]

    if status:
        filtered = [r for r in filtered if r["status"] == status]

    if start_time:
        filtered = [r for r in filtered if r["created_at"] >= start_time]

    if end_time:
        filtered = [r for r in filtered if r["created_at"] <= end_time]

    filtered.sort(key=lambda r: r["created_at"], reverse=True)

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


@router.get("/{report_id}", response_model=CommandResponse)
async def get_report_info(report_id: int):
    """
    获取报告信息
    """
    report = next((r for r in reports_db if r["id"] == report_id), None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报告ID {report_id} 不存在"
        )
    return CommandResponse(
        success=True,
        message="获取报告信息成功",
        data=report,
    )


@router.get("/{report_id}/download")
async def download_report(report_id: int):
    """
    下载报告
    """
    report = next((r for r in reports_db if r["id"] == report_id), None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报告ID {report_id} 不存在"
        )

    if report["status"] == "processing":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="报告正在生成中，请稍后再试"
        )

    if report["status"] == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"报告生成失败: {report.get('error', '未知错误')}"
        )

    if not report["file_path"] or not os.path.exists(report["file_path"]):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="报告文件不存在或已过期"
        )

    from .devices import devices_db
    device = next((d for d in devices_db if d.id == report["device_id"]), None)
    device_name = device.name if device else "device"

    file_name = f"{device_name}_{report['report_type']}_report_{report['start_time'].strftime('%Y%m%d')}_{report['end_time'].strftime('%Y%m%d')}.pdf"

    def iterfile():
        with open(report["file_path"], mode="rb") as f:
            yield from f

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{file_name}",
            "Content-Length": str(report.get("file_size", 0)),
        },
    )


@router.post("/preview", response_model=CommandResponse)
async def preview_report(request: ReportRequest):
    """
    预览报告内容（返回JSON格式的报告数据）
    """
    from .devices import devices_db
    from .analysis import analysis_results_db
    from .data import vibration_data_db
    from .alarms import alarm_records_db

    device = next((d for d in devices_db if d.id == request.device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {request.device_id} 不存在"
        )

    if request.start_time >= request.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="开始时间必须早于结束时间"
        )

    device_analysis = [
        r for r in analysis_results_db
        if r.device_id == request.device_id
        and r.timestamp >= request.start_time
        and r.timestamp <= request.end_time
    ]

    device_data = [
        d for d in vibration_data_db
        if d.device_id == request.device_id
        and d.timestamp >= request.start_time
        and d.timestamp <= request.end_time
    ]

    device_alarms = [
        a for a in alarm_records_db
        if a.device_id == request.device_id
        and a.created_at
        and a.created_at >= request.start_time
        and a.created_at <= request.end_time
    ]

    from report_generator import ReportGenerator, ReportData as GenReportData, ISO10816Standard
    from feature_frequency import BearingParameters

    bearing_params = BearingParameters(
        roller_count=10,
        pitch_diameter=80.0,
        roller_diameter=12.0,
        contact_angle_deg=0.0,
    )

    report_data = GenReportData(
        device=device,
        analysis_results=device_analysis,
        vibration_data=device_data,
        alarm_records=device_alarms,
        bearing_params=bearing_params,
        gear_params=None,
        rpm=3000.0,
        start_time=request.start_time,
        end_time=request.end_time,
    )

    generator = ReportGenerator()
    diagnosis = generator._generate_diagnosis(report_data)

    feature_analysis = generator._get_feature_frequency_analysis(report_data)

    rms_value = None
    iso_zone = None
    if device_analysis:
        rms_value = device_analysis[-1].time_domain.rms
        iso_zone = ISO10816Standard.get_zone(rms_value, "II")

    return CommandResponse(
        success=True,
        message="报告预览成功",
        data={
            "device": device,
            "period": {
                "start": request.start_time.isoformat(),
                "end": request.end_time.isoformat(),
            },
            "statistics": {
                "data_count": len(device_data),
                "analysis_count": len(device_analysis),
                "alarm_count": len(device_alarms),
            },
            "latest_health": device_analysis[-1].health_index if device_analysis else None,
            "latest_rms": rms_value,
            "iso_zone": iso_zone[0] if iso_zone else None,
            "iso_zone_desc": iso_zone[1] if iso_zone else None,
            "diagnosis": diagnosis,
            "feature_matches": {
                "bearing": feature_analysis.get("bearing", {}).get("matches", {}) if "bearing" in feature_analysis else None,
                "gear": feature_analysis.get("gear", {}).get("matches", {}) if "gear" in feature_analysis else None,
            },
        },
    )


@router.delete("/{report_id}", response_model=CommandResponse)
async def delete_report(report_id: int):
    """
    删除报告
    """
    global reports_db

    report = next((r for r in reports_db if r["id"] == report_id), None)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"报告ID {report_id} 不存在"
        )

    if report["file_path"] and os.path.exists(report["file_path"]):
        try:
            os.remove(report["file_path"])
        except:
            pass

    reports_db = [r for r in reports_db if r["id"] != report_id]

    return CommandResponse(
        success=True,
        message="删除报告成功",
        data={"report_id": report_id},
    )


@router.get("/templates/list", response_model=CommandResponse)
async def get_report_templates():
    """
    获取可用的报告模板列表
    """
    templates = [
        {
            "id": "daily",
            "name": "日报",
            "description": "每日设备运行状态汇总",
            "default_period": "24小时",
        },
        {
            "id": "weekly",
            "name": "周报",
            "description": "每周设备运行趋势分析",
            "default_period": "7天",
        },
        {
            "id": "monthly",
            "name": "月报",
            "description": "每月设备健康评估报告",
            "default_period": "30天",
        },
        {
            "id": "diagnostic",
            "name": "诊断报告",
            "description": "故障诊断专项分析报告",
            "default_period": "自定义",
        },
        {
            "id": "comparison",
            "name": "对比报告",
            "description": "多设备运行状态对比分析",
            "default_period": "自定义",
        },
    ]

    return CommandResponse(
        success=True,
        message="获取报告模板成功",
        data={"templates": templates},
    )
