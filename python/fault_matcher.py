import os
import sys
import logging
import math
import numpy as np
from typing import List, Dict, Any, Tuple
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import (
    FeatureSnapshot,
    FaultModeKnowledge,
    FaultMatchResult,
    MaintenanceSuggestion,
    DiagnosisReport,
    DiagnosisTask,
    DiagnosisStatus,
    SeverityLevel,
    UrgencyLevel,
)
from database import get_database

logger = logging.getLogger(__name__)


class FaultMatcherEngine:
    def __init__(self):
        self.db = get_database()

    def extract_features(
        self,
        device_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> FeatureSnapshot:
        vibration_data, _ = self.db.get_vibration_data(
            page=1,
            page_size=1000,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
        )

        if not vibration_data:
            logger.warning(f"设备 {device_id} 在指定时间范围内没有振动数据，使用默认特征值")
            return FeatureSnapshot(
                rms_trend_slope=0.0,
                kurtosis_mean=3.0,
                dominant_frequency_offset=0.0,
                harmonic_ratio=0.1,
                peak_value=0.5,
                crest_factor=3.0,
                spectral_centroid=50.0,
                data_points_count=0,
            )

        rms_values = []
        kurtosis_values = []
        peak_values = []
        crest_values = []
        spectral_centroids = []
        dominant_frequencies = []
        harmonic_ratios = []
        time_domain_features_list = []
        frequency_domain_features_list = []

        analysis_results, _ = self.db.get_analysis_results(
            page=1,
            page_size=1000,
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
        )

        if analysis_results:
            for result in analysis_results:
                rms_values.append(result.time_domain.rms)
                kurtosis_values.append(result.time_domain.kurtosis)
                peak_values.append(result.time_domain.peak)
                crest_values.append(result.time_domain.crest_factor)
                spectral_centroids.append(result.frequency_domain.spectral_centroid)
                dominant_frequencies.append(result.frequency_domain.dominant_frequency)
                time_domain_features_list.append(result.time_domain.model_dump())
                frequency_domain_features_list.append(result.frequency_domain.model_dump())

                dom_amp = result.frequency_domain.dominant_amplitude
                harmonic_amp = result.frequency_domain.frequency_bands.get("harmonic", 0)
                if dom_amp > 0:
                    harmonic_ratios.append(harmonic_amp / dom_amp)
        else:
            from time_domain import extract_time_domain_features
            from frequency_domain import extract_frequency_domain_features

            for data in vibration_data:
                td_features = extract_time_domain_features(np.array(data.data))
                fd_features = extract_frequency_domain_features(
                    np.array(data.data), data.sample_rate
                )

                rms_values.append(td_features.rms)
                kurtosis_values.append(td_features.kurtosis)
                peak_values.append(td_features.peak)
                crest_values.append(td_features.crest_factor)
                spectral_centroids.append(fd_features.spectral_centroid)
                dominant_frequencies.append(fd_features.dominant_frequency)
                time_domain_features_list.append(td_features.model_dump())
                frequency_domain_features_list.append(fd_features.model_dump())

                dom_amp = fd_features.dominant_amplitude
                harmonic_amp = fd_features.frequency_bands.get("harmonic", 0)
                if dom_amp > 0:
                    harmonic_ratios.append(harmonic_amp / dom_amp)

        if len(rms_values) < 2:
            rms_trend_slope = 0.0
        else:
            x = np.arange(len(rms_values))
            rms_trend_slope = float(np.polyfit(x, rms_values, 1)[0])

        kurtosis_mean = float(np.mean(kurtosis_values)) if kurtosis_values else 0.0
        dominant_frequency_offset = float(np.std(dominant_frequencies)) if dominant_frequencies else 0.0
        harmonic_ratio = float(np.mean(harmonic_ratios)) if harmonic_ratios else 0.0
        peak_value = float(np.mean(peak_values)) if peak_values else 0.0
        crest_factor = float(np.mean(crest_values)) if crest_values else 0.0
        spectral_centroid = float(np.mean(spectral_centroids)) if spectral_centroids else 0.0

        avg_time_domain = {}
        if time_domain_features_list:
            keys = time_domain_features_list[0].keys()
            for key in keys:
                avg_time_domain[key] = float(np.mean([f[key] for f in time_domain_features_list]))

        avg_frequency_domain = {}
        if frequency_domain_features_list:
            keys = frequency_domain_features_list[0].keys()
            for key in keys:
                if key == "frequency_bands":
                    continue
                avg_frequency_domain[key] = float(np.mean([f[key] for f in frequency_domain_features_list]))

            band_keys = frequency_domain_features_list[0].get("frequency_bands", {}).keys()
            avg_frequency_domain["frequency_bands"] = {}
            for key in band_keys:
                avg_frequency_domain["frequency_bands"][key] = float(
                    np.mean([f.get("frequency_bands", {}).get(key, 0) for f in frequency_domain_features_list])
                )

        return FeatureSnapshot(
            rms_trend_slope=rms_trend_slope,
            kurtosis_mean=kurtosis_mean,
            dominant_frequency_offset=dominant_frequency_offset,
            harmonic_ratio=harmonic_ratio,
            peak_value=peak_value,
            crest_factor=crest_factor,
            spectral_centroid=spectral_centroid,
            data_points_count=len(vibration_data),
            time_domain_features=avg_time_domain,
            frequency_domain_features=avg_frequency_domain,
        )

    def match_faults(
        self,
        feature_snapshot: FeatureSnapshot,
        knowledge_base: List[FaultModeKnowledge],
    ) -> List[FaultMatchResult]:
        match_results = []

        for knowledge in knowledge_base:
            confidence, evidence = self._calculate_match_confidence(
                feature_snapshot, knowledge
            )

            if confidence > 20:
                match_results.append(
                    FaultMatchResult(
                        fault_mode_name=knowledge.name,
                        confidence=round(confidence, 1),
                        evidence=evidence,
                        severity_level=knowledge.severity_level,
                        key_frequency_features=knowledge.key_frequency_features,
                    )
                )

        match_results.sort(key=lambda x: x.confidence, reverse=True)
        return match_results

    def _calculate_match_confidence(
        self,
        features: FeatureSnapshot,
        knowledge: FaultModeKnowledge,
    ) -> Tuple[float, List[str]]:
        confidence = 0.0
        evidence = []
        fault_name = knowledge.name

        if fault_name == "转子不平衡":
            if features.peak_value > 5.0:
                confidence += 25
                evidence.append(f"峰值 {features.peak_value:.2f} mm/s 较高，表明振动剧烈")
            if features.rms_trend_slope > 0.01:
                confidence += 20
                evidence.append(f"RMS趋势斜率 {features.rms_trend_slope:.4f} 呈上升趋势")
            if features.harmonic_ratio > 0.3 and features.harmonic_ratio < 0.7:
                confidence += 15
                evidence.append(f"谐波比 {features.harmonic_ratio:.2f} 符合不平衡特征")
            if features.kurtosis_mean < 4.0:
                confidence += 10
                evidence.append(f"峭度均值 {features.kurtosis_mean:.2f} 较低，符合稳态不平衡特征")
            if features.dominant_frequency_offset < 2.0:
                confidence += 15
                evidence.append(f"主频偏移 {features.dominant_frequency_offset:.2f} Hz 较小，相位稳定")

        elif fault_name == "轴不对中":
            if features.harmonic_ratio > 0.6:
                confidence += 30
                evidence.append(f"谐波比 {features.harmonic_ratio:.2f} 较高，2X频率分量显著")
            if features.peak_value > 4.0:
                confidence += 20
                evidence.append(f"峰值 {features.peak_value:.2f} mm/s 较高")
            if features.rms_trend_slope > 0.005:
                confidence += 15
                evidence.append(f"RMS趋势呈上升趋势 ({features.rms_trend_slope:.4f})")
            if features.spectral_centroid > 100:
                confidence += 10
                evidence.append(f"频谱质心 {features.spectral_centroid:.1f} Hz 偏高")

        elif fault_name == "机械松动":
            if features.kurtosis_mean > 4.5:
                confidence += 25
                evidence.append(f"峭度均值 {features.kurtosis_mean:.2f} 较高，表明有冲击成分")
            if features.crest_factor > 6.0:
                confidence += 20
                evidence.append(f"波峰因数 {features.crest_factor:.2f} 较高")
            if features.harmonic_ratio > 0.8:
                confidence += 20
                evidence.append(f"谐波比 {features.harmonic_ratio:.2f} 很高，存在大量谐波")
            if features.dominant_frequency_offset > 3.0:
                confidence += 15
                evidence.append(f"主频偏移 {features.dominant_frequency_offset:.2f} Hz 较大，振动不稳定")

        elif fault_name == "滚动轴承外圈缺陷":
            if features.kurtosis_mean > 5.0:
                confidence += 30
                evidence.append(f"峭度均值 {features.kurtosis_mean:.2f} 很高，典型的轴承故障特征")
            if features.crest_factor > 7.0:
                confidence += 25
                evidence.append(f"波峰因数 {features.crest_factor:.2f} 很高，存在周期性冲击")
            if features.peak_value > 6.0:
                confidence += 15
                evidence.append(f"峰值 {features.peak_value:.2f} mm/s 较高")
            if features.spectral_centroid > 150:
                confidence += 10
                evidence.append(f"频谱质心 {features.spectral_centroid:.1f} Hz 较高，高频成分丰富")

        elif fault_name == "齿轮磨损":
            if features.harmonic_ratio > 0.5:
                confidence += 25
                evidence.append(f"谐波比 {features.harmonic_ratio:.2f} 较高，存在啮合频率谐波")
            if features.spectral_centroid > 120:
                confidence += 20
                evidence.append(f"频谱质心 {features.spectral_centroid:.1f} Hz 较高，边带丰富")
            if features.kurtosis_mean > 3.5:
                confidence += 15
                evidence.append(f"峭度均值 {features.kurtosis_mean:.2f} 略高")
            if features.rms_trend_slope > 0.008:
                confidence += 15
                evidence.append(f"RMS趋势呈上升趋势 ({features.rms_trend_slope:.4f})")

        elif fault_name == "共振":
            if features.peak_value > 8.0:
                confidence += 35
                evidence.append(f"峰值 {features.peak_value:.2f} mm/s 很高，共振特征明显")
            if features.dominant_frequency_offset > 5.0:
                confidence += 25
                evidence.append(f"主频偏移 {features.dominant_frequency_offset:.2f} Hz 较大，频率随转速变化")
            if features.crest_factor > 8.0:
                confidence += 20
                evidence.append(f"波峰因数 {features.crest_factor:.2f} 很高")
            if features.spectral_centroid > 200:
                confidence += 10
                evidence.append(f"频谱质心 {features.spectral_centroid:.1f} Hz 很高")

        else:
            if features.kurtosis_mean > 4.0:
                confidence += 15
                evidence.append(f"峭度均值 {features.kurtosis_mean:.2f} 偏高")
            if features.peak_value > 5.0:
                confidence += 15
                evidence.append(f"峰值 {features.peak_value:.2f} mm/s 偏高")
            if features.rms_trend_slope > 0.01:
                confidence += 10
                evidence.append(f"RMS趋势呈上升趋势 ({features.rms_trend_slope:.4f})")

        confidence = min(confidence, 98.0)
        return confidence, evidence

    def generate_maintenance_suggestions(
        self,
        match_results: List[FaultMatchResult],
        knowledge_base: List[FaultModeKnowledge],
    ) -> List[MaintenanceSuggestion]:
        suggestions = []

        knowledge_dict = {k.name: k for k in knowledge_base}

        for result in match_results[:3]:
            knowledge = knowledge_dict.get(result.fault_mode_name)
            if not knowledge:
                continue

            urgency = self._determine_urgency(result.confidence, result.severity_level)
            impact = self._generate_impact(result.fault_mode_name, result.confidence)

            suggestions.append(
                MaintenanceSuggestion(
                    action=knowledge.maintenance_action,
                    urgency=urgency,
                    expected_impact=impact,
                )
            )

        if not suggestions:
            suggestions.append(
                MaintenanceSuggestion(
                    action="继续观察运行状态",
                    urgency=UrgencyLevel.OBSERVE,
                    expected_impact="当前未发现明显故障特征，建议定期监测",
                )
            )

        return suggestions

    def _determine_urgency(
        self,
        confidence: float,
        severity: SeverityLevel,
    ) -> UrgencyLevel:
        severity_weight = {
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }

        score = confidence * severity_weight[severity] / 100

        if score >= 3.0 or confidence >= 85:
            return UrgencyLevel.IMMEDIATE
        elif score >= 1.5 or confidence >= 50:
            return UrgencyLevel.PLANNED
        else:
            return UrgencyLevel.OBSERVE

    def _generate_impact(self, fault_name: str, confidence: float) -> str:
        base_impacts = {
            "转子不平衡": "如不及时处理，可能导致轴承磨损加剧、联轴器损坏，严重时可能引发轴系断裂",
            "轴不对中": "可能导致轴承过载、密封失效、联轴器损坏，长期运行会缩短设备寿命",
            "机械松动": "可能导致部件磨损加剧、连接螺栓断裂，严重时可能引发设备振动失控",
            "滚动轴承外圈缺陷": "轴承可能在短期内失效，导致设备停机，建议尽快更换",
            "齿轮磨损": "可能导致传动效率下降、噪音增大，严重时可能发生断齿事故",
            "共振": "可能导致结构疲劳损坏、连接部件松动，严重时可能引发灾难性故障",
        }

        base = base_impacts.get(
            fault_name, "可能导致设备运行状况恶化，建议进一步检查确认"
        )

        if confidence >= 80:
            return f"置信度 {confidence:.1f}%，风险很高。{base}"
        elif confidence >= 50:
            return f"置信度 {confidence:.1f}%，存在一定风险。{base}"
        else:
            return f"置信度 {confidence:.1f}%，可能性较低。{base}"

    def generate_diagnosis_report(
        self,
        task: DiagnosisTask,
        device_info: Dict[str, Any],
    ) -> DiagnosisReport:
        if not task.feature_snapshot or not task.match_results:
            raise ValueError("诊断任务尚未完成，无法生成报告")

        knowledge_base = self.db.get_all_fault_knowledge()

        maintenance_suggestions = self.generate_maintenance_suggestions(
            task.match_results, knowledge_base
        )

        return DiagnosisReport(
            task_id=task.id,
            device_info=device_info,
            time_range={
                "start": task.start_time,
                "end": task.end_time,
            },
            feature_snapshot=task.feature_snapshot,
            fault_match_results=task.match_results,
            maintenance_suggestions=maintenance_suggestions,
        )

    def run_diagnosis(self, task_id: int) -> DiagnosisTask:
        task = self.db.get_diagnosis_task(task_id)
        if not task:
            raise ValueError(f"诊断任务 {task_id} 不存在")

        try:
            feature_snapshot = self.extract_features(
                task.device_id,
                task.start_time,
                task.end_time,
            )

            knowledge_base = self.db.get_all_fault_knowledge()
            match_results = self.match_faults(feature_snapshot, knowledge_base)

            updated_task = self.db.update_diagnosis_task(
                task_id,
                status=DiagnosisStatus.COMPLETED,
                feature_snapshot=feature_snapshot,
                match_results=match_results,
            )

            logger.info(f"诊断任务 {task_id} 完成，匹配到 {len(match_results)} 个故障模式")
            return updated_task

        except Exception as e:
            logger.error(f"诊断任务 {task_id} 失败: {e}", exc_info=True)
            self.db.update_diagnosis_task(task_id, status=DiagnosisStatus.FAILED)
            raise


_matcher_instance = None


def get_fault_matcher() -> FaultMatcherEngine:
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = FaultMatcherEngine()
    return _matcher_instance
