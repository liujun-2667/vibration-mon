import os
import io
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams

rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
rcParams["axes.unicode_minus"] = False

from models import (
    Device,
    AnalysisResult,
    VibrationData,
    AlarmRecord,
    TimeDomainFeatures,
    FrequencyDomainFeatures,
)
from frequency_domain import FrequencyDomain
from feature_frequency import (
    FeatureFrequency,
    BearingParameters,
    GearParameters,
)


@dataclass
class ReportData:
    device: Device
    analysis_results: List[AnalysisResult]
    vibration_data: Optional[List[VibrationData]] = None
    alarm_records: Optional[List[AlarmRecord]] = None
    bearing_params: Optional[BearingParameters] = None
    gear_params: Optional[GearParameters] = None
    rpm: float = 3000.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ISO10816Standard:
    MACHINE_CLASSES = {
        "I": {
            "name": "1类 - 小型电机",
            "description": "功率≤15kW的电动机",
            "zones": {
                "A": {"limit": 0.71, "desc": "新交付机械"},
                "B": {"limit": 2.3, "desc": "可长期运行"},
                "C": {"limit": 4.5, "desc": "可短期运行"},
                "D": {"limit": float("inf"), "desc": "停机检修"},
            },
        },
        "II": {
            "name": "2类 - 中型机械",
            "description": "功率15~75kW的电机，安装在刚性基础上的机械",
            "zones": {
                "A": {"limit": 1.12, "desc": "新交付机械"},
                "B": {"limit": 2.8, "desc": "可长期运行"},
                "C": {"limit": 7.1, "desc": "可短期运行"},
                "D": {"limit": float("inf"), "desc": "停机检修"},
            },
        },
        "III": {
            "name": "3类 - 大型机械",
            "description": "功率>75kW的电机，安装在柔性基础上的机械",
            "zones": {
                "A": {"limit": 1.8, "desc": "新交付机械"},
                "B": {"limit": 4.5, "desc": "可长期运行"},
                "C": {"limit": 11.2, "desc": "可短期运行"},
                "D": {"limit": float("inf"), "desc": "停机检修"},
            },
        },
        "IV": {
            "name": "4类 - 驱动站",
            "description": "燃气轮机和蒸汽轮机驱动站",
            "zones": {
                "A": {"limit": 1.4, "desc": "新交付机械"},
                "B": {"limit": 3.5, "desc": "可长期运行"},
                "C": {"limit": 9.0, "desc": "可短期运行"},
                "D": {"limit": float("inf"), "desc": "停机检修"},
            },
        },
    }

    @classmethod
    def get_zone(cls, rms_value: float, machine_class: str = "I") -> Tuple[str, str]:
        if machine_class not in cls.MACHINE_CLASSES:
            machine_class = "I"

        zones = cls.MACHINE_CLASSES[machine_class]["zones"]
        for zone in ["A", "B", "C", "D"]:
            if rms_value <= zones[zone]["limit"]:
                return zone, zones[zone]["desc"]
        return "D", zones["D"]["desc"]


class ReportGenerator:
    def __init__(self):
        self.freq_analyzer = FrequencyDomain()
        self.feature_freq = FeatureFrequency()
        self.iso_standard = ISO10816Standard()

    def _create_spectrum_plot(
        self,
        freqs: np.ndarray,
        amplitudes: np.ndarray,
        title: str = "频谱图",
        highlight_freqs: Optional[Dict[str, float]] = None,
    ) -> bytes:
        fig, ax = plt.subplots(figsize=(16, 6), dpi=120)
        ax.plot(freqs, amplitudes, linewidth=0.8, color="#1f77b4")

        if highlight_freqs:
            color_map = {
                "BPFO": "#ff7f0e",
                "BPFI": "#2ca02c",
                "BSF": "#d62728",
                "FTF": "#9467bd",
                "GMF": "#e377c2",
                "rotational": "#8c564b",
            }
            for name, freq in highlight_freqs.items():
                color = color_map.get(name, "#7f7f7f")
                ax.axvline(x=freq, color=color, linestyle="--", alpha=0.7, linewidth=1)
                idx = np.argmin(np.abs(freqs - freq))
                if idx < len(amplitudes):
                    ax.annotate(
                        f"{name}",
                        xy=(freq, amplitudes[idx]),
                        xytext=(freq + 5, amplitudes[idx] * 1.1),
                        color=color,
                        fontsize=9,
                        arrowprops=dict(arrowstyle="->", color=color, alpha=0.6),
                    )

        ax.set_xlabel("频率 (Hz)", fontsize=11)
        ax.set_ylabel("幅值 (mm/s)", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    def _create_trend_plot(
        self,
        timestamps: List[datetime],
        values: List[float],
        title: str = "趋势图",
        ylabel: str = "RMS值 (mm/s)",
        warning_threshold: Optional[float] = None,
        alarm_threshold: Optional[float] = None,
    ) -> bytes:
        fig, ax = plt.subplots(figsize=(16, 5), dpi=120)
        ax.plot(timestamps, values, marker="o", markersize=4, linewidth=1.5, color="#1f77b4")

        if warning_threshold:
            ax.axhline(y=warning_threshold, color="#ff7f0e", linestyle="--", alpha=0.7, label=f"警告阈值: {warning_threshold}")
        if alarm_threshold:
            ax.axhline(y=alarm_threshold, color="#d62728", linestyle="--", alpha=0.7, label=f"报警阈值: {alarm_threshold}")

        ax.set_xlabel("时间", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best")

        fig.autofmt_xdate()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    def _create_time_waveform_plot(
        self,
        t: np.ndarray,
        signal: np.ndarray,
        title: str = "时域波形",
    ) -> bytes:
        fig, ax = plt.subplots(figsize=(16, 4), dpi=120)
        ax.plot(t, signal, linewidth=0.6, color="#1f77b4")
        ax.set_xlabel("时间 (s)", fontsize=11)
        ax.set_ylabel("幅值 (mm/s)", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf.getvalue()

    def _get_styles(self) -> Dict[str, ParagraphStyle]:
        styles = getSampleStyleSheet()
        custom_styles = {
            "title": ParagraphStyle(
                "CustomTitle",
                parent=styles["Title"],
                fontSize=20,
                textColor=colors.HexColor("#1a365d"),
                alignment=TA_CENTER,
                spaceAfter=10,
            ),
            "subtitle": ParagraphStyle(
                "CustomSubtitle",
                parent=styles["Heading2"],
                fontSize=14,
                textColor=colors.HexColor("#2b6cb0"),
                alignment=TA_CENTER,
                spaceAfter=20,
            ),
            "heading1": ParagraphStyle(
                "CustomHeading1",
                parent=styles["Heading1"],
                fontSize=14,
                textColor=colors.HexColor("#1a365d"),
                spaceBefore=12,
                spaceAfter=8,
                borderWidth=1,
                borderColor=colors.HexColor("#3182ce"),
                borderPadding=6,
                borderRadius=4,
                backColor=colors.HexColor("#ebf8ff"),
            ),
            "heading2": ParagraphStyle(
                "CustomHeading2",
                parent=styles["Heading2"],
                fontSize=12,
                textColor=colors.HexColor("#2b6cb0"),
                spaceBefore=10,
                spaceAfter=6,
            ),
            "body": ParagraphStyle(
                "CustomBody",
                parent=styles["BodyText"],
                fontSize=10,
                textColor=colors.HexColor("#2d3748"),
                alignment=TA_JUSTIFY,
                spaceAfter=6,
                leading=14,
            ),
            "table_header": ParagraphStyle(
                "TableHeader",
                parent=styles["BodyText"],
                fontSize=10,
                textColor=colors.white,
                alignment=TA_CENTER,
                fontName="Helvetica-Bold",
            ),
            "table_cell": ParagraphStyle(
                "TableCell",
                parent=styles["BodyText"],
                fontSize=9,
                textColor=colors.HexColor("#2d3748"),
                alignment=TA_CENTER,
            ),
            "footer": ParagraphStyle(
                "CustomFooter",
                parent=styles["BodyText"],
                fontSize=8,
                textColor=colors.HexColor("#718096"),
                alignment=TA_CENTER,
            ),
        }
        return custom_styles

    def _get_iso_table_data(self) -> List[List]:
        header = [
            Paragraph("机械设备类别", self._get_styles()["table_header"]),
            Paragraph("描述", self._get_styles()["table_header"]),
            Paragraph("A区(良好)<br/>≤mm/s", self._get_styles()["table_header"]),
            Paragraph("B区(合格)<br/>≤mm/s", self._get_styles()["table_header"]),
            Paragraph("C区(注意)<br/>≤mm/s", self._get_styles()["table_header"]),
            Paragraph("D区(危险)<br/>>mm/s", self._get_styles()["table_header"]),
        ]

        data = [header]
        for class_id, class_info in ISO10816Standard.MACHINE_CLASSES.items():
            zones = class_info["zones"]
            row = [
                Paragraph(f"{class_info['name']}", self._get_styles()["table_cell"]),
                Paragraph(class_info["description"], self._get_styles()["table_cell"]),
                Paragraph(f"≤{zones['A']['limit']}", self._get_styles()["table_cell"]),
                Paragraph(f"≤{zones['B']['limit']}", self._get_styles()["table_cell"]),
                Paragraph(f"≤{zones['C']['limit']}", self._get_styles()["table_cell"]),
                Paragraph(f">{zones['C']['limit']}", self._get_styles()["table_cell"]),
            ]
            data.append(row)
        return data

    def _create_iso_table(self) -> Table:
        table_data = self._get_iso_table_data()
        table = Table(table_data, colWidths=[30 * mm, 45 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm])

        style = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3182ce")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ])
        table.setStyle(style)
        return table

    def _get_feature_frequency_analysis(self, report_data: ReportData) -> Dict[str, Any]:
        if not report_data.analysis_results:
            return {}

        latest_result = report_data.analysis_results[-1]
        if not report_data.vibration_data:
            return {}

        latest_data = report_data.vibration_data[-1]
        signal = np.array(latest_data.data)
        sample_rate = latest_data.sample_rate

        freqs, amplitudes = self.freq_analyzer.compute_spectrum(
            signal, window_size=2048, overlap=0.5
        )

        theoretical_freqs = {}
        feature_analysis = {}

        if report_data.bearing_params:
            bearing_freqs = self.feature_freq.calculate_bearing_frequencies(
                report_data.bearing_params, report_data.rpm
            )
            theoretical_freqs.update({
                "BPFO": bearing_freqs["BPFO"],
                "BPFI": bearing_freqs["BPFI"],
                "BSF": bearing_freqs["BSF"],
                "FTF": bearing_freqs["FTF"],
                "rotational": bearing_freqs["rotational_freq"],
            })
            feature_analysis["bearing"] = self.feature_freq.analyze_bearing_spectrum(
                freqs, amplitudes, report_data.bearing_params, report_data.rpm
            )

        if report_data.gear_params:
            gear_freqs = self.feature_freq.calculate_gear_mesh_frequency(
                report_data.gear_params
            )
            theoretical_freqs.update({
                "GMF": gear_freqs["GMF"],
                "rotational": gear_freqs["rotational_freq"],
            })
            feature_analysis["gear"] = self.feature_freq.analyze_gear_spectrum(
                freqs, amplitudes, report_data.gear_params
            )

        peak_freqs, peak_amps = self.freq_analyzer.detect_peaks(
            freqs, amplitudes, num_peaks=10
        )

        feature_analysis["spectrum"] = {
            "freqs": freqs,
            "amplitudes": amplitudes,
            "peak_freqs": peak_freqs,
            "peak_amps": peak_amps,
            "theoretical_freqs": theoretical_freqs,
        }

        return feature_analysis

    def _generate_diagnosis(self, report_data: ReportData) -> List[str]:
        diagnosis = []
        if not report_data.analysis_results:
            return ["无足够数据进行诊断分析"]

        latest = report_data.analysis_results[-1]
        health_index = latest.health_index
        status = latest.status
        anomalies = latest.anomalies
        time_domain = latest.time_domain

        if health_index >= 80:
            diagnosis.append(f"设备整体运行状态良好，健康指数 {health_index:.1f}/100。")
        elif health_index >= 60:
            diagnosis.append(f"设备运行状态正常，健康指数 {health_index:.1f}/100，建议持续监测。")
        elif health_index >= 40:
            diagnosis.append(f"设备运行状态异常，健康指数 {health_index:.1f}/100，建议进行专项检查。")
        else:
            diagnosis.append(f"设备运行状态严重异常，健康指数 {health_index:.1f}/100，建议立即停机检修。")

        zone, zone_desc = self.iso_standard.get_zone(time_domain.rms, "II")
        zone_colors = {"A": "绿色", "B": "黄色", "C": "橙色", "D": "红色"}
        diagnosis.append(f"根据ISO 10816标准，当前RMS值 {time_domain.rms:.3f} mm/s 处于{zone_colors.get(zone, '未知')}区域({zone}区)：{zone_desc}。")

        if anomalies:
            diagnosis.append("检测到以下异常特征：")
            for anomaly in anomalies:
                diagnosis.append(f"  • {anomaly}")

        if time_domain.kurtosis > 4.0:
            diagnosis.append(f"峭度值 {time_domain.kurtosis:.2f} 偏高，提示可能存在冲击性故障（如轴承磨损、齿轮点蚀等）。")

        if time_domain.crest_factor > 4.0:
            diagnosis.append(f"波峰因数 {time_domain.crest_factor:.2f} 偏高，提示可能存在局部故障。")

        feature_analysis = self._get_feature_frequency_analysis(report_data)
        if "bearing" in feature_analysis:
            bearing_matches = feature_analysis["bearing"]["matches"]
            fault_freqs = []
            for key in ["BPFO", "BPFI", "BSF", "FTF"]:
                if bearing_matches[key]["found"]:
                    fault_freqs.append(f"{key}({bearing_matches[key]['closest_freq']:.2f}Hz)")
            if fault_freqs:
                diagnosis.append(f"频谱分析检测到轴承特征频率：{', '.join(fault_freqs)}，需关注轴承磨损情况。")

        if "gear" in feature_analysis:
            gear_matches = feature_analysis["gear"]["matches"]
            if gear_matches["GMF"]["found"]:
                diagnosis.append(f"频谱分析检测到齿轮啮合频率 GMF: {gear_matches['GMF']['closest_freq']:.2f}Hz，需关注齿轮啮合状态。")

        if report_data.alarm_records:
            critical_count = sum(1 for a in report_data.alarm_records if a.alarm_level == "critical")
            warning_count = sum(1 for a in report_data.alarm_records if a.alarm_level == "warning")
            if critical_count > 0:
                diagnosis.append(f"报告周期内共发生 {critical_count} 次严重报警，{warning_count} 次警告报警。")

        if not diagnosis:
            diagnosis.append("设备运行正常，无明显异常特征。")

        return diagnosis

    def generate_report(self, report_data: ReportData, output_path: str) -> str:
        styles = self._get_styles()
        story = []

        story.append(Paragraph("设备振动分析诊断报告", styles["title"]))
        story.append(Paragraph(
            f"报告生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
            styles["subtitle"]
        ))
        story.append(Spacer(1, 8 * mm))

        story.append(Paragraph("一、设备基本信息", styles["heading1"]))
        device = report_data.device
        device_info = [
            ["设备名称", device.name, "设备编码", device.code],
            ["安装位置", device.location, "设备状态", device.status],
            ["IP地址", device.ip_address or "-", "传感器数量", str(device.sensor_count)],
            ["创建时间", device.created_at.strftime("%Y-%m-%d %H:%M:%S") if device.created_at else "-",
             "更新时间", device.updated_at.strftime("%Y-%m-%d %H:%M:%S") if device.updated_at else "-"],
            ["报告周期", f"{report_data.start_time.strftime('%Y-%m-%d') if report_data.start_time else '-'} 至 {report_data.end_time.strftime('%Y-%m-%d') if report_data.end_time else '-'}",
             "转速", f"{report_data.rpm:.0f} RPM"],
        ]
        if device.description:
            device_info.append(["设备描述", device.description, "", ""])

        device_table = Table(device_info, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
        device_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ebf8ff")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#ebf8ff")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(device_table)
        story.append(Spacer(1, 6 * mm))

        story.append(Paragraph("二、ISO 10816振动评定标准", styles["heading1"]))
        story.append(Paragraph(
            "ISO 10816是国际标准化组织制定的机械振动评估标准，通过测量轴承座处的振动速度有效值(RMS)来评估机械的运行状态。",
            styles["body"]
        ))
        story.append(Spacer(1, 3 * mm))
        story.append(self._create_iso_table())
        story.append(Spacer(1, 4 * mm))

        zone_color_map = {
            "A": colors.HexColor("#38a169"),
            "B": colors.HexColor("#ecc94b"),
            "C": colors.HexColor("#ed8936"),
            "D": colors.HexColor("#e53e3e"),
        }
        if report_data.analysis_results:
            rms_value = report_data.analysis_results[-1].time_domain.rms
            zone, zone_desc = self.iso_standard.get_zone(rms_value, "II")
            zone_color = zone_color_map.get(zone, colors.gray)
            zone_table = Table(
                [[Paragraph(f"当前RMS值: <b>{rms_value:.3f} mm/s</b>", styles["body"]),
                  Paragraph(f"评定区域: <font color='{zone_color.hexval()}'><b>{zone}区 - {zone_desc}</b></font>", styles["body"])]],
                colWidths=[85 * mm, 85 * mm]
            )
            zone_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fff4")),
                ("BOX", (0, 0), (-1, -1), 1, zone_color),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ]))
            story.append(zone_table)
        story.append(Spacer(1, 8 * mm))

        story.append(PageBreak())

        story.append(Paragraph("三、时域波形与频谱分析", styles["heading1"]))

        if report_data.vibration_data and report_data.analysis_results:
            latest_data = report_data.vibration_data[-1]
            signal = np.array(latest_data.data)
            sample_rate = latest_data.sample_rate
            t = np.linspace(0, len(signal) / sample_rate, len(signal), endpoint=False)

            waveform_img = self._create_time_waveform_plot(t, signal, "时域波形图")
            story.append(Image(io.BytesIO(waveform_img), width=170 * mm, height=45 * mm))
            story.append(Spacer(1, 4 * mm))

            feature_analysis = self._get_feature_frequency_analysis(report_data)
            if "spectrum" in feature_analysis:
                spec = feature_analysis["spectrum"]
                spectrum_img = self._create_spectrum_plot(
                    spec["freqs"], spec["amplitudes"],
                    "频谱图 (FFT)",
                    spec.get("theoretical_freqs")
                )
                story.append(Image(io.BytesIO(spectrum_img), width=170 * mm, height=65 * mm))
                story.append(Spacer(1, 4 * mm))

                if len(spec["peak_freqs"]) > 0:
                    story.append(Paragraph("主要频谱峰值:", styles["heading2"]))
                    peak_data = [
                        [Paragraph("序号", styles["table_header"]),
                         Paragraph("频率 (Hz)", styles["table_header"]),
                         Paragraph("幅值 (mm/s)", styles["table_header"])],
                    ]
                    for i, (f, a) in enumerate(zip(spec["peak_freqs"][:8], spec["peak_amps"][:8]), 1):
                        peak_data.append([
                            Paragraph(str(i), styles["table_cell"]),
                            Paragraph(f"{f:.2f}", styles["table_cell"]),
                            Paragraph(f"{a:.4f}", styles["table_cell"]),
                        ])
                    peak_table = Table(peak_data, colWidths=[20 * mm, 50 * mm, 50 * mm], hAlign="LEFT")
                    peak_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3182ce")),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(peak_table)
        else:
            story.append(Paragraph("暂无振动数据用于分析", styles["body"]))
        story.append(Spacer(1, 8 * mm))

        story.append(PageBreak())

        story.append(Paragraph("四、特征频率分析", styles["heading1"]))

        feature_analysis = self._get_feature_frequency_analysis(report_data)

        if report_data.bearing_params and "bearing" in feature_analysis:
            story.append(Paragraph("4.1 轴承特征频率分析", styles["heading2"]))
            bearing_data = feature_analysis["bearing"]
            theoretical = bearing_data["theoretical_frequencies"]
            matches = bearing_data["matches"]

            bearing_freq_data = [
                [Paragraph("特征频率", styles["table_header"]),
                 Paragraph("理论值 (Hz)", styles["table_header"]),
                 Paragraph("理论值 (RPM)", styles["table_header"]),
                 Paragraph("实测值 (Hz)", styles["table_header"]),
                 Paragraph("是否匹配", styles["table_header"]),
                 Paragraph("偏差 (%)", styles["table_header"])],
            ]
            for key, label in [("BPFO", "外圈故障频率"), ("BPFI", "内圈故障频率"),
                               ("BSF", "滚动体故障频率"), ("FTF", "保持架故障频率")]:
                match = matches[key]
                found_text = "是" if match["found"] else "否"
                found_color = colors.HexColor("#38a169") if match["found"] else colors.HexColor("#e53e3e")
                bearing_freq_data.append([
                    Paragraph(f"{key}<br/><font size=8>{label}</font>", styles["table_cell"]),
                    Paragraph(f"{theoretical[key]:.2f}", styles["table_cell"]),
                    Paragraph(f"{theoretical[f'{key}_rpm']:.1f}", styles["table_cell"]),
                    Paragraph(f"{match['closest_freq']:.2f}", styles["table_cell"]),
                    Paragraph(f"<font color='{found_color.hexval()}'>{found_text}</font>", styles["table_cell"]),
                    Paragraph(f"{match['deviation_percent']:.2f}", styles["table_cell"]),
                ])
            bearing_table = Table(bearing_freq_data, colWidths=[30 * mm, 25 * mm, 25 * mm, 25 * mm, 20 * mm, 20 * mm])
            bearing_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3182ce")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(bearing_table)
            story.append(Spacer(1, 4 * mm))

        if report_data.gear_params and "gear" in feature_analysis:
            story.append(Paragraph("4.2 齿轮特征频率分析", styles["heading2"]))
            gear_data = feature_analysis["gear"]
            theoretical = gear_data["theoretical_frequencies"]
            matches = gear_data["matches"]

            gear_freq_data = [
                [Paragraph("特征频率", styles["table_header"]),
                 Paragraph("理论值 (Hz)", styles["table_header"]),
                 Paragraph("实测值 (Hz)", styles["table_header"]),
                 Paragraph("是否匹配", styles["table_header"]),
                 Paragraph("偏差 (%)", styles["table_header"])],
            ]
            for key, label in [("rotational", "转动频率"), ("GMF", "齿轮啮合频率"),
                               ("GMF_2x", "2倍啮合频率"), ("GMF_3x", "3倍啮合频率")]:
                match = matches[key]
                found_text = "是" if match["found"] else "否"
                found_color = colors.HexColor("#38a169") if match["found"] else colors.HexColor("#e53e3e")
                gear_freq_data.append([
                    Paragraph(f"{key}<br/><font size=8>{label}</font>", styles["table_cell"]),
                    Paragraph(f"{theoretical.get(key, theoretical.get('GMF', 0) * (int(key.split('_')[-1][0]) if 'x' in key else 1)):.2f}", styles["table_cell"]),
                    Paragraph(f"{match['closest_freq']:.2f}", styles["table_cell"]),
                    Paragraph(f"<font color='{found_color.hexval()}'>{found_text}</font>", styles["table_cell"]),
                    Paragraph(f"{match['deviation_percent']:.2f}", styles["table_cell"]),
                ])
            gear_table = Table(gear_freq_data, colWidths=[35 * mm, 30 * mm, 30 * mm, 25 * mm, 25 * mm])
            gear_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3182ce")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(gear_table)
            story.append(Spacer(1, 4 * mm))

        story.append(Paragraph("4.3 分析结论", styles["heading2"]))
        if "bearing" in feature_analysis or "gear" in feature_analysis:
            matched_features = []
            if "bearing" in feature_analysis:
                for key in ["BPFO", "BPFI", "BSF", "FTF"]:
                    if feature_analysis["bearing"]["matches"][key]["found"]:
                        matched_features.append(key)
            if "gear" in feature_analysis:
                if feature_analysis["gear"]["matches"]["GMF"]["found"]:
                    matched_features.append("GMF")

            if matched_features:
                story.append(Paragraph(
                    f"频谱中检测到特征频率成分: {', '.join(matched_features)}。建议根据匹配情况进行针对性的故障诊断。",
                    styles["body"]
                ))
            else:
                story.append(Paragraph(
                    "频谱中未检测到明显的轴承或齿轮特征频率成分，说明设备传动部件运行状态良好。",
                    styles["body"]
                ))
        else:
            story.append(Paragraph(
                "未配置轴承或齿轮参数，无法进行特征频率匹配分析。请在设备配置中补充相关参数。",
                styles["body"]
            ))
        story.append(Spacer(1, 8 * mm))

        story.append(PageBreak())

        story.append(Paragraph("五、趋势对比分析", styles["heading1"]))

        if len(report_data.analysis_results) >= 2:
            timestamps = [r.timestamp for r in report_data.analysis_results]
            rms_values = [r.time_domain.rms for r in report_data.analysis_results]
            peak_values = [r.time_domain.peak for r in report_data.analysis_results]
            kurtosis_values = [r.time_domain.kurtosis for r in report_data.analysis_results]
            health_values = [r.health_index for r in report_data.analysis_results]

            rms_trend = self._create_trend_plot(
                timestamps, rms_values,
                "RMS值趋势图", "RMS值 (mm/s)",
                warning_threshold=2.3, alarm_threshold=4.5
            )
            story.append(Image(io.BytesIO(rms_trend), width=170 * mm, height=55 * mm))
            story.append(Spacer(1, 3 * mm))

            kurtosis_trend = self._create_trend_plot(
                timestamps, kurtosis_values,
                "峭度值趋势图", "峭度",
                warning_threshold=4.0, alarm_threshold=7.0
            )
            story.append(Image(io.BytesIO(kurtosis_trend), width=170 * mm, height=55 * mm))
            story.append(Spacer(1, 3 * mm))

            health_trend = self._create_trend_plot(
                timestamps, health_values,
                "健康指数趋势图", "健康指数 (0-100)",
                warning_threshold=60.0, alarm_threshold=40.0
            )
            story.append(Image(io.BytesIO(health_trend), width=170 * mm, height=55 * mm))
            story.append(Spacer(1, 4 * mm))

            story.append(Paragraph("趋势分析统计:", styles["heading2"]))
            stats_data = [
                [Paragraph("指标", styles["table_header"]),
                 Paragraph("最小值", styles["table_header"]),
                 Paragraph("最大值", styles["table_header"]),
                 Paragraph("平均值", styles["table_header"]),
                 Paragraph("最新值", styles["table_header"]),
                 Paragraph("变化趋势", styles["table_header"])],
            ]

            def calc_trend(values):
                if len(values) < 2:
                    return "-"
                change = values[-1] - values[0]
                if abs(change) < 0.01:
                    return "稳定"
                elif change > 0:
                    return "↑ 上升"
                else:
                    return "↓ 下降"

            for name, values in [("RMS (mm/s)", rms_values), ("峰值", peak_values),
                                 ("峭度", kurtosis_values), ("健康指数", health_values)]:
                stats_data.append([
                    Paragraph(name, styles["table_cell"]),
                    Paragraph(f"{min(values):.3f}", styles["table_cell"]),
                    Paragraph(f"{max(values):.3f}", styles["table_cell"]),
                    Paragraph(f"{np.mean(values):.3f}", styles["table_cell"]),
                    Paragraph(f"{values[-1]:.3f}", styles["table_cell"]),
                    Paragraph(calc_trend(values), styles["table_cell"]),
                ])

            stats_table = Table(stats_data, colWidths=[35 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 25 * mm])
            stats_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3182ce")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.append(stats_table)
        else:
            story.append(Paragraph(
                "分析结果数据不足(至少需要2组数据)，无法进行趋势对比分析。",
                styles["body"]
            ))
        story.append(Spacer(1, 8 * mm))

        story.append(PageBreak())

        story.append(Paragraph("六、诊断建议", styles["heading1"]))

        diagnosis = self._generate_diagnosis(report_data)
        for i, diag in enumerate(diagnosis, 1):
            story.append(Paragraph(f"{i}. {diag}", styles["body"]))
        story.append(Spacer(1, 6 * mm))

        story.append(Paragraph("维护建议:", styles["heading2"]))
        if report_data.analysis_results:
            health = report_data.analysis_results[-1].health_index
            if health >= 80:
                suggestions = [
                    "继续按正常周期进行监测，无需特殊处理。",
                    "保持现有维护计划和润滑制度。",
                    "定期校准传感器，确保数据准确性。",
                ]
            elif health >= 60:
                suggestions = [
                    "缩短监测周期，建议从每周1次增加到每周2-3次。",
                    "检查设备润滑情况，按需补充或更换润滑油。",
                    "检查设备安装基础，确认无松动。",
                    "准备备品备件，预防可能的故障。",
                ]
            elif health >= 40:
                suggestions = [
                    "立即增加监测频率，建议每日监测1次。",
                    "组织专业技术人员进行现场检查和专项诊断。",
                    "使用手持式振动仪进行复测确认。",
                    "考虑安排计划性停机检修，避免突发故障。",
                    "通知维护部门制定维修方案。",
                ]
            else:
                suggestions = [
                    "建议立即停机检修，避免造成更大损失。",
                    "启动应急预案，切换备用设备。",
                    "组织故障分析会议，确定故障原因。",
                    "制定详细的维修计划，准备所需备件。",
                    "维修完成后进行试运行和验收。",
                ]
            for i, sug in enumerate(suggestions, 1):
                story.append(Paragraph(f"  {i}. {sug}", styles["body"]))
        story.append(Spacer(1, 10 * mm))

        if report_data.alarm_records:
            story.append(Paragraph("七、报警记录摘要", styles["heading1"]))
            alarm_data = [
                [Paragraph("时间", styles["table_header"]),
                 Paragraph("类型", styles["table_header"]),
                 Paragraph("级别", styles["table_header"]),
                 Paragraph("信息", styles["table_header"]),
                 Paragraph("状态", styles["table_header"])],
            ]
            for alarm in report_data.alarm_records[:10]:
                level_color = {
                    "info": "#3182ce",
                    "warning": "#ed8936",
                    "critical": "#e53e3e",
                }.get(alarm.alarm_level, "#718096")
                status_text = "已确认" if alarm.acknowledged else "待处理"
                status_color = "#38a169" if alarm.acknowledged else "#e53e3e"
                alarm_data.append([
                    Paragraph(alarm.created_at.strftime("%m-%d %H:%M") if alarm.created_at else "-", styles["table_cell"]),
                    Paragraph(alarm.alarm_type, styles["table_cell"]),
                    Paragraph(f"<font color='{level_color}'>{alarm.alarm_level}</font>", styles["table_cell"]),
                    Paragraph(alarm.message, styles["table_cell"]),
                    Paragraph(f"<font color='{status_color}'>{status_text}</font>", styles["table_cell"]),
                ])
            alarm_table = Table(alarm_data, colWidths=[25 * mm, 25 * mm, 20 * mm, 70 * mm, 22 * mm])
            alarm_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3182ce")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(alarm_table)

        story.append(Spacer(1, 15 * mm))
        story.append(Paragraph("— 报告结束 —", styles["footer"]))

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        def add_page_number(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#718096"))
            page_num = canvas.getPageNumber()
            canvas.drawCentredString(
                A4[0] / 2,
                15 * mm,
                f"第 {page_num} 页 / 共 {doc.page} 页" if hasattr(doc, 'page') else f"第 {page_num} 页"
            )
            canvas.drawString(15 * mm, 15 * mm, "振动监测系统")
            canvas.drawRightString(A4[0] - 15 * mm, 15 * mm, datetime.now().strftime("%Y-%m-%d"))
            canvas.restoreState()

        doc.build(story, onLaterPages=add_page_number, onFirstPage=add_page_number)
        return output_path

    def generate_report_bytes(self, report_data: ReportData) -> bytes:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name

        try:
            self.generate_report(report_data, tmp_path)
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
