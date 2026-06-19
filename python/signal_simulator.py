import numpy as np
from enum import Enum
from typing import Optional, Tuple


class FaultType(Enum):
    NORMAL = "normal"
    MISALIGNMENT = "misalignment"
    UNBALANCE = "unbalance"
    BEARING_FAULT = "bearing_fault"
    GEAR_FAULT = "gear_fault"


class Severity(Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class SampleRate(Enum):
    SR_5120 = 5120
    SR_10240 = 10240
    SR_20480 = 20480
    SR_51200 = 51200


class SignalSimulator:
    def __init__(
        self,
        sample_rate: SampleRate = SampleRate.SR_10240,
        fault_type: FaultType = FaultType.NORMAL,
        severity: Severity = Severity.MILD,
        rpm: float = 3000,
        snr_db: float = 30.0,
    ):
        self.sample_rate = sample_rate
        self.fault_type = fault_type
        self.severity = severity
        self.rpm = rpm
        self.snr_db = snr_db
        self._fault_amplitude_factor = self._get_severity_factor()

    def _get_severity_factor(self) -> float:
        factors = {
            Severity.MILD: 1.5,
            Severity.MODERATE: 3.0,
            Severity.SEVERE: 6.0,
        }
        return factors[self.severity]

    def set_sample_rate(self, sample_rate: SampleRate) -> None:
        self.sample_rate = sample_rate

    def set_fault_type(self, fault_type: FaultType) -> None:
        self.fault_type = fault_type

    def set_severity(self, severity: Severity) -> None:
        self.severity = severity
        self._fault_amplitude_factor = self._get_severity_factor()

    def set_rpm(self, rpm: float) -> None:
        self.rpm = rpm

    def set_snr_db(self, snr_db: float) -> None:
        self.snr_db = snr_db

    def _rotational_frequency(self) -> float:
        return self.rpm / 60.0

    def _add_noise(self, signal: np.ndarray) -> np.ndarray:
        signal_power = np.mean(signal ** 2)
        noise_power = signal_power / (10 ** (self.snr_db / 10))
        noise = np.sqrt(noise_power) * np.random.randn(len(signal))
        return signal + noise

    def _generate_normal_signal(self, n_samples: int, t: np.ndarray) -> np.ndarray:
        f_rot = self._rotational_frequency()
        signal = (
            0.5 * np.sin(2 * np.pi * f_rot * t)
            + 0.2 * np.sin(2 * np.pi * 2 * f_rot * t)
            + 0.1 * np.sin(2 * np.pi * 3 * f_rot * t)
        )
        return signal

    def _generate_misalignment_signal(self, n_samples: int, t: np.ndarray) -> np.ndarray:
        f_rot = self._rotational_frequency()
        base_signal = self._generate_normal_signal(n_samples, t)
        fault_component = self._fault_amplitude_factor * (
            0.4 * np.sin(2 * np.pi * 2 * f_rot * t + np.pi / 4)
            + 0.2 * np.sin(2 * np.pi * 4 * f_rot * t + np.pi / 6)
            + 0.15 * np.sin(2 * np.pi * 1 * f_rot * t)
        )
        return base_signal + fault_component

    def _generate_unbalance_signal(self, n_samples: int, t: np.ndarray) -> np.ndarray:
        f_rot = self._rotational_frequency()
        base_signal = self._generate_normal_signal(n_samples, t)
        fault_component = self._fault_amplitude_factor * (
            0.6 * np.sin(2 * np.pi * f_rot * t + np.pi / 3)
            + 0.1 * np.sin(2 * np.pi * 2 * f_rot * t)
        )
        return base_signal + fault_component

    def _generate_bearing_fault_signal(self, n_samples: int, t: np.ndarray) -> np.ndarray:
        f_rot = self._rotational_frequency()
        base_signal = self._generate_normal_signal(n_samples, t)

        bpfo = 3.5 * f_rot
        bpfi = 5.5 * f_rot
        bsf = 2.8 * f_rot
        ftf = 0.4 * f_rot

        fault_amplitude = self._fault_amplitude_factor
        fault_component = np.zeros(n_samples)

        impulses = np.zeros(n_samples)
        impulse_interval = int(self.sample_rate.value / bpfo)
        for i in range(0, n_samples, impulse_interval):
            if i < n_samples:
                impulse_length = min(20, n_samples - i)
                decay = np.exp(-np.linspace(0, 5, impulse_length))
                impulses[i:i+impulse_length] = decay * np.sin(2 * np.pi * 2000 * t[i:i+impulse_length])

        fault_component += (
            fault_amplitude * 0.3 * np.sin(2 * np.pi * bpfo * t)
            + fault_amplitude * 0.2 * np.sin(2 * np.pi * bpfi * t)
            + fault_amplitude * 0.15 * np.sin(2 * np.pi * bsf * t)
            + fault_amplitude * 0.1 * np.sin(2 * np.pi * ftf * t)
            + fault_amplitude * 0.4 * impulses
        )

        return base_signal + fault_component

    def _generate_gear_fault_signal(self, n_samples: int, t: np.ndarray) -> np.ndarray:
        f_rot = self._rotational_frequency()
        base_signal = self._generate_normal_signal(n_samples, t)

        num_teeth = 24
        gear_mesh_freq = num_teeth * f_rot

        fault_amplitude = self._fault_amplitude_factor
        fault_component = np.zeros(n_samples)

        fault_component += (
            fault_amplitude * 0.4 * np.sin(2 * np.pi * gear_mesh_freq * t)
            + fault_amplitude * 0.2 * np.sin(2 * np.pi * gear_mesh_freq * t + np.pi / 4)
            * np.sin(2 * np.pi * f_rot * t)
            + fault_amplitude * 0.15 * np.sin(2 * np.pi * 2 * gear_mesh_freq * t)
            + fault_amplitude * 0.1 * np.sin(2 * np.pi * 3 * gear_mesh_freq * t)
        )

        sidebands = np.zeros(n_samples)
        for k in range(1, 4):
            sidebands += 0.1 * np.sin(2 * np.pi * (gear_mesh_freq - k * f_rot) * t)
            sidebands += 0.1 * np.sin(2 * np.pi * (gear_mesh_freq + k * f_rot) * t)
        fault_component += fault_amplitude * 0.3 * sidebands

        return base_signal + fault_component

    def generate(self, duration: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        n_samples = int(self.sample_rate.value * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)

        signal_generators = {
            FaultType.NORMAL: self._generate_normal_signal,
            FaultType.MISALIGNMENT: self._generate_misalignment_signal,
            FaultType.UNBALANCE: self._generate_unbalance_signal,
            FaultType.BEARING_FAULT: self._generate_bearing_fault_signal,
            FaultType.GEAR_FAULT: self._generate_gear_fault_signal,
        }

        generator = signal_generators[self.fault_type]
        clean_signal = generator(n_samples, t)
        noisy_signal = self._add_noise(clean_signal)

        return t, noisy_signal

    def generate_batch(self, num_segments: int, duration_per_segment: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        all_t = []
        all_signals = []
        total_time = 0.0

        for _ in range(num_segments):
            t, signal = self.generate(duration_per_segment)
            all_t.append(t + total_time)
            all_signals.append(signal)
            total_time += duration_per_segment

        return np.concatenate(all_t), np.concatenate(all_signals)


def main():
    import matplotlib.pyplot as plt

    simulator = SignalSimulator(
        sample_rate=SampleRate.SR_10240,
        fault_type=FaultType.BEARING_FAULT,
        severity=Severity.MODERATE,
        rpm=3000,
        snr_db=30.0,
    )

    t, signal = simulator.generate(duration=0.5)

    plt.figure(figsize=(10, 4))
    plt.plot(t, signal)
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title(f"Vibration Signal - {simulator.fault_type.value} ({simulator.severity.value})")
    plt.grid(True)
    plt.show()

    print(f"Signal length: {len(signal)} samples")
    print(f"Sample rate: {simulator.sample_rate.value} Hz")
    print(f"Duration: {t[-1]:.3f} s")
    print(f"RPM: {simulator.rpm}")
    print(f"SNR: {simulator.snr_db} dB")


if __name__ == "__main__":
    main()
