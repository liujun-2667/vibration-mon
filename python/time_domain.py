import numpy as np
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Tuple, List
from enum import Enum


class AlertLevel(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    ALARM = "alarm"


@dataclass
class ThresholdConfig:
    rms_warning: float = 2.0
    rms_alarm: float = 5.0
    peak_warning: float = 5.0
    peak_alarm: float = 10.0
    peak_to_peak_warning: float = 10.0
    peak_to_peak_alarm: float = 20.0
    crest_factor_warning: float = 4.0
    crest_factor_alarm: float = 6.0
    kurtosis_warning: float = 4.0
    kurtosis_alarm: float = 7.0


@dataclass
class TimeDomainFeatures:
    rms: float = 0.0
    peak: float = 0.0
    peak_to_peak: float = 0.0
    crest_factor: float = 0.0
    kurtosis: float = 0.0
    timestamp: float = field(default_factory=time.time)
    alerts: Dict[str, AlertLevel] = field(default_factory=dict)


class TimeDomainAnalyzer:
    def __init__(
        self,
        sample_rate: int = 10240,
        refresh_interval: float = 0.5,
        thresholds: Optional[ThresholdConfig] = None,
    ):
        self.sample_rate = sample_rate
        self.refresh_interval = refresh_interval
        self.thresholds = thresholds or ThresholdConfig()
        self._last_refresh_time = 0.0
        self._history: List[TimeDomainFeatures] = []
        self._alert_callbacks: List[Callable[[str, AlertLevel, TimeDomainFeatures], None]] = []
        self._update_callbacks: List[Callable[[TimeDomainFeatures], None]] = []

    def set_thresholds(self, thresholds: ThresholdConfig) -> None:
        self.thresholds = thresholds

    def set_sample_rate(self, sample_rate: int) -> None:
        self.sample_rate = sample_rate

    def set_refresh_interval(self, interval: float) -> None:
        self.refresh_interval = interval

    def register_alert_callback(
        self,
        callback: Callable[[str, AlertLevel, TimeDomainFeatures], None],
    ) -> None:
        self._alert_callbacks.append(callback)

    def register_update_callback(
        self,
        callback: Callable[[TimeDomainFeatures], None],
    ) -> None:
        self._update_callbacks.append(callback)

    def clear_callbacks(self) -> None:
        self._alert_callbacks.clear()
        self._update_callbacks.clear()

    @staticmethod
    def calculate_rms(signal: np.ndarray) -> float:
        return np.sqrt(np.mean(signal ** 2))

    @staticmethod
    def calculate_peak(signal: np.ndarray) -> float:
        return float(np.max(np.abs(signal)))

    @staticmethod
    def calculate_peak_to_peak(signal: np.ndarray) -> float:
        return float(np.max(signal) - np.min(signal))

    @staticmethod
    def calculate_crest_factor(signal: np.ndarray) -> float:
        rms = TimeDomainAnalyzer.calculate_rms(signal)
        if rms == 0:
            return 0.0
        peak = TimeDomainAnalyzer.calculate_peak(signal)
        return peak / rms

    @staticmethod
    def calculate_kurtosis(signal: np.ndarray) -> float:
        mean = np.mean(signal)
        std = np.std(signal)
        if std == 0:
            return 0.0
        normalized = (signal - mean) / std
        return float(np.mean(normalized ** 4))

    def extract_features(self, signal: np.ndarray) -> TimeDomainFeatures:
        features = TimeDomainFeatures(
            rms=self.calculate_rms(signal),
            peak=self.calculate_peak(signal),
            peak_to_peak=self.calculate_peak_to_peak(signal),
            crest_factor=self.calculate_crest_factor(signal),
            kurtosis=self.calculate_kurtosis(signal),
            timestamp=time.time(),
        )
        features.alerts = self._check_alerts(features)
        return features

    def _check_alerts(self, features: TimeDomainFeatures) -> Dict[str, AlertLevel]:
        alerts = {}

        thresholds = [
            ("rms", features.rms, self.thresholds.rms_warning, self.thresholds.rms_alarm),
            ("peak", features.peak, self.thresholds.peak_warning, self.thresholds.peak_alarm),
            ("peak_to_peak", features.peak_to_peak, self.thresholds.peak_to_peak_warning, self.thresholds.peak_to_peak_alarm),
            ("crest_factor", features.crest_factor, self.thresholds.crest_factor_warning, self.thresholds.crest_factor_alarm),
            ("kurtosis", features.kurtosis, self.thresholds.kurtosis_warning, self.thresholds.kurtosis_alarm),
        ]

        for name, value, warning_thresh, alarm_thresh in thresholds:
            if value >= alarm_thresh:
                alerts[name] = AlertLevel.ALARM
            elif value >= warning_thresh:
                alerts[name] = AlertLevel.WARNING
            else:
                alerts[name] = AlertLevel.NORMAL

        return alerts

    def _trigger_alert_callbacks(self, features: TimeDomainFeatures) -> None:
        for metric, level in features.alerts.items():
            if level != AlertLevel.NORMAL:
                for callback in self._alert_callbacks:
                    callback(metric, level, features)

    def _trigger_update_callbacks(self, features: TimeDomainFeatures) -> None:
        for callback in self._update_callbacks:
            callback(features)

    def should_refresh(self) -> bool:
        current_time = time.time()
        if current_time - self._last_refresh_time >= self.refresh_interval:
            self._last_refresh_time = current_time
            return True
        return False

    def analyze(self, signal: np.ndarray, force: bool = False) -> Optional[TimeDomainFeatures]:
        if not (force or self.should_refresh()):
            return None

        features = self.extract_features(signal)
        self._history.append(features)

        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        self._trigger_alert_callbacks(features)
        self._trigger_update_callbacks(features)

        return features

    def analyze_stream(
        self,
        source: Callable[[], np.ndarray],
        stop_condition: Optional[Callable[[], bool]] = None,
    ) -> None:
        stop_condition = stop_condition or (lambda: False)

        while not stop_condition():
            signal = source()
            self.analyze(signal)
            time.sleep(0.01)

    def get_history(self) -> List[TimeDomainFeatures]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    def get_summary(self) -> Dict[str, Dict[str, float]]:
        if not self._history:
            return {}

        metrics = ["rms", "peak", "peak_to_peak", "crest_factor", "kurtosis"]
        summary = {}

        for metric in metrics:
            values = [getattr(f, metric) for f in self._history]
            summary[metric] = {
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "latest": values[-1],
            }

        return summary

    def get_highest_alert_level(self, features: Optional[TimeDomainFeatures] = None) -> AlertLevel:
        features = features or (self._history[-1] if self._history else None)
        if features is None:
            return AlertLevel.NORMAL

        priority = {AlertLevel.ALARM: 2, AlertLevel.WARNING: 1, AlertLevel.NORMAL: 0}
        max_level = AlertLevel.NORMAL

        for level in features.alerts.values():
            if priority[level] > priority[max_level]:
                max_level = level

        return max_level


def main():
    from signal_simulator import SignalSimulator, SampleRate, FaultType, Severity

    def alert_callback(metric: str, level: AlertLevel, features: TimeDomainFeatures) -> None:
        print(f"[{level.value.upper()}] {metric}: {getattr(features, metric):.4f}")

    def update_callback(features: TimeDomainFeatures) -> None:
        print(
            f"t={features.timestamp:.2f}s | "
            f"RMS={features.rms:.4f} | "
            f"Peak={features.peak:.4f} | "
            f"P2P={features.peak_to_peak:.4f} | "
            f"Crest={features.crest_factor:.4f} | "
            f"Kurtosis={features.kurtosis:.4f}"
        )

    analyzer = TimeDomainAnalyzer(
        sample_rate=10240,
        refresh_interval=0.5,
    )
    analyzer.register_alert_callback(alert_callback)
    analyzer.register_update_callback(update_callback)

    simulator = SignalSimulator(
        sample_rate=SampleRate.SR_10240,
        fault_type=FaultType.BEARING_FAULT,
        severity=Severity.SEVERE,
        rpm=3000,
    )

    print("Starting time domain analysis (Ctrl+C to stop)...")
    try:
        for _ in range(10):
            _, signal = simulator.generate(duration=0.5)
            analyzer.analyze(signal, force=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nAnalysis stopped.")

    print("\nSummary:")
    summary = analyzer.get_summary()
    for metric, stats in summary.items():
        print(f"{metric}: min={stats['min']:.4f}, max={stats['max']:.4f}, mean={stats['mean']:.4f}")


if __name__ == "__main__":
    main()
