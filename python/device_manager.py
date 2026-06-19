import os
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field

from models import (
    Device,
    DeviceCreate,
    DeviceUpdate,
    DeviceStatus,
    SamplingParams,
    SamplingParamsCreate,
    AlarmRule,
    AlarmRuleCreate,
    AlarmRecord,
    AlarmLevel,
)

logger = logging.getLogger(__name__)

STATUS_COLOR_MAP = {
    DeviceStatus.ONLINE: {"color": "#22c55e", "name": "正常", "bg_color": "#dcfce7"},
    DeviceStatus.WARNING: {"color": "#eab308", "name": "预警", "bg_color": "#fef9c3"},
    DeviceStatus.ERROR: {"color": "#ef4444", "name": "报警", "bg_color": "#fee2e2"},
    DeviceStatus.OFFLINE: {"color": "#6b7280", "name": "离线", "bg_color": "#f3f4f6"},
}


@dataclass
class MonitoringPoint:
    id: int
    device_id: int
    name: str
    location: str
    sensor_type: str
    channel: int
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class MonitoringPointCreate:
    device_id: int
    name: str
    location: str
    sensor_type: str
    channel: int
    description: Optional[str] = None


class DeviceManager:
    def __init__(self, storage_path: Optional[str] = None):
        self._devices: Dict[int, Device] = {}
        self._monitoring_points: Dict[int, MonitoringPoint] = {}
        self._sampling_params: Dict[int, SamplingParams] = {}
        self._alarm_rules: Dict[int, AlarmRule] = {}
        self._alarm_records: List[AlarmRecord] = []
        self._device_id_counter = 1
        self._point_id_counter = 1
        self._params_id_counter = 1
        self._rule_id_counter = 1
        self._record_id_counter = 1

        if storage_path is None:
            storage_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "data"
            )
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._devices_file = self._storage_path / "devices.json"
        self._points_file = self._storage_path / "monitoring_points.json"

        self._load_from_storage()

    def _load_from_storage(self) -> None:
        try:
            if self._devices_file.exists():
                with open(self._devices_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for device_data in data.get("devices", []):
                        device = Device.model_validate(device_data)
                        self._devices[device.id] = device
                        if device.id >= self._device_id_counter:
                            self._device_id_counter = device.id + 1
                logger.info(f"已加载 {len(self._devices)} 个设备配置")

            if self._points_file.exists():
                with open(self._points_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for point_data in data.get("points", []):
                        point = MonitoringPoint(**point_data)
                        self._monitoring_points[point.id] = point
                        if point.id >= self._point_id_counter:
                            self._point_id_counter = point.id + 1
                logger.info(f"已加载 {len(self._monitoring_points)} 个监测点配置")
        except Exception as e:
            logger.error(f"加载设备配置失败: {e}")

    def _save_to_storage(self) -> None:
        try:
            devices_data = {
                "devices": [d.model_dump(mode="json") for d in self._devices.values()]
            }
            with open(self._devices_file, "w", encoding="utf-8") as f:
                json.dump(devices_data, f, ensure_ascii=False, indent=2)

            points_data = {
                "points": [
                    {
                        "id": p.id,
                        "device_id": p.device_id,
                        "name": p.name,
                        "location": p.location,
                        "sensor_type": p.sensor_type,
                        "channel": p.channel,
                        "description": p.description,
                        "created_at": p.created_at.isoformat(),
                    }
                    for p in self._monitoring_points.values()
                ]
            }
            with open(self._points_file, "w", encoding="utf-8") as f:
                json.dump(points_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存设备配置失败: {e}")

    def create_device(self, device_create: DeviceCreate) -> Device:
        for existing in self._devices.values():
            if existing.code == device_create.code:
                raise ValueError(f"设备编码 {device_create.code} 已存在")

        device_id = self._device_id_counter
        self._device_id_counter += 1

        now = datetime.now()
        device = Device(
            id=device_id,
            name=device_create.name,
            code=device_create.code,
            location=device_create.location,
            status=DeviceStatus.OFFLINE,
            ip_address=device_create.ip_address,
            sensor_count=device_create.sensor_count,
            description=device_create.description,
            created_at=now,
            updated_at=now,
        )

        self._devices[device_id] = device
        self._save_to_storage()
        logger.info(f"创建设备成功: {device.name} (ID: {device.id})")
        return device

    def get_device(self, device_id: int) -> Optional[Device]:
        return self._devices.get(device_id)

    def get_devices(
        self,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Tuple[List[Device], int]:
        devices = list(self._devices.values())

        if status:
            devices = [d for d in devices if d.status.value == status]

        if keyword:
            keyword_lower = keyword.lower()
            devices = [
                d
                for d in devices
                if keyword_lower in d.name.lower()
                or keyword_lower in d.code.lower()
                or keyword_lower in d.location.lower()
            ]

        devices.sort(key=lambda d: d.id, reverse=True)

        total = len(devices)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_devices = devices[start:end]

        return paginated_devices, total

    def update_device(self, device_id: int, device_update: DeviceUpdate) -> Device:
        device = self._devices.get(device_id)
        if not device:
            raise ValueError(f"设备 {device_id} 不存在")

        update_data = device_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(device, key, value)

        device.updated_at = datetime.now()
        self._devices[device_id] = device
        self._save_to_storage()
        logger.info(f"更新设备成功: {device.name} (ID: {device.id})")
        return device

    def delete_device(self, device_id: int) -> None:
        if device_id not in self._devices:
            raise ValueError(f"设备 {device_id} 不存在")

        points_to_delete = [
            pid for pid, p in self._monitoring_points.items() if p.device_id == device_id
        ]
        for pid in points_to_delete:
            del self._monitoring_points[pid]

        del self._devices[device_id]
        self._save_to_storage()
        logger.info(f"删除设备成功: ID {device_id}")

    def update_device_status(
        self, device_id: int, status: DeviceStatus
    ) -> Device:
        device = self._devices.get(device_id)
        if not device:
            raise ValueError(f"设备 {device_id} 不存在")

        device.status = status
        device.updated_at = datetime.now()
        self._devices[device_id] = device
        self._save_to_storage()
        return device

    def get_device_status_display(self, status: DeviceStatus) -> Dict[str, str]:
        return STATUS_COLOR_MAP.get(
            status,
            {"color": "#6b7280", "name": "未知", "bg_color": "#f3f4f6"},
        )

    def get_all_devices_status(self) -> List[Dict[str, Any]]:
        result = []
        for device in self._devices.values():
            status_info = self.get_device_status_display(device.status)
            points = self.get_monitoring_points_by_device(device.id)
            result.append(
                {
                    "device": device.model_dump(mode="json"),
                    "status_display": status_info,
                    "monitoring_points_count": len(points),
                    "monitoring_points": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "location": p.location,
                            "channel": p.channel,
                            "sensor_type": p.sensor_type,
                        }
                        for p in points
                    ],
                }
            )
        return result

    def create_monitoring_point(
        self, point_create: MonitoringPointCreate
    ) -> MonitoringPoint:
        if point_create.device_id not in self._devices:
            raise ValueError(f"设备 {point_create.device_id} 不存在")

        for existing in self._monitoring_points.values():
            if (
                existing.device_id == point_create.device_id
                and existing.channel == point_create.channel
            ):
                raise ValueError(
                    f"设备 {point_create.device_id} 的通道 {point_create.channel} 已配置监测点"
                )

        point_id = self._point_id_counter
        self._point_id_counter += 1

        point = MonitoringPoint(
            id=point_id,
            device_id=point_create.device_id,
            name=point_create.name,
            location=point_create.location,
            sensor_type=point_create.sensor_type,
            channel=point_create.channel,
            description=point_create.description,
        )

        self._monitoring_points[point_id] = point
        self._save_to_storage()
        logger.info(f"创建监测点成功: {point.name} (ID: {point.id})")
        return point

    def get_monitoring_point(self, point_id: int) -> Optional[MonitoringPoint]:
        return self._monitoring_points.get(point_id)

    def get_monitoring_points_by_device(
        self, device_id: int
    ) -> List[MonitoringPoint]:
        return [p for p in self._monitoring_points.values() if p.device_id == device_id]

    def delete_monitoring_point(self, point_id: int) -> None:
        if point_id not in self._monitoring_points:
            raise ValueError(f"监测点 {point_id} 不存在")

        del self._monitoring_points[point_id]
        self._save_to_storage()
        logger.info(f"删除监测点成功: ID {point_id}")

    def create_sampling_params(
        self, params_create: SamplingParamsCreate
    ) -> SamplingParams:
        if params_create.device_id not in self._devices:
            raise ValueError(f"设备 {params_create.device_id} 不存在")

        params_id = self._params_id_counter
        self._params_id_counter += 1

        params = SamplingParams(
            id=params_id,
            device_id=params_create.device_id,
            sample_rate=params_create.sample_rate,
            sample_length=params_create.sample_length,
            channel_count=params_create.channel_count,
            acquisition_interval=params_create.acquisition_interval,
            is_continuous=params_create.is_continuous,
            created_at=datetime.now(),
        )

        self._sampling_params[params_id] = params
        logger.info(f"创建采样参数成功: 设备ID {params.device_id}")
        return params

    def get_sampling_params_by_device(
        self, device_id: int
    ) -> Optional[SamplingParams]:
        for params in self._sampling_params.values():
            if params.device_id == device_id:
                return params
        return None

    def create_alarm_rule(self, rule_create: AlarmRuleCreate) -> AlarmRule:
        if rule_create.device_id not in self._devices:
            raise ValueError(f"设备 {rule_create.device_id} 不存在")

        rule_id = self._rule_id_counter
        self._rule_id_counter += 1

        rule = AlarmRule(
            id=rule_id,
            device_id=rule_create.device_id,
            name=rule_create.name,
            alarm_type=rule_create.alarm_type,
            alarm_level=rule_create.alarm_level,
            parameter=rule_create.parameter,
            threshold=rule_create.threshold,
            operator=rule_create.operator,
            duration=rule_create.duration,
            enabled=rule_create.enabled,
            created_at=datetime.now(),
        )

        self._alarm_rules[rule_id] = rule
        logger.info(f"创建报警规则成功: {rule.name} (ID: {rule.id})")
        return rule

    def evaluate_alarm_rules(
        self, device_id: int, parameter: str, value: float
    ) -> List[AlarmRecord]:
        triggered_records = []
        now = datetime.now()

        for rule in self._alarm_rules.values():
            if rule.device_id != device_id or not rule.enabled:
                continue
            if rule.parameter != parameter:
                continue

            is_triggered = False
            if rule.operator == ">":
                is_triggered = value > rule.threshold
            elif rule.operator == ">=":
                is_triggered = value >= rule.threshold
            elif rule.operator == "<":
                is_triggered = value < rule.threshold
            elif rule.operator == "<=":
                is_triggered = value <= rule.threshold
            elif rule.operator == "==":
                is_triggered = value == rule.threshold
            elif rule.operator == "!=":
                is_triggered = value != rule.threshold

            if is_triggered:
                record_id = self._record_id_counter
                self._record_id_counter += 1

                record = AlarmRecord(
                    id=record_id,
                    device_id=device_id,
                    rule_id=rule.id,
                    alarm_type=rule.alarm_type,
                    alarm_level=rule.alarm_level,
                    message=f"{rule.name}: {parameter}={value} {rule.operator} {rule.threshold}",
                    parameter=parameter,
                    actual_value=value,
                    threshold=rule.threshold,
                    created_at=now,
                )

                self._alarm_records.append(record)
                triggered_records.append(record)

                if rule.alarm_level == AlarmLevel.CRITICAL:
                    self.update_device_status(device_id, DeviceStatus.ERROR)
                elif rule.alarm_level == AlarmLevel.WARNING:
                    self.update_device_status(device_id, DeviceStatus.WARNING)

                logger.warning(
                    f"报警触发: 设备 {device_id}, {rule.name}, 值={value}"
                )

        return triggered_records

    def get_alarm_records(
        self,
        page: int = 1,
        page_size: int = 10,
        device_id: Optional[int] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Tuple[List[AlarmRecord], int]:
        records = list(self._alarm_records)

        if device_id is not None:
            records = [r for r in records if r.device_id == device_id]

        if level:
            records = [r for r in records if r.alarm_level.value == level]

        if start_time:
            records = [r for r in records if r.created_at >= start_time]

        if end_time:
            records = [r for r in records if r.created_at <= end_time]

        records.sort(key=lambda r: r.created_at, reverse=True)

        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_records = records[start:end]

        return paginated_records, total

    def acknowledge_alarm(self, record_id: int) -> AlarmRecord:
        for record in self._alarm_records:
            if record.id == record_id:
                record.acknowledged = True
                record.acknowledged_at = datetime.now()
                logger.info(f"确认报警: 记录ID {record_id}")
                return record
        raise ValueError(f"报警记录 {record_id} 不存在")

    def get_statistics(self) -> Dict[str, Any]:
        total_devices = len(self._devices)
        online_devices = sum(
            1 for d in self._devices.values() if d.status == DeviceStatus.ONLINE
        )
        warning_devices = sum(
            1 for d in self._devices.values() if d.status == DeviceStatus.WARNING
        )
        error_devices = sum(
            1 for d in self._devices.values() if d.status == DeviceStatus.ERROR
        )
        offline_devices = sum(
            1 for d in self._devices.values() if d.status == DeviceStatus.OFFLINE
        )
        total_points = len(self._monitoring_points)
        unacknowledged_alarms = sum(
            1 for r in self._alarm_records if not r.acknowledged
        )

        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "warning_devices": warning_devices,
            "error_devices": error_devices,
            "offline_devices": offline_devices,
            "total_monitoring_points": total_points,
            "unacknowledged_alarms": unacknowledged_alarms,
            "device_status_distribution": [
                {
                    "status": DeviceStatus.ONLINE.value,
                    "count": online_devices,
                    "display": self.get_device_status_display(DeviceStatus.ONLINE),
                },
                {
                    "status": DeviceStatus.WARNING.value,
                    "count": warning_devices,
                    "display": self.get_device_status_display(DeviceStatus.WARNING),
                },
                {
                    "status": DeviceStatus.ERROR.value,
                    "count": error_devices,
                    "display": self.get_device_status_display(DeviceStatus.ERROR),
                },
                {
                    "status": DeviceStatus.OFFLINE.value,
                    "count": offline_devices,
                    "display": self.get_device_status_display(DeviceStatus.OFFLINE),
                },
            ],
        }


_device_manager_instance: Optional[DeviceManager] = None


def get_device_manager() -> DeviceManager:
    global _device_manager_instance
    if _device_manager_instance is None:
        _device_manager_instance = DeviceManager()
    return _device_manager_instance
