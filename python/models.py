from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    WARNING = "warning"
    ERROR = "error"


class AlarmLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlarmType(str, Enum):
    OVER_THRESHOLD = "over_threshold"
    SPECTRUM_ANOMALY = "spectrum_anomaly"
    TREND_ANOMALY = "trend_anomaly"
    CONNECTION_LOST = "connection_lost"


class Device(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="设备ID")
    name: str = Field(..., description="设备名称")
    code: str = Field(..., description="设备编码")
    location: str = Field(..., description="安装位置")
    status: DeviceStatus = Field(default=DeviceStatus.OFFLINE, description="设备状态")
    ip_address: Optional[str] = Field(default=None, description="IP地址")
    sensor_count: int = Field(default=1, description="传感器数量")
    description: Optional[str] = Field(default=None, description="设备描述")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")


class DeviceCreate(BaseModel):
    name: str = Field(..., description="设备名称")
    code: str = Field(..., description="设备编码")
    location: str = Field(..., description="安装位置")
    ip_address: Optional[str] = Field(default=None, description="IP地址")
    sensor_count: int = Field(default=1, description="传感器数量")
    description: Optional[str] = Field(default=None, description="设备描述")


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(default=None, description="设备名称")
    location: Optional[str] = Field(default=None, description="安装位置")
    status: Optional[DeviceStatus] = Field(default=None, description="设备状态")
    ip_address: Optional[str] = Field(default=None, description="IP地址")
    sensor_count: Optional[int] = Field(default=None, description="传感器数量")
    description: Optional[str] = Field(default=None, description="设备描述")


class SamplingParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="参数ID")
    device_id: int = Field(..., description="设备ID")
    sample_rate: int = Field(default=1000, description="采样率(Hz)")
    sample_length: int = Field(default=1024, description="采样点数")
    channel_count: int = Field(default=1, description="通道数")
    acquisition_interval: int = Field(default=1000, description="采集间隔(ms)")
    is_continuous: bool = Field(default=False, description="是否连续采集")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")


class SamplingParamsCreate(BaseModel):
    device_id: int = Field(..., description="设备ID")
    sample_rate: int = Field(default=1000, description="采样率(Hz)")
    sample_length: int = Field(default=1024, description="采样点数")
    channel_count: int = Field(default=1, description="通道数")
    acquisition_interval: int = Field(default=1000, description="采集间隔(ms)")
    is_continuous: bool = Field(default=False, description="是否连续采集")


class AlarmRule(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="规则ID")
    device_id: int = Field(..., description="设备ID")
    name: str = Field(..., description="规则名称")
    alarm_type: AlarmType = Field(..., description="报警类型")
    alarm_level: AlarmLevel = Field(default=AlarmLevel.WARNING, description="报警级别")
    parameter: str = Field(..., description="监测参数")
    threshold: float = Field(..., description="阈值")
    operator: str = Field(default=">", description="比较运算符")
    duration: int = Field(default=0, description="持续时间(秒)")
    enabled: bool = Field(default=True, description="是否启用")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")


class AlarmRuleCreate(BaseModel):
    device_id: int = Field(..., description="设备ID")
    name: str = Field(..., description="规则名称")
    alarm_type: AlarmType = Field(..., description="报警类型")
    alarm_level: AlarmLevel = Field(default=AlarmLevel.WARNING, description="报警级别")
    parameter: str = Field(..., description="监测参数")
    threshold: float = Field(..., description="阈值")
    operator: str = Field(default=">", description="比较运算符")
    duration: int = Field(default=0, description="持续时间(秒)")
    enabled: bool = Field(default=True, description="是否启用")


class AlarmRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="记录ID")
    device_id: int = Field(..., description="设备ID")
    rule_id: Optional[int] = Field(default=None, description="规则ID")
    alarm_type: AlarmType = Field(..., description="报警类型")
    alarm_level: AlarmLevel = Field(..., description="报警级别")
    message: str = Field(..., description="报警信息")
    parameter: Optional[str] = Field(default=None, description="监测参数")
    actual_value: Optional[float] = Field(default=None, description="实际值")
    threshold: Optional[float] = Field(default=None, description="阈值")
    acknowledged: bool = Field(default=False, description="是否已确认")
    acknowledged_at: Optional[datetime] = Field(default=None, description="确认时间")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")


class VibrationData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="数据ID")
    device_id: int = Field(..., description="设备ID")
    channel: int = Field(default=0, description="通道号")
    timestamp: datetime = Field(..., description="采集时间")
    sample_rate: int = Field(..., description="采样率")
    data: List[float] = Field(..., description="原始振动数据")
    created_at: Optional[datetime] = Field(default=None, description="存储时间")


class VibrationDataCreate(BaseModel):
    device_id: int = Field(..., description="设备ID")
    channel: int = Field(default=0, description="通道号")
    timestamp: datetime = Field(..., description="采集时间")
    sample_rate: int = Field(..., description="采样率")
    data: List[float] = Field(..., description="原始振动数据")


class TimeDomainFeatures(BaseModel):
    rms: float = Field(..., description="均方根值")
    peak: float = Field(..., description="峰值")
    peak_to_peak: float = Field(..., description="峰峰值")
    crest_factor: float = Field(..., description="波峰因数")
    kurtosis: float = Field(..., description="峭度")
    skewness: float = Field(..., description="偏度")
    mean: float = Field(..., description="均值")
    variance: float = Field(..., description="方差")
    standard_deviation: float = Field(..., description="标准差")


class FrequencyDomainFeatures(BaseModel):
    dominant_frequency: float = Field(..., description="主导频率")
    dominant_amplitude: float = Field(..., description="主导频率幅值")
    frequency_bands: Dict[str, float] = Field(..., description="频带能量")
    spectral_centroid: float = Field(..., description="频谱质心")
    spectral_rolloff: float = Field(..., description="频谱滚降点")
    spectral_spread: float = Field(..., description="频谱展宽")


class HHTFeatures(BaseModel):
    imf_count: int = Field(..., description="IMF分量数量")
    instantaneous_frequencies: List[List[float]] = Field(..., description="瞬时频率")
    instantaneous_amplitudes: List[List[float]] = Field(..., description="瞬时幅值")
    marginal_spectrum: List[float] = Field(..., description="边际谱")
    hilbert_spectrum: List[List[float]] = Field(..., description="希尔伯特谱")
    energy: List[float] = Field(..., description="各IMF能量")


class AnalysisResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="结果ID")
    device_id: int = Field(..., description="设备ID")
    data_id: Optional[int] = Field(default=None, description="原始数据ID")
    channel: int = Field(default=0, description="通道号")
    timestamp: datetime = Field(..., description="分析时间")
    time_domain: TimeDomainFeatures = Field(..., description="时域特征")
    frequency_domain: FrequencyDomainFeatures = Field(..., description="频域特征")
    hht_features: Optional[HHTFeatures] = Field(default=None, description="HHT分析特征")
    health_index: float = Field(..., description="健康指数(0-100)")
    status: str = Field(..., description="状态评估")
    anomalies: List[str] = Field(default_factory=list, description="异常列表")
    created_at: Optional[datetime] = Field(default=None, description="存储时间")


class AnalysisRequest(BaseModel):
    device_id: int = Field(..., description="设备ID")
    data: List[float] = Field(..., description="振动数据")
    sample_rate: int = Field(default=1000, description="采样率")
    channel: int = Field(default=0, description="通道号")
    perform_hht: bool = Field(default=True, description="是否执行HHT分析")


class ReportRequest(BaseModel):
    device_id: int = Field(..., description="设备ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    report_type: str = Field(default="daily", description="报告类型")
    format: str = Field(default="pdf", description="报告格式")


class CommandResponse(BaseModel):
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[Any] = Field(default=None, description="返回数据")


class PaginatedResponse(BaseModel):
    items: List[Any] = Field(..., description="数据列表")
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")


class DiagnosisStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UrgencyLevel(str, Enum):
    IMMEDIATE = "immediate"
    PLANNED = "planned"
    OBSERVE = "observe"


class FeatureSnapshot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rms_trend_slope: float = Field(..., description="RMS趋势斜率")
    kurtosis_mean: float = Field(..., description="峭度均值")
    dominant_frequency_offset: float = Field(..., description="主频偏移量(Hz)")
    harmonic_ratio: float = Field(..., description="谐波比")
    peak_value: float = Field(..., description="峰值")
    crest_factor: float = Field(..., description="波峰因数")
    spectral_centroid: float = Field(..., description="频谱质心")
    data_points_count: int = Field(..., description="分析数据点数")
    time_domain_features: Optional[Dict[str, float]] = Field(default=None, description="完整时域特征")
    frequency_domain_features: Optional[Dict[str, Any]] = Field(default=None, description="完整频域特征")


class FaultModeKnowledge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="规则ID")
    name: str = Field(..., description="故障模式名称")
    description: str = Field(..., description="判定条件描述")
    key_frequency_features: str = Field(..., description="关键频率特征")
    severity_level: SeverityLevel = Field(default=SeverityLevel.MEDIUM, description="严重等级")
    maintenance_action: str = Field(..., description="建议维护动作")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")


class FaultModeKnowledgeCreate(BaseModel):
    name: str = Field(..., description="故障模式名称")
    description: str = Field(..., description="判定条件描述")
    key_frequency_features: Optional[str] = Field(default="", description="关键频率特征")
    severity_level: Optional[SeverityLevel] = Field(default=SeverityLevel.MEDIUM, description="严重等级")
    maintenance_action: Optional[str] = Field(default="专业检查", description="建议维护动作")


class FaultMatchResult(BaseModel):
    fault_mode_name: str = Field(..., description="故障模式名称")
    confidence: float = Field(..., description="匹配置信度(0-100)")
    evidence: List[str] = Field(..., description="关键证据描述列表")
    severity_level: SeverityLevel = Field(..., description="严重等级")
    key_frequency_features: str = Field(..., description="关键频率特征")


class MaintenanceSuggestion(BaseModel):
    action: str = Field(..., description="建议动作")
    urgency: UrgencyLevel = Field(..., description="紧急程度")
    expected_impact: str = Field(..., description="预计影响")
    estimated_cost: Optional[str] = Field(default=None, description="预计成本")


class DiagnosisTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="任务ID")
    device_id: int = Field(..., description="设备ID")
    device_name: Optional[str] = Field(default=None, description="设备名称")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")
    status: DiagnosisStatus = Field(default=DiagnosisStatus.PENDING, description="诊断状态")
    feature_snapshot: Optional[FeatureSnapshot] = Field(default=None, description="特征快照")
    match_results: Optional[List[FaultMatchResult]] = Field(default=None, description="故障匹配结果")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    completed_at: Optional[datetime] = Field(default=None, description="完成时间")


class DiagnosisTaskCreate(BaseModel):
    device_id: int = Field(..., description="设备ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: datetime = Field(..., description="结束时间")


class DiagnosisReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int = Field(..., description="诊断任务ID")
    device_info: Dict[str, Any] = Field(..., description="设备信息")
    time_range: Dict[str, datetime] = Field(..., description="时间范围")
    feature_snapshot: FeatureSnapshot = Field(..., description="特征快照数据")
    fault_match_results: List[FaultMatchResult] = Field(..., description="故障匹配结果")
    maintenance_suggestions: List[MaintenanceSuggestion] = Field(..., description="维护建议")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
    report_version: str = Field(default="1.0", description="报告版本")
