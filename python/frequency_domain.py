import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq, ifft
from scipy.signal import hilbert, find_peaks
from typing import Tuple, List, Optional, Dict


class FrequencyDomain:
    def __init__(self, sample_rate: float = 25600.0):
        self.sample_rate = sample_rate
        self.valid_window_sizes = [1024, 2048, 4096]
        self._cached_window = {}

    def _get_window(self, window_size: int) -> np.ndarray:
        if window_size not in self._cached_window:
            self._cached_window[window_size] = np.hanning(window_size)
        return self._cached_window[window_size]

    def _validate_window_size(self, window_size: int) -> int:
        if window_size not in self.valid_window_sizes:
            closest = min(self.valid_window_sizes, key=lambda x: abs(x - window_size))
            return closest
        return window_size

    def compute_fft(self,
                    data: np.ndarray,
                    window_size: int = 2048,
                    overlap: float = 0.5,
                    remove_dc: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        window_size = self._validate_window_size(window_size)
        data = np.asarray(data, dtype=np.float64)

        if remove_dc:
            data = data - np.mean(data)

        window = self._get_window(window_size)
        window_power = np.sum(window ** 2)

        step = int(window_size * (1 - overlap))
        n_segments = (len(data) - window_size) // step + 1

        if n_segments < 1:
            n_segments = 1
            step = 0

        fft_sum = np.zeros(window_size // 2 + 1, dtype=np.complex128)

        for i in range(n_segments):
            start = i * step
            segment = data[start:start + window_size] * window
            fft_result = fft(segment)
            fft_sum += fft_result[:window_size // 2 + 1]

        fft_avg = fft_sum / n_segments

        freqs = fftfreq(window_size, 1.0 / self.sample_rate)[:window_size // 2 + 1]
        amplitudes = np.abs(fft_avg) * 2.0 / np.sqrt(window_power)

        return freqs, amplitudes

    def compute_spectrum(self,
                         data: np.ndarray,
                         window_size: int = 2048,
                         overlap: float = 0.5,
                         db_scale: bool = False,
                         db_reference: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        freqs, amplitudes = self.compute_fft(data, window_size, overlap)

        if db_scale:
            with np.errstate(divide='ignore'):
                amplitudes_db = 20 * np.log10(amplitudes / db_reference + 1e-12)
            return freqs, amplitudes_db

        return freqs, amplitudes

    def detect_peaks(self,
                     freqs: np.ndarray,
                     amplitudes: np.ndarray,
                     num_peaks: int = 10,
                     min_prominence: float = 0.05,
                     min_distance: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        amplitudes = np.asarray(amplitudes, dtype=np.float64)
        max_amp = np.max(amplitudes) if len(amplitudes) > 0 else 1.0
        prominence = max(min_prominence * max_amp, 1e-10)

        peak_indices, properties = find_peaks(
            amplitudes,
            prominence=prominence,
            distance=min_distance,
            height=0.05 * max_amp
        )

        if len(peak_indices) == 0:
            return np.array([]), np.array([])

        peak_heights = amplitudes[peak_indices]
        sorted_indices = np.argsort(peak_heights)[::-1]
        top_indices = sorted_indices[:num_peaks]

        peak_freqs = freqs[peak_indices[top_indices]]
        peak_amps = peak_heights[top_indices]

        return peak_freqs, peak_amps

    def compute_envelope_spectrum(self,
                                   data: np.ndarray,
                                   window_size: int = 2048,
                                   overlap: float = 0.5,
                                   bandpass_low: Optional[float] = None,
                                   bandpass_high: Optional[float] = None,
                                   db_scale: bool = False) -> Tuple[np.ndarray, np.ndarray]:
        data = np.asarray(data, dtype=np.float64)
        data = data - np.mean(data)

        if bandpass_low is not None and bandpass_high is not None:
            nyquist = 0.5 * self.sample_rate
            low = bandpass_low / nyquist
            high = bandpass_high / nyquist
            if low > 0 and high < 1:
                b, a = signal.butter(4, [low, high], btype='band')
                data = signal.filtfilt(b, a, data)

        analytic_signal = hilbert(data)
        envelope = np.abs(analytic_signal)
        envelope = envelope - np.mean(envelope)

        return self.compute_spectrum(envelope, window_size, overlap, db_scale)

    def convert_to_log_scale(self,
                              freqs: np.ndarray,
                              amplitudes: np.ndarray,
                              log_x: bool = False,
                              log_y: bool = False,
                              db_reference: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        out_freqs = freqs.copy()
        out_amps = amplitudes.copy()

        if log_y and np.min(out_amps) >= 0:
            with np.errstate(divide='ignore'):
                out_amps = 20 * np.log10(out_amps / db_reference + 1e-12)

        if log_x:
            with np.errstate(divide='ignore', invalid='ignore'):
                out_freqs = np.log10(out_freqs)

        return out_freqs, out_amps

    def frequency_cursor(self,
                         freqs: np.ndarray,
                         amplitudes: np.ndarray,
                         target_freq: float,
                         tolerance: float = 0.02) -> Dict:
        freqs = np.asarray(freqs, dtype=np.float64)
        amplitudes = np.asarray(amplitudes, dtype=np.float64)

        min_tol = target_freq * (1 - tolerance)
        max_tol = target_freq * (1 + tolerance)

        mask = (freqs >= min_tol) & (freqs <= max_tol)
        if not np.any(mask):
            closest_idx = np.argmin(np.abs(freqs - target_freq))
            closest_freq = freqs[closest_idx]
            deviation = abs(closest_freq - target_freq) / target_freq * 100
            return {
                'target_frequency': target_freq,
                'found': False,
                'closest_frequency': float(closest_freq),
                'closest_amplitude': float(amplitudes[closest_idx]),
                'deviation_percent': float(deviation),
                'tolerance': tolerance * 100
            }

        filtered_indices = np.where(mask)[0]
        peak_idx = filtered_indices[np.argmax(amplitudes[filtered_indices])]
        found_freq = freqs[peak_idx]
        found_amp = amplitudes[peak_idx]
        deviation = abs(found_freq - target_freq) / target_freq * 100

        return {
            'target_frequency': target_freq,
            'found': True,
            'closest_frequency': float(found_freq),
            'closest_amplitude': float(found_amp),
            'deviation_percent': float(deviation),
            'tolerance': tolerance * 100,
            'matching_peaks': [
                {
                    'frequency': float(freqs[idx]),
                    'amplitude': float(amplitudes[idx]),
                    'deviation_percent': float(abs(freqs[idx] - target_freq) / target_freq * 100)
                }
                for idx in filtered_indices
            ]
        }

    def get_frequency_resolution(self, window_size: int) -> float:
        window_size = self._validate_window_size(window_size)
        return self.sample_rate / window_size

    def get_nyquist_frequency(self) -> float:
        return self.sample_rate / 2.0

    def welch_method(self,
                      data: np.ndarray,
                      window_size: int = 2048,
                      overlap: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        window_size = self._validate_window_size(window_size)
        data = np.asarray(data, dtype=np.float64) - np.mean(data)
        nperseg = window_size
        noverlap = int(window_size * overlap)

        f, Pxx = signal.welch(
            data,
            fs=self.sample_rate,
            window='hann',
            nperseg=nperseg,
            noverlap=noverlap,
            scaling='spectrum'
        )

        return f, np.sqrt(Pxx)
