import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Callable
from enum import Enum
from datetime import datetime, timedelta
import time
from scipy import stats


class TimeRange(str, Enum):
    HOUR_1 = "1h"
    HOUR_8 = "8h"
    HOUR_24 = "24h"
    DAY_7 = "7d"


class TrendStatus(str, Enum):
    STABLE = "stable"
    RISING = "rising"
    FALLING = "falling"
    UNKNOWN = "unknown"


@dataclass
class TrendMetrics:
    timestamp: float
    rms: float
    peak: float
    peak_to_peak: float
    crest_factor: float
    kurtosis: float


@dataclass
class TrendReferenceLines:
    baseline: float
    warning: float
    alarm: float


@dataclass
class LinearRegressionResult:
    slope: float
    intercept: float
    r_value: float
    p_value: float
    std_err: float
    r_squared: float


@dataclass
class TrendAnalysisResult:
    time_range: TimeRange
    metric: str
    timestamps: List[float]
    values: List[float]
    regression: LinearRegressionResult
    status: TrendStatus
    reference_lines: TrendReferenceLines
    start_time: float
    end_time: float
    data_points: int


class TrendAnalyzer:
    TIME_RANGE_SECONDS = {
        TimeRange.HOUR_1: 3600,
        TimeRange.HOUR_8: 28800,
        TimeRange.HOUR_24: 86400,
        TimeRange.DAY_7: 604800,
    }

    R_SQUARED_THRESHOLD = 0.7

    def __init__(
        self,
        reference_lines: Optional[TrendReferenceLines] = None,
        max_history_size: int = 10000,
    ):
        self._history: List[TrendMetrics] = []
        self._max_history_size = max_history_size
        self._reference_lines = reference_lines or TrendReferenceLines(
            baseline=1.0,
            warning=2.0,
            alarm=5.0,
        )
        self._trend_callbacks: List[Callable[[TrendAnalysisResult], None]] = []

    def set_reference_lines(self, reference_lines: TrendReferenceLines) -> None:
        self._reference_lines = reference_lines

    def get_reference_lines(self) -> TrendReferenceLines:
        return self._reference_lines

    def register_trend_callback(
        self,
        callback: Callable[[TrendAnalysisResult], None],
    ) -> None:
        self._trend_callbacks.append(callback)

    def clear_callbacks(self) -> None:
        self._trend_callbacks.clear()

    def add_metrics(self, metrics: TrendMetrics) -> None:
        self._history.append(metrics)
        if len(self._history) > self._max_history_size:
            self._history = self._history[-self._max_history_size:]

    def add_metrics_values(
        self,
        rms: float,
        peak: float,
        peak_to_peak: float,
        crest_factor: float,
        kurtosis: float,
        timestamp: Optional[float] = None,
    ) -> None:
        metrics = TrendMetrics(
            timestamp=timestamp or time.time(),
            rms=rms,
            peak=peak,
            peak_to_peak=peak_to_peak,
            crest_factor=crest_factor,
            kurtosis=kurtosis,
        )
        self.add_metrics(metrics)

    def clear_history(self) -> None:
        self._history.clear()

    def get_history(self) -> List[TrendMetrics]:
        return list(self._history)

    def _filter_by_time_range(
        self,
        time_range: TimeRange,
        end_time: Optional[float] = None,
    ) -> List[TrendMetrics]:
        end_time = end_time or time.time()
        start_time = end_time - self.TIME_RANGE_SECONDS[time_range]

        return [
            m for m in self._history
            if start_time <= m.timestamp <= end_time
        ]

    def _extract_metric_values(
        self,
        filtered_data: List[TrendMetrics],
        metric: str,
    ) -> Tuple[List[float], List[float]]:
        timestamps = []
        values = []

        for m in filtered_data:
            timestamps.append(m.timestamp)
            values.append(getattr(m, metric))

        return timestamps, values

    @staticmethod
    def perform_linear_regression(
        x: np.ndarray,
        y: np.ndarray,
    ) -> LinearRegressionResult:
        if len(x) < 2 or len(y) < 2:
            return LinearRegressionResult(
                slope=0.0,
                intercept=0.0,
                r_value=0.0,
                p_value=1.0,
                std_err=0.0,
                r_squared=0.0,
            )

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2

        return LinearRegressionResult(
            slope=float(slope),
            intercept=float(intercept),
            r_value=float(r_value),
            p_value=float(p_value),
            std_err=float(std_err),
            r_squared=float(r_squared),
        )

    def _determine_trend_status(
        self,
        regression: LinearRegressionResult,
    ) -> TrendStatus:
        if regression.r_squared < self.R_SQUARED_THRESHOLD:
            return TrendStatus.UNKNOWN

        if regression.slope > 0:
            return TrendStatus.RISING
        elif regression.slope < 0:
            return TrendStatus.FALLING
        else:
            return TrendStatus.STABLE

    def detect_rising_trend(
        self,
        regression: LinearRegressionResult,
    ) -> bool:
        return (
            regression.slope > 0
            and regression.r_squared > self.R_SQUARED_THRESHOLD
        )

    def analyze_trend(
        self,
        time_range: TimeRange,
        metric: str = "rms",
        end_time: Optional[float] = None,
        trigger_callbacks: bool = True,
    ) -> TrendAnalysisResult:
        valid_metrics = ["rms", "peak", "peak_to_peak", "crest_factor", "kurtosis"]
        if metric not in valid_metrics:
            raise ValueError(
                f"Invalid metric '{metric}'. Must be one of: {valid_metrics}"
            )

        end_time = end_time or time.time()
        start_time = end_time - self.TIME_RANGE_SECONDS[time_range]

        filtered_data = self._filter_by_time_range(time_range, end_time)
        timestamps, values = self._extract_metric_values(filtered_data, metric)

        if len(timestamps) < 2:
            regression = LinearRegressionResult(
                slope=0.0,
                intercept=0.0,
                r_value=0.0,
                p_value=1.0,
                std_err=0.0,
                r_squared=0.0,
            )
            status = TrendStatus.UNKNOWN
        else:
            x = np.array(timestamps)
            y = np.array(values)
            x_normalized = x - x[0]

            regression = self.perform_linear_regression(x_normalized, y)
            status = self._determine_trend_status(regression)

        result = TrendAnalysisResult(
            time_range=time_range,
            metric=metric,
            timestamps=timestamps,
            values=values,
            regression=regression,
            status=status,
            reference_lines=self._reference_lines,
            start_time=start_time,
            end_time=end_time,
            data_points=len(timestamps),
        )

        if trigger_callbacks and len(timestamps) >= 2:
            for callback in self._trend_callbacks:
                callback(result)

        return result

    def analyze_all_metrics(
        self,
        time_range: TimeRange,
        end_time: Optional[float] = None,
    ) -> Dict[str, TrendAnalysisResult]:
        metrics = ["rms", "peak", "peak_to_peak", "crest_factor", "kurtosis"]
        results = {}

        for metric in metrics:
            results[metric] = self.analyze_trend(
                time_range=time_range,
                metric=metric,
                end_time=end_time,
                trigger_callbacks=False,
            )

        return results

    def analyze_all_time_ranges(
        self,
        metric: str = "rms",
        end_time: Optional[float] = None,
    ) -> Dict[TimeRange, TrendAnalysisResult]:
        time_ranges = [
            TimeRange.HOUR_1,
            TimeRange.HOUR_8,
            TimeRange.HOUR_24,
            TimeRange.DAY_7,
        ]
        results = {}

        for time_range in time_ranges:
            results[time_range] = self.analyze_trend(
                time_range=time_range,
                metric=metric,
                end_time=end_time,
                trigger_callbacks=False,
            )

        return results

    def get_trend_summary(
        self,
        end_time: Optional[float] = None,
    ) -> Dict:
        end_time = end_time or time.time()
        summary = {}

        for time_range in TimeRange:
            time_range_summary = {}
            results = self.analyze_all_metrics(time_range, end_time)

            for metric, result in results.items():
                if result.data_points > 0:
                    values = np.array(result.values)
                    time_range_summary[metric] = {
                        "min": float(np.min(values)),
                        "max": float(np.max(values)),
                        "mean": float(np.mean(values)),
                        "std": float(np.std(values)),
                        "latest": values[-1],
                        "trend": result.status.value,
                        "slope": result.regression.slope,
                        "r_squared": result.regression.r_squared,
                        "is_rising": self.detect_rising_trend(result.regression),
                        "data_points": result.data_points,
                    }

            summary[time_range.value] = time_range_summary

        return summary

    def generate_trend_data(
        self,
        time_range: TimeRange,
        metric: str = "rms",
        end_time: Optional[float] = None,
    ) -> Dict:
        result = self.analyze_trend(time_range, metric, end_time, trigger_callbacks=False)

        if result.data_points < 2:
            regression_line = []
        else:
            x = np.array(result.timestamps)
            x_normalized = x - x[0]
            regression_line = (
                result.regression.slope * x_normalized + result.regression.intercept
            ).tolist()

        return {
            "time_range": time_range.value,
            "metric": metric,
            "timestamps": [
                datetime.fromtimestamp(t).isoformat()
                for t in result.timestamps
            ],
            "values": result.values,
            "regression_line": regression_line,
            "status": result.status.value,
            "is_rising": self.detect_rising_trend(result.regression),
            "reference_lines": {
                "baseline": result.reference_lines.baseline,
                "warning": result.reference_lines.warning,
                "alarm": result.reference_lines.alarm,
            },
            "statistics": {
                "slope": result.regression.slope,
                "intercept": result.regression.intercept,
                "r_value": result.regression.r_value,
                "r_squared": result.regression.r_squared,
                "p_value": result.regression.p_value,
                "std_err": result.regression.std_err,
            },
            "data_points": result.data_points,
            "start_time": datetime.fromtimestamp(result.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(result.end_time).isoformat(),
        }


def main():
    print("Trend Analysis Module Test")
    print("=" * 60)

    analyzer = TrendAnalyzer(
        reference_lines=TrendReferenceLines(
            baseline=1.0,
            warning=2.0,
            alarm=5.0,
        )
    )

    base_time = time.time() - 3600
    print("\nGenerating test data with rising trend...")
    for i in range(60):
        t = base_time + i * 60
        base_rms = 0.5 + 0.02 * i
        noise = np.random.normal(0, 0.05)
        rms = base_rms + noise

        analyzer.add_metrics_values(
            rms=rms,
            peak=rms * 2.5,
            peak_to_peak=rms * 4.5,
            crest_factor=2.5 + np.random.normal(0, 0.2),
            kurtosis=3.0 + np.random.normal(0, 0.3),
            timestamp=t,
        )

    print("\nAnalyzing trends for different time ranges:")
    for time_range in TimeRange:
        result = analyzer.analyze_trend(
            time_range=time_range,
            metric="rms",
            trigger_callbacks=False,
        )
        print(f"\n  {time_range.value}:")
        print(f"    Data points: {result.data_points}")
        print(f"    Status: {result.status.value}")
        print(f"    Slope: {result.regression.slope:.6f}")
        print(f"    R^2: {result.regression.r_squared:.4f}")
        print(f"    Is rising: {analyzer.detect_rising_trend(result.regression)}")

    print("\nTrend Summary:")
    summary = analyzer.get_trend_summary()
    for tr, metrics in summary.items():
        if metrics and "rms" in metrics:
            print(f"  {tr}: RMS={metrics['rms']['latest']:.4f}, "
                  f"trend={metrics['rms']['trend']}, "
                  f"rising={metrics['rms']['is_rising']}")

    print("\nGenerating trend data for visualization:")
    trend_data = analyzer.generate_trend_data(TimeRange.HOUR_1, "rms")
    print(f"  Time range: {trend_data['time_range']}")
    print(f"  Metric: {trend_data['metric']}")
    print(f"  Data points: {trend_data['data_points']}")
    print(f"  Status: {trend_data['status']}")
    print(f"  Is rising: {trend_data['is_rising']}")
    print(f"  Reference lines: baseline={trend_data['reference_lines']['baseline']}, "
          f"warning={trend_data['reference_lines']['warning']}, "
          f"alarm={trend_data['reference_lines']['alarm']}")


if __name__ == "__main__":
    main()
