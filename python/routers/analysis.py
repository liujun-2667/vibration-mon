from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status
import numpy as np

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    CommandResponse,
    PaginatedResponse,
    AnalysisRequest,
    AnalysisResult,
    TimeDomainFeatures,
    FrequencyDomainFeatures,
)

router = APIRouter()

analysis_results_db: List[AnalysisResult] = []
_analysis_id_counter = 1


def _init_sample_analysis():
    global _analysis_id_counter

    now = datetime.now()
    samples = []

    for i in range(6):
        base_time = now - timedelta(hours=6 - i)
        base_rms = 1.8 + i * 0.15
        result = AnalysisResult(
            id=_analysis_id_counter + i,
            device_id=1,
            data_id=100 + i,
            channel=0,
            timestamp=base_time,
            time_domain=TimeDomainFeatures(
                rms=base_rms,
                peak=base_rms * 2.5,
                peak_to_peak=base_rms * 4.8,
                crest_factor=2.5 + i * 0.1,
                kurtosis=3.0 + i * 0.3,
                skewness=0.1 + i * 0.05,
                mean=0.02 + i * 0.01,
                variance=base_rms ** 2,
                standard_deviation=base_rms,
            ),
            frequency_domain=FrequencyDomainFeatures(
                dominant_frequency=50.0 + i * 0.5,
                dominant_amplitude=0.8 + i * 0.1,
                frequency_bands={
                    "low_0-100Hz": 0.6 + i * 0.05,
                    "mid_100-500Hz": 0.3 + i * 0.03,
                    "high_500-1000Hz": 0.15 + i * 0.02,
                },
                spectral_centroid=150.0 + i * 5,
                spectral_rolloff=400.0 + i * 10,
                spectral_spread=80.0 + i * 3,
            ),
            health_index=90 - i * 3,
            status="正常" if i < 4 else ("注意" if i < 5 else "异常"),
            anomalies=["峭度值偏高"] if i >= 4 else [],
            created_at=base_time,
        )
        samples.append(result)

    analysis_results_db.extend(samples)
    _analysis_id_counter += len(samples)


_init_sample_analysis()


def _extract_time_domain_features(signal: np.ndarray) -> TimeDomainFeatures:
    rms = float(np.sqrt(np.mean(signal ** 2)))
    peak = float(np.max(np.abs(signal)))
    peak_to_peak = float(np.max(signal) - np.min(signal))
    crest_factor = peak / rms if rms > 0 else 0.0
    mean = float(np.mean(signal))
    std = float(np.std(signal))
    if std > 0:
        normalized = (signal - mean) / std
        kurtosis = float(np.mean(normalized ** 4))
        skewness = float(np.mean(normalized ** 3))
    else:
        kurtosis = 0.0
        skewness = 0.0

    return TimeDomainFeatures(
        rms=rms,
        peak=peak,
        peak_to_peak=peak_to_peak,
        crest_factor=crest_factor,
        kurtosis=kurtosis,
        skewness=skewness,
        mean=mean,
        variance=std ** 2,
        standard_deviation=std,
    )


def _extract_frequency_domain_features(
    signal: np.ndarray, sample_rate: int
) -> FrequencyDomainFeatures:
    from frequency_domain import FrequencyDomain

    analyzer = FrequencyDomain(sample_rate=sample_rate)
    freqs, amplitudes = analyzer.compute_spectrum(signal, window_size=2048)

    if len(amplitudes) > 0:
        dominant_idx = int(np.argmax(amplitudes))
        dominant_frequency = float(freqs[dominant_idx])
        dominant_amplitude = float(amplitudes[dominant_idx])
    else:
        dominant_frequency = 0.0
        dominant_amplitude = 0.0

    nyquist = sample_rate / 2
    bands = {
        "low_0-100Hz": 0.0,
        "mid_100-500Hz": 0.0,
        "high_500-1000Hz": 0.0,
    }

    if len(freqs) > 0 and len(amplitudes) > 0:
        mask_low = freqs <= 100
        if np.any(mask_low):
            bands["low_0-100Hz"] = float(np.sum(amplitudes[mask_low] ** 2))

        mask_mid = (freqs > 100) & (freqs <= 500)
        if np.any(mask_mid):
            bands["mid_100-500Hz"] = float(np.sum(amplitudes[mask_mid] ** 2))

        mask_high = (freqs > 500) & (freqs <= 1000)
        if np.any(mask_high):
            bands["high_500-1000Hz"] = float(np.sum(amplitudes[mask_high] ** 2))

    total_energy = sum(bands.values())
    if total_energy > 0:
        spectral_centroid = float(
            np.sum(freqs * amplitudes ** 2) / np.sum(amplitudes ** 2)
        ) if np.sum(amplitudes ** 2) > 0 else 0.0

        cumulative = np.cumsum(amplitudes ** 2)
        if len(cumulative) > 0:
            rolloff_idx = np.where(cumulative >= 0.85 * cumulative[-1])[0]
            spectral_rolloff = float(freqs[rolloff_idx[0]]) if len(rolloff_idx) > 0 else float(freqs[-1])
        else:
            spectral_rolloff = 0.0

        spectral_spread = float(
            np.sqrt(np.sum(((freqs - spectral_centroid) ** 2) * (amplitudes ** 2)) / np.sum(amplitudes ** 2))
        ) if np.sum(amplitudes ** 2) > 0 else 0.0
    else:
        spectral_centroid = 0.0
        spectral_rolloff = 0.0
        spectral_spread = 0.0

    return FrequencyDomainFeatures(
        dominant_frequency=dominant_frequency,
        dominant_amplitude=dominant_amplitude,
        frequency_bands=bands,
        spectral_centroid=spectral_centroid,
        spectral_rolloff=spectral_rolloff,
        spectral_spread=spectral_spread,
    )


def _calculate_health_index(
    time_domain: TimeDomainFeatures,
    freq_domain: FrequencyDomainFeatures,
) -> tuple[float, str, List[str]]:
    score = 100.0
    anomalies = []

    rms = time_domain.rms
    if rms > 4.5:
        score -= 30
        anomalies.append("RMS值严重超标")
    elif rms > 2.3:
        score -= 15
        anomalies.append("RMS值超过警告阈值")
    elif rms > 1.12:
        score -= 5

    kurtosis = time_domain.kurtosis
    if kurtosis > 7.0:
        score -= 25
        anomalies.append("峭度值严重偏高，可能存在严重冲击故障")
    elif kurtosis > 4.0:
        score -= 12
        anomalies.append("峭度值偏高，可能存在冲击性故障")

    crest = time_domain.crest_factor
    if crest > 6.0:
        score -= 20
        anomalies.append("波峰因数严重偏高")
    elif crest > 4.0:
        score -= 10
        anomalies.append("波峰因数偏高")

    score = max(0.0, min(100.0, score))

    if score >= 80:
        status = "良好"
    elif score >= 60:
        status = "正常"
    elif score >= 40:
        status = "注意"
    else:
        status = "异常"

    return score, status, anomalies


@router.post("", response_model=CommandResponse)
async def analyze_vibration(request: AnalysisRequest):
    """
    执行振动数据分析
    """
    global _analysis_id_counter

    from .devices import devices_db

    device = next((d for d in devices_db if d.id == request.device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {request.device_id} 不存在"
        )

    if len(request.data) < 256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="振动数据长度不足，至少需要256个采样点"
        )

    signal = np.array(request.data, dtype=np.float64)

    time_domain = _extract_time_domain_features(signal)
    freq_domain = _extract_frequency_domain_features(signal, request.sample_rate)

    health_index, status, anomalies = _calculate_health_index(time_domain, freq_domain)

    now = datetime.now()
    result = AnalysisResult(
        id=_analysis_id_counter,
        device_id=request.device_id,
        data_id=None,
        channel=request.channel,
        timestamp=now,
        time_domain=time_domain,
        frequency_domain=freq_domain,
        hht_features=None,
        health_index=health_index,
        status=status,
        anomalies=anomalies,
        created_at=now,
    )

    analysis_results_db.append(result)
    _analysis_id_counter += 1

    from .alarms import alarm_rules_db, alarm_records_db, _record_id_counter
    global _record_id_counter

    for rule in alarm_rules_db:
        if rule.device_id != request.device_id or not rule.enabled:
            continue

        actual_value = None
        if rule.parameter == "rms":
            actual_value = time_domain.rms
        elif rule.parameter == "kurtosis":
            actual_value = time_domain.kurtosis
        elif rule.parameter == "crest_factor":
            actual_value = time_domain.crest_factor
        elif rule.parameter == "peak":
            actual_value = time_domain.peak

        if actual_value is None:
            continue

        triggered = False
        if rule.operator == ">" and actual_value > rule.threshold:
            triggered = True
        elif rule.operator == ">=" and actual_value >= rule.threshold:
            triggered = True
        elif rule.operator == "<" and actual_value < rule.threshold:
            triggered = True
        elif rule.operator == "<=" and actual_value <= rule.threshold:
            triggered = True

        if triggered:
            from models import AlarmRecord, AlarmLevel, AlarmType
            from .alarms import _record_id_counter as alarm_record_id
            alarm_record = AlarmRecord(
                id=alarm_record_id,
                device_id=request.device_id,
                rule_id=rule.id,
                alarm_type=rule.alarm_type,
                alarm_level=rule.alarm_level,
                message=f"{rule.name}: {actual_value:.4f} {rule.operator} {rule.threshold}",
                parameter=rule.parameter,
                actual_value=actual_value,
                threshold=rule.threshold,
                acknowledged=False,
                acknowledged_at=None,
                created_at=now,
            )
            alarm_records_db.append(alarm_record)
            from .alarms import _record_id_counter
            _record_id_counter += 1

    return CommandResponse(
        success=True,
        message="振动分析完成",
        data=result,
    )


@router.get("/results", response_model=PaginatedResponse)
async def get_analysis_results(
    page: int = 1,
    page_size: int = 10,
    device_id: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    min_health_index: Optional[float] = None,
):
    """
    获取分析结果历史
    """
    filtered = analysis_results_db

    if device_id:
        filtered = [r for r in filtered if r.device_id == device_id]

    if start_time:
        filtered = [r for r in filtered if r.timestamp >= start_time]

    if end_time:
        filtered = [r for r in filtered if r.timestamp <= end_time]

    if min_health_index is not None:
        filtered = [r for r in filtered if r.health_index >= min_health_index]

    filtered.sort(key=lambda r: r.timestamp, reverse=True)

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


@router.get("/results/{result_id}", response_model=CommandResponse)
async def get_analysis_result(result_id: int):
    """
    获取分析结果详情
    """
    result = next((r for r in analysis_results_db if r.id == result_id), None)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"分析结果ID {result_id} 不存在"
        )
    return CommandResponse(
        success=True,
        message="获取分析结果成功",
        data=result,
    )


@router.get("/{device_id}/latest", response_model=CommandResponse)
async def get_latest_analysis(device_id: int):
    """
    获取设备最新分析结果
    """
    from .devices import devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    device_results = [r for r in analysis_results_db if r.device_id == device_id]
    if not device_results:
        return CommandResponse(
            success=True,
            message="设备暂无分析结果",
            data=None,
        )

    latest = max(device_results, key=lambda r: r.timestamp)
    return CommandResponse(
        success=True,
        message="获取最新分析结果成功",
        data=latest,
    )


@router.get("/{device_id}/trend", response_model=CommandResponse)
async def get_analysis_trend(
    device_id: int,
    hours: int = 24,
    metric: str = "rms",
):
    """
    获取设备分析趋势数据
    """
    from .devices import devices_db

    device = next((d for d in devices_db if d.id == device_id), None)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"设备ID {device_id} 不存在"
        )

    start_time = datetime.now() - timedelta(hours=hours)
    device_results = [
        r for r in analysis_results_db
        if r.device_id == device_id and r.timestamp >= start_time
    ]
    device_results.sort(key=lambda r: r.timestamp)

    if not device_results:
        return CommandResponse(
            success=True,
            message="无趋势数据",
            data={"timestamps": [], "values": []},
        )

    timestamps = [r.timestamp.isoformat() for r in device_results]
    values = []

    for r in device_results:
        if metric == "rms":
            values.append(r.time_domain.rms)
        elif metric == "peak":
            values.append(r.time_domain.peak)
        elif metric == "kurtosis":
            values.append(r.time_domain.kurtosis)
        elif metric == "crest_factor":
            values.append(r.time_domain.crest_factor)
        elif metric == "health_index":
            values.append(r.health_index)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的指标: {metric}，支持: rms, peak, kurtosis, crest_factor, health_index"
            )

    return CommandResponse(
        success=True,
        message="获取趋势数据成功",
        data={
            "device_id": device_id,
            "metric": metric,
            "time_window_hours": hours,
            "timestamps": timestamps,
            "values": values,
            "statistics": {
                "min": float(np.min(values)) if values else 0,
                "max": float(np.max(values)) if values else 0,
                "avg": float(np.mean(values)) if values else 0,
                "latest": values[-1] if values else 0,
            },
        },
    )


@router.post("/batch", response_model=CommandResponse)
async def batch_analyze(requests: List[AnalysisRequest]):
    """
    批量执行振动数据分析
    """
    if len(requests) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="批量分析最多支持100条数据"
        )

    results = []
    for req in requests:
        try:
            resp = await analyze_vibration(req)
            if resp.success and resp.data:
                results.append(resp.data)
        except Exception as e:
            results.append({"error": str(e)})

    return CommandResponse(
        success=True,
        message=f"批量分析完成，成功 {len(results)} 条",
        data={"results": results},
    )


@router.get("/features/compare", response_model=CommandResponse)
async def compare_features(
    device_ids: List[int],
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    """
    多设备特征对比
    """
    from .devices import devices_db

    comparison_data = []

    for device_id in device_ids:
        device = next((d for d in devices_db if d.id == device_id), None)
        if not device:
            continue

        device_results = [
            r for r in analysis_results_db
            if r.device_id == device_id
        ]

        if start_time:
            device_results = [r for r in device_results if r.timestamp >= start_time]
        if end_time:
            device_results = [r for r in device_results if r.timestamp <= end_time]

        if not device_results:
            comparison_data.append({
                "device_id": device_id,
                "device_name": device.name,
                "data_available": False,
            })
            continue

        latest = max(device_results, key=lambda r: r.timestamp)
        avg_rms = np.mean([r.time_domain.rms for r in device_results])
        avg_health = np.mean([r.health_index for r in device_results])

        comparison_data.append({
            "device_id": device_id,
            "device_name": device.name,
            "data_available": True,
            "latest_health_index": latest.health_index,
            "latest_status": latest.status,
            "avg_rms": float(avg_rms),
            "avg_health_index": float(avg_health),
            "latest_rms": latest.time_domain.rms,
            "latest_kurtosis": latest.time_domain.kurtosis,
            "anomaly_count": len(latest.anomalies),
            "analysis_count": len(device_results),
        })

    return CommandResponse(
        success=True,
        message="设备特征对比完成",
        data={"comparison": comparison_data},
    )
