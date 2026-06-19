import numpy as np
import json
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable, Union
from enum import Enum
from datetime import datetime, timedelta
import time
import platform
import sys

try:
    from trend_analysis import TrendAnalyzer, TimeRange
except ImportError:
    TrendAnalyzer = None
    TimeRange = None


class RuleType(str, Enum):
    ABSOLUTE_THRESHOLD = "absolute_threshold"
    RELATIVE_CHANGE = "relative_change"
    FREQUENCY_THRESHOLD = "frequency_threshold"
    TREND_RISING = "trend_rising"


class LogicalOperator(str, Enum):
    AND = "and"
    OR = "or"


class ComparisonOperator(str, Enum):
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_OR_EQUAL = ">="
    LESS_OR_EQUAL = "<="
    EQUAL = "=="
    NOT_EQUAL = "!="


class AlarmLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class RuleCondition:
    id: str
    rule_type: RuleType
    parameter: str
    enabled: bool = True

    threshold: Optional[float] = None
    operator: ComparisonOperator = ComparisonOperator.GREATER_THAN

    relative_change_percent: Optional[float] = None
    baseline_window_seconds: Optional[int] = None

    frequency_band: Optional[str] = None
    frequency_min: Optional[float] = None
    frequency_max: Optional[float] = None

    trend_time_range: Optional[TimeRange] = None
    min_r_squared: float = 0.7

    description: Optional[str] = None


@dataclass
class AlarmRule:
    id: str
    name: str
    device_id: int
    conditions: List[RuleCondition]
    logical_operator: LogicalOperator = LogicalOperator.AND
    level: AlarmLevel = AlarmLevel.WARNING
    enabled: bool = True
    cooldown_seconds: int = 60
    description: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class ConditionEvaluationResult:
    condition_id: str
    rule_type: RuleType
    parameter: str
    result: bool
    actual_value: Optional[float] = None
    threshold_value: Optional[float] = None
    message: Optional[str] = None


@dataclass
class AlarmTriggerEvent:
    rule_id: str
    rule_name: str
    device_id: int
    level: AlarmLevel
    timestamp: float
    conditions: List[ConditionEvaluationResult]
    message: str
    acknowledged: bool = False


@dataclass
class AlarmLogEntry:
    id: str
    rule_id: str
    rule_name: str
    device_id: int
    level: AlarmLevel
    timestamp: float
    message: str
    conditions: List[Dict[str, Any]]
    actual_values: Dict[str, float]
    acknowledged: bool = False
    acknowledged_at: Optional[float] = None
    acknowledged_by: Optional[str] = None


class Notifier:
    def __init__(self, app_name: str = "Vibration Monitor"):
        self.app_name = app_name
        self._logger = logging.getLogger(__name__)
        self._notification_callback: Optional[Callable[[AlarmTriggerEvent], None]] = None

    def set_notification_callback(
        self,
        callback: Callable[[AlarmTriggerEvent], None],
    ) -> None:
        self._notification_callback = callback

    def _send_desktop_notification(self, event: AlarmTriggerEvent) -> bool:
        try:
            if platform.system() == "Windows":
                return self._send_windows_notification(event)
            elif platform.system() == "Darwin":
                return self._send_macos_notification(event)
            elif platform.system() == "Linux":
                return self._send_linux_notification(event)
        except Exception as e:
            self._logger.warning(f"Failed to send desktop notification: {e}")

        return False

    def _send_windows_notification(self, event: AlarmTriggerEvent) -> bool:
        try:
            import win10toast
            toaster = win10toast.ToastNotifier()
            toaster.show_toast(
                title=f"{event.level.value.upper()}: {event.rule_name}",
                msg=event.message,
                duration=10,
                threaded=True,
            )
            return True
        except ImportError:
            pass
        except Exception as e:
            self._logger.warning(f"Windows notification failed: {e}")
        return False

    def _send_macos_notification(self, event: AlarmTriggerEvent) -> bool:
        try:
            script = f'display notification "{event.message}" with title "{event.level.value.upper()}: {event.rule_name}"'
            import subprocess
            subprocess.run(["osascript", "-e", script], check=True)
            return True
        except Exception as e:
            self._logger.warning(f"macOS notification failed: {e}")
        return False

    def _send_linux_notification(self, event: AlarmTriggerEvent) -> bool:
        try:
            import subprocess
            subprocess.run([
                "notify-send",
                f"{event.level.value.upper()}: {event.rule_name}",
                event.message,
                "-t", "10000",
            ], check=True)
            return True
        except Exception as e:
            self._logger.warning(f"Linux notification failed: {e}")
        return False

    def notify(self, event: AlarmTriggerEvent) -> None:
        self._logger.info(
            f"[{event.level.value.upper()}] {event.rule_name}: {event.message}"
        )

        self._send_desktop_notification(event)

        if self._notification_callback is not None:
            try:
                self._notification_callback(event)
            except Exception as e:
                self._logger.error(f"Notification callback error: {e}")


class AlarmHistory:
    def __init__(self, log_file: Optional[str] = None, max_entries: int = 10000):
        self._log_file = log_file
        self._max_entries = max_entries
        self._logs: List[AlarmLogEntry] = []
        self._logger = logging.getLogger(__name__)

        if log_file and os.path.exists(log_file):
            self._load_from_file()

    def _load_from_file(self) -> None:
        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for entry_data in data:
                    try:
                        entry = AlarmLogEntry(
                            id=entry_data["id"],
                            rule_id=entry_data["rule_id"],
                            rule_name=entry_data["rule_name"],
                            device_id=entry_data["device_id"],
                            level=AlarmLevel(entry_data["level"]),
                            timestamp=entry_data["timestamp"],
                            message=entry_data["message"],
                            conditions=entry_data.get("conditions", []),
                            actual_values=entry_data.get("actual_values", {}),
                            acknowledged=entry_data.get("acknowledged", False),
                            acknowledged_at=entry_data.get("acknowledged_at"),
                            acknowledged_by=entry_data.get("acknowledged_by"),
                        )
                        self._logs.append(entry)
                    except Exception as e:
                        self._logger.warning(f"Failed to load log entry: {e}")
        except Exception as e:
            self._logger.warning(f"Failed to load alarm history: {e}")

    def _save_to_file(self) -> None:
        if not self._log_file:
            return

        try:
            data = []
            for entry in self._logs:
                data.append({
                    "id": entry.id,
                    "rule_id": entry.rule_id,
                    "rule_name": entry.rule_name,
                    "device_id": entry.device_id,
                    "level": entry.level.value,
                    "timestamp": entry.timestamp,
                    "message": entry.message,
                    "conditions": entry.conditions,
                    "actual_values": entry.actual_values,
                    "acknowledged": entry.acknowledged,
                    "acknowledged_at": entry.acknowledged_at,
                    "acknowledged_by": entry.acknowledged_by,
                })

            with open(self._log_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self._logger.error(f"Failed to save alarm history: {e}")

    def add_entry(
        self,
        event: AlarmTriggerEvent,
        actual_values: Dict[str, float],
    ) -> AlarmLogEntry:
        import uuid
        entry = AlarmLogEntry(
            id=str(uuid.uuid4()),
            rule_id=event.rule_id,
            rule_name=event.rule_name,
            device_id=event.device_id,
            level=event.level,
            timestamp=event.timestamp,
            message=event.message,
            conditions=[
                {
                    "condition_id": c.condition_id,
                    "rule_type": c.rule_type.value,
                    "parameter": c.parameter,
                    "result": c.result,
                    "actual_value": c.actual_value,
                    "threshold_value": c.threshold_value,
                    "message": c.message,
                }
                for c in event.conditions
            ],
            actual_values=actual_values,
        )

        self._logs.append(entry)

        if len(self._logs) > self._max_entries:
            self._logs = self._logs[-self._max_entries:]

        self._save_to_file()
        return entry

    def get_logs(
        self,
        device_id: Optional[int] = None,
        level: Optional[AlarmLevel] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 1000,
    ) -> List[AlarmLogEntry]:
        logs = list(self._logs)

        if device_id is not None:
            logs = [l for l in logs if l.device_id == device_id]
        if level is not None:
            logs = [l for l in logs if l.level == level]
        if start_time is not None:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time is not None:
            logs = [l for l in logs if l.timestamp <= end_time]
        if acknowledged is not None:
            logs = [l for l in logs if l.acknowledged == acknowledged]

        return sorted(logs, key=lambda l: l.timestamp, reverse=True)[:limit]

    def acknowledge(
        self,
        log_id: str,
        acknowledged_by: Optional[str] = None,
    ) -> bool:
        for entry in self._logs:
            if entry.id == log_id:
                entry.acknowledged = True
                entry.acknowledged_at = time.time()
                entry.acknowledged_by = acknowledged_by
                self._save_to_file()
                return True
        return False

    def get_statistics(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        logs = self._logs
        if start_time is not None:
            logs = [l for l in logs if l.timestamp >= start_time]
        if end_time is not None:
            logs = [l for l in logs if l.timestamp <= end_time]

        stats = {
            "total": len(logs),
            "by_level": {level.value: 0 for level in AlarmLevel},
            "unacknowledged": 0,
            "by_device": {},
            "by_rule": {},
        }

        for entry in logs:
            stats["by_level"][entry.level.value] += 1
            if not entry.acknowledged:
                stats["unacknowledged"] += 1

            device_key = str(entry.device_id)
            stats["by_device"][device_key] = stats["by_device"].get(device_key, 0) + 1

            stats["by_rule"][entry.rule_id] = stats["by_rule"].get(entry.rule_id, 0) + 1

        return stats


class RuleEvaluator:
    def __init__(
        self,
        trend_analyzer: Optional[TrendAnalyzer] = None,
    ):
        self._trend_analyzer = trend_analyzer
        self._baseline_history: Dict[str, List[Tuple[float, float]]] = {}
        self._logger = logging.getLogger(__name__)

    def set_trend_analyzer(self, trend_analyzer: TrendAnalyzer) -> None:
        self._trend_analyzer = trend_analyzer

    def _compare(
        self,
        value: float,
        operator: ComparisonOperator,
        threshold: float,
    ) -> bool:
        if operator == ComparisonOperator.GREATER_THAN:
            return value > threshold
        elif operator == ComparisonOperator.LESS_THAN:
            return value < threshold
        elif operator == ComparisonOperator.GREATER_OR_EQUAL:
            return value >= threshold
        elif operator == ComparisonOperator.LESS_OR_EQUAL:
            return value <= threshold
        elif operator == ComparisonOperator.EQUAL:
            return abs(value - threshold) < 1e-10
        elif operator == ComparisonOperator.NOT_EQUAL:
            return abs(value - threshold) >= 1e-10
        return False

    def _get_parameter_value(
        self,
        parameter: str,
        time_domain_features: Optional[Dict[str, float]] = None,
        frequency_domain_features: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        if time_domain_features and parameter in time_domain_features:
            return float(time_domain_features[parameter])

        if frequency_domain_features:
            if parameter in frequency_domain_features:
                val = frequency_domain_features[parameter]
                if isinstance(val, (int, float)):
                    return float(val)
            if "frequency_bands" in frequency_domain_features:
                if parameter in frequency_domain_features["frequency_bands"]:
                    return float(frequency_domain_features["frequency_bands"][parameter])

        return None

    def evaluate_absolute_threshold(
        self,
        condition: RuleCondition,
        current_values: Dict[str, float],
    ) -> ConditionEvaluationResult:
        actual_value = current_values.get(condition.parameter)

        if actual_value is None:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=condition.parameter,
                result=False,
                message=f"Parameter '{condition.parameter}' not found",
            )

        result = self._compare(actual_value, condition.operator, condition.threshold)

        return ConditionEvaluationResult(
            condition_id=condition.id,
            rule_type=condition.rule_type,
            parameter=condition.parameter,
            result=result,
            actual_value=actual_value,
            threshold_value=condition.threshold,
            message=(
                f"{condition.parameter} = {actual_value:.4f} "
                f"{condition.operator.value} {condition.threshold:.4f}: "
                f"{'TRIGGERED' if result else 'NORMAL'}"
            ),
        )

    def evaluate_relative_change(
        self,
        condition: RuleCondition,
        current_values: Dict[str, float],
        current_time: Optional[float] = None,
    ) -> ConditionEvaluationResult:
        current_time = current_time or time.time()
        actual_value = current_values.get(condition.parameter)

        if actual_value is None:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=condition.parameter,
                result=False,
                message=f"Parameter '{condition.parameter}' not found",
            )

        if condition.parameter not in self._baseline_history:
            self._baseline_history[condition.parameter] = []

        self._baseline_history[condition.parameter].append((current_time, actual_value))

        window_start = current_time - condition.baseline_window_seconds
        history = [
            (t, v) for t, v in self._baseline_history[condition.parameter]
            if t >= window_start
        ]
        self._baseline_history[condition.parameter] = history

        if len(history) < 2:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=condition.parameter,
                result=False,
                actual_value=actual_value,
                message="Insufficient baseline data",
            )

        baseline_values = [v for _, v in history[:-1]]
        baseline_mean = np.mean(baseline_values)

        if baseline_mean == 0:
            change_percent = float("inf") if actual_value > 0 else 0.0
        else:
            change_percent = (actual_value - baseline_mean) / abs(baseline_mean) * 100.0

        threshold = condition.relative_change_percent or 200.0
        result = abs(change_percent) >= threshold

        return ConditionEvaluationResult(
            condition_id=condition.id,
            rule_type=condition.rule_type,
            parameter=condition.parameter,
            result=result,
            actual_value=actual_value,
            threshold_value=threshold,
            message=(
                f"{condition.parameter} = {actual_value:.4f}, "
                f"baseline = {baseline_mean:.4f}, "
                f"change = {change_percent:.1f}%, "
                f"threshold = {threshold:.1f}%: "
                f"{'TRIGGERED' if result else 'NORMAL'}"
            ),
        )

    def evaluate_frequency_threshold(
        self,
        condition: RuleCondition,
        frequency_data: Optional[Dict[str, Any]],
    ) -> ConditionEvaluationResult:
        if frequency_data is None:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=condition.parameter,
                result=False,
                message="No frequency data available",
            )

        amplitude = None
        if condition.frequency_band and "frequency_bands" in frequency_data:
            amplitude = frequency_data["frequency_bands"].get(condition.frequency_band)
        elif condition.frequency_min is not None and condition.frequency_max is not None:
            if "freqs" in frequency_data and "amplitudes" in frequency_data:
                freqs = np.array(frequency_data["freqs"])
                amps = np.array(frequency_data["amplitudes"])
                mask = (freqs >= condition.frequency_min) & (freqs <= condition.frequency_max)
                if np.any(mask):
                    amplitude = float(np.max(amps[mask]))
        elif condition.parameter in frequency_data:
            val = frequency_data[condition.parameter]
            if isinstance(val, (int, float)):
                amplitude = float(val)

        if amplitude is None:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=condition.parameter,
                result=False,
                message="Frequency band/parameter not found",
            )

        result = self._compare(amplitude, condition.operator, condition.threshold)

        return ConditionEvaluationResult(
            condition_id=condition.id,
            rule_type=condition.rule_type,
            parameter=condition.parameter,
            result=result,
            actual_value=amplitude,
            threshold_value=condition.threshold,
            message=(
                f"Frequency {condition.frequency_band or condition.parameter} = {amplitude:.4f} "
                f"{condition.operator.value} {condition.threshold:.4f}: "
                f"{'TRIGGERED' if result else 'NORMAL'}"
            ),
        )

    def evaluate_trend_rising(
        self,
        condition: RuleCondition,
    ) -> ConditionEvaluationResult:
        if self._trend_analyzer is None:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=condition.parameter,
                result=False,
                message="Trend analyzer not available",
            )

        time_range = condition.trend_time_range or TimeRange.HOUR_1
        metric = condition.parameter

        try:
            trend_result = self._trend_analyzer.analyze_trend(
                time_range=time_range,
                metric=metric,
                trigger_callbacks=False,
            )

            is_rising = (
                trend_result.regression.slope > 0
                and trend_result.regression.r_squared >= condition.min_r_squared
            )

            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=metric,
                result=is_rising,
                actual_value=trend_result.regression.slope,
                threshold_value=condition.min_r_squared,
                message=(
                    f"Trend {metric}: slope={trend_result.regression.slope:.6f}, "
                    f"R^2={trend_result.regression.r_squared:.4f}, "
                    f"R^2_threshold={condition.min_r_squared}: "
                    f"{'TRIGGERED' if is_rising else 'NORMAL'}"
                ),
            )
        except Exception as e:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=metric,
                result=False,
                message=f"Trend analysis error: {e}",
            )

    def evaluate_condition(
        self,
        condition: RuleCondition,
        current_values: Dict[str, float],
        frequency_data: Optional[Dict[str, Any]] = None,
        current_time: Optional[float] = None,
    ) -> ConditionEvaluationResult:
        if not condition.enabled:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=condition.parameter,
                result=False,
                message="Condition disabled",
            )

        if condition.rule_type == RuleType.ABSOLUTE_THRESHOLD:
            return self.evaluate_absolute_threshold(condition, current_values)
        elif condition.rule_type == RuleType.RELATIVE_CHANGE:
            return self.evaluate_relative_change(condition, current_values, current_time)
        elif condition.rule_type == RuleType.FREQUENCY_THRESHOLD:
            return self.evaluate_frequency_threshold(condition, frequency_data)
        elif condition.rule_type == RuleType.TREND_RISING:
            return self.evaluate_trend_rising(condition)
        else:
            return ConditionEvaluationResult(
                condition_id=condition.id,
                rule_type=condition.rule_type,
                parameter=condition.parameter,
                result=False,
                message=f"Unknown rule type: {condition.rule_type}",
            )

    def evaluate_rule(
        self,
        rule: AlarmRule,
        current_values: Dict[str, float],
        frequency_data: Optional[Dict[str, Any]] = None,
        current_time: Optional[float] = None,
    ) -> List[ConditionEvaluationResult]:
        if not rule.enabled:
            return []

        results = []
        for condition in rule.conditions:
            result = self.evaluate_condition(
                condition=condition,
                current_values=current_values,
                frequency_data=frequency_data,
                current_time=current_time,
            )
            results.append(result)

        return results

    def check_rule_triggered(
        self,
        rule: AlarmRule,
        condition_results: List[ConditionEvaluationResult],
    ) -> bool:
        if not condition_results:
            return False

        triggered = [r.result for r in condition_results]

        if rule.logical_operator == LogicalOperator.AND:
            return all(triggered)
        elif rule.logical_operator == LogicalOperator.OR:
            return any(triggered)

        return False


class AlarmRuleManager:
    def __init__(
        self,
        log_file: Optional[str] = None,
        trend_analyzer: Optional[TrendAnalyzer] = None,
        notification_callback: Optional[Callable[[AlarmTriggerEvent], None]] = None,
    ):
        self._rules: Dict[str, AlarmRule] = {}
        self._last_triggered: Dict[str, float] = {}
        self._evaluator = RuleEvaluator(trend_analyzer=trend_analyzer)
        self._notifier = Notifier()
        self._history = AlarmHistory(log_file=log_file)
        self._logger = logging.getLogger(__name__)

        if notification_callback:
            self._notifier.set_notification_callback(notification_callback)

    def set_trend_analyzer(self, trend_analyzer: TrendAnalyzer) -> None:
        self._evaluator.set_trend_analyzer(trend_analyzer)

    def set_notification_callback(
        self,
        callback: Callable[[AlarmTriggerEvent], None],
    ) -> None:
        self._notifier.set_notification_callback(callback)

    def add_rule(self, rule: AlarmRule) -> None:
        self._rules[rule.id] = rule
        self._logger.info(f"Added alarm rule: {rule.name} ({rule.id})")

    def remove_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            del self._rules[rule_id]
            if rule_id in self._last_triggered:
                del self._last_triggered[rule_id]
            self._logger.info(f"Removed alarm rule: {rule_id}")
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[AlarmRule]:
        return self._rules.get(rule_id)

    def get_all_rules(self) -> List[AlarmRule]:
        return list(self._rules.values())

    def enable_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = True
            self._rules[rule_id].updated_at = time.time()
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        if rule_id in self._rules:
            self._rules[rule_id].enabled = False
            self._rules[rule_id].updated_at = time.time()
            return True
        return False

    def _should_trigger(
        self,
        rule: AlarmRule,
        triggered: bool,
        current_time: float,
    ) -> bool:
        if not triggered:
            return False

        last_triggered = self._last_triggered.get(rule.id, 0)
        cooldown_until = last_triggered + rule.cooldown_seconds

        if current_time < cooldown_until:
            return False

        return True

    def evaluate(
        self,
        device_id: int,
        time_domain_features: Dict[str, float],
        frequency_domain_features: Optional[Dict[str, Any]] = None,
        current_time: Optional[float] = None,
    ) -> List[AlarmTriggerEvent]:
        current_time = current_time or time.time()
        events = []

        for rule in self._rules.values():
            if rule.device_id != device_id or not rule.enabled:
                continue

            condition_results = self._evaluator.evaluate_rule(
                rule=rule,
                current_values=time_domain_features,
                frequency_data=frequency_domain_features,
                current_time=current_time,
            )

            triggered = self._evaluator.check_rule_triggered(rule, condition_results)

            if self._should_trigger(rule, triggered, current_time):
                message_parts = [r.message for r in condition_results if r.result]
                message = "; ".join(message_parts) if message_parts else rule.description or "Alarm triggered"

                event = AlarmTriggerEvent(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    device_id=rule.device_id,
                    level=rule.level,
                    timestamp=current_time,
                    conditions=condition_results,
                    message=message,
                )

                self._notifier.notify(event)
                self._history.add_entry(event, time_domain_features)
                self._last_triggered[rule.id] = current_time
                events.append(event)

        return events

    def get_history(self) -> AlarmHistory:
        return self._history

    def get_alarm_logs(
        self,
        device_id: Optional[int] = None,
        level: Optional[AlarmLevel] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        acknowledged: Optional[bool] = None,
        limit: int = 1000,
    ) -> List[AlarmLogEntry]:
        return self._history.get_logs(
            device_id=device_id,
            level=level,
            start_time=start_time,
            end_time=end_time,
            acknowledged=acknowledged,
            limit=limit,
        )

    def acknowledge_alarm(
        self,
        log_id: str,
        acknowledged_by: Optional[str] = None,
    ) -> bool:
        return self._history.acknowledge(log_id, acknowledged_by)

    def get_statistics(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> Dict[str, Any]:
        return self._history.get_statistics(start_time, end_time)


def create_simple_rule(
    rule_id: str,
    name: str,
    device_id: int,
    parameter: str,
    threshold: float,
    operator: ComparisonOperator = ComparisonOperator.GREATER_THAN,
    level: AlarmLevel = AlarmLevel.WARNING,
    description: Optional[str] = None,
) -> AlarmRule:
    condition = RuleCondition(
        id=f"{rule_id}_cond_1",
        rule_type=RuleType.ABSOLUTE_THRESHOLD,
        parameter=parameter,
        threshold=threshold,
        operator=operator,
        description=description,
    )

    return AlarmRule(
        id=rule_id,
        name=name,
        device_id=device_id,
        conditions=[condition],
        level=level,
        description=description,
    )


def create_trend_rule(
    rule_id: str,
    name: str,
    device_id: int,
    parameter: str,
    time_range: TimeRange,
    min_r_squared: float = 0.7,
    level: AlarmLevel = AlarmLevel.WARNING,
    description: Optional[str] = None,
) -> AlarmRule:
    condition = RuleCondition(
        id=f"{rule_id}_cond_1",
        rule_type=RuleType.TREND_RISING,
        parameter=parameter,
        trend_time_range=time_range,
        min_r_squared=min_r_squared,
        description=description,
    )

    return AlarmRule(
        id=rule_id,
        name=name,
        device_id=device_id,
        conditions=[condition],
        level=level,
        description=description,
    )


def create_combined_rule(
    rule_id: str,
    name: str,
    device_id: int,
    conditions: List[RuleCondition],
    operator: LogicalOperator = LogicalOperator.AND,
    level: AlarmLevel = AlarmLevel.WARNING,
    description: Optional[str] = None,
) -> AlarmRule:
    return AlarmRule(
        id=rule_id,
        name=name,
        device_id=device_id,
        conditions=conditions,
        logical_operator=operator,
        level=level,
        description=description,
    )


def main():
    print("Alarm Rules Module Test")
    print("=" * 60)

    def notification_callback(event: AlarmTriggerEvent):
        print(f"\n[NOTIFICATION] {event.level.value.upper()}: {event.rule_name}")
        print(f"  Message: {event.message}")
        print(f"  Time: {datetime.fromtimestamp(event.timestamp)}")

    manager = AlarmRuleManager(
        notification_callback=notification_callback,
    )

    rms_threshold_rule = create_simple_rule(
        rule_id="rms_high",
        name="RMS High Warning",
        device_id=1,
        parameter="rms",
        threshold=2.0,
        operator=ComparisonOperator.GREATER_THAN,
        level=AlarmLevel.WARNING,
        description="RMS value exceeds warning threshold",
    )
    manager.add_rule(rms_threshold_rule)

    peak_critical_rule = create_simple_rule(
        rule_id="peak_critical",
        name="Peak Critical Alarm",
        device_id=1,
        parameter="peak",
        threshold=10.0,
        operator=ComparisonOperator.GREATER_THAN,
        level=AlarmLevel.CRITICAL,
        description="Peak value exceeds critical threshold",
    )
    manager.add_rule(peak_critical_rule)

    if TrendAnalyzer and TimeRange:
        trend_analyzer = TrendAnalyzer()
        manager.set_trend_analyzer(trend_analyzer)

        base_time = time.time() - 3600
        for i in range(60):
            t = base_time + i * 60
            rms = 0.5 + 0.02 * i + np.random.normal(0, 0.05)
            trend_analyzer.add_metrics_values(
                rms=rms,
                peak=rms * 2.5,
                peak_to_peak=rms * 4.5,
                crest_factor=2.5,
                kurtosis=3.0,
                timestamp=t,
            )

        trend_rule = create_trend_rule(
            rule_id="rms_trend",
            name="RMS Rising Trend",
            device_id=1,
            parameter="rms",
            time_range=TimeRange.HOUR_1,
            min_r_squared=0.7,
            level=AlarmLevel.WARNING,
            description="RMS shows continuous rising trend",
        )
        manager.add_rule(trend_rule)

    relative_condition = RuleCondition(
        id="rel_cond_1",
        rule_type=RuleType.RELATIVE_CHANGE,
        parameter="rms",
        relative_change_percent=200.0,
        baseline_window_seconds=3600,
        description="RMS increased by more than 200%",
    )

    combined_rule = create_combined_rule(
        rule_id="combined_rms",
        name="Combined RMS Alarm",
        device_id=1,
        conditions=[
            rms_threshold_rule.conditions[0],
            relative_condition,
        ],
        operator=LogicalOperator.AND,
        level=AlarmLevel.CRITICAL,
        description="RMS exceeds threshold AND shows significant increase",
    )
    manager.add_rule(combined_rule)

    print("\nRegistered rules:")
    for rule in manager.get_all_rules():
        print(f"  - {rule.name} ({rule.id}): {rule.level.value}, "
              f"{'enabled' if rule.enabled else 'disabled'}")

    print("\nEvaluating rules with test data...")
    test_data = {
        "rms": 3.5,
        "peak": 12.0,
        "peak_to_peak": 20.0,
        "crest_factor": 3.4,
        "kurtosis": 5.0,
    }

    events = manager.evaluate(
        device_id=1,
        time_domain_features=test_data,
    )

    print(f"\nTriggered {len(events)} alarms")

    print("\nAlarm statistics:")
    stats = manager.get_statistics()
    print(f"  Total: {stats['total']}")
    print(f"  By level: {stats['by_level']}")
    print(f"  Unacknowledged: {stats['unacknowledged']}")

    print("\nRecent alarm logs:")
    logs = manager.get_alarm_logs(limit=10)
    for log in logs:
        print(f"  [{datetime.fromtimestamp(log.timestamp)}] "
              f"{log.level.value.upper()}: {log.rule_name} - {log.message}")


if __name__ == "__main__":
    main()
