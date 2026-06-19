import numpy as np
from typing import Dict, Tuple, Optional, List, Union
from dataclasses import dataclass, field


@dataclass
class BearingParameters:
    roller_count: int
    pitch_diameter: float
    roller_diameter: float
    contact_angle_deg: float = 0.0

    def validate(self) -> bool:
        if self.roller_count <= 0:
            return False
        if self.pitch_diameter <= 0:
            return False
        if self.roller_diameter <= 0:
            return False
        if self.roller_diameter >= self.pitch_diameter:
            return False
        return True


@dataclass
class GearParameters:
    tooth_count: int
    rpm: float = 0.0

    def validate(self) -> bool:
        if self.tooth_count <= 0:
            return False
        return True


@dataclass
class FrequencyMatch:
    target_freq: float
    actual_freq: float
    deviation_percent: float
    tolerance_percent: float
    matched: bool
    harmonic_order: int = 1
    sideband: Optional[float] = None


class FeatureFrequency:
    HIT_TOLERANCE = 0.02

    def __init__(self):
        pass

    @staticmethod
    def _rpm_to_hz(rpm: float) -> float:
        return rpm / 60.0

    @staticmethod
    def _hz_to_rpm(hz: float) -> float:
        return hz * 60.0

    @staticmethod
    def _deg_to_rad(deg: float) -> float:
        return np.deg2rad(deg)

    def calculate_bearing_frequencies(self,
                                       bearing_params: BearingParameters,
                                       rpm: float) -> Dict[str, float]:
        if not bearing_params.validate():
            raise ValueError("Invalid bearing parameters")

        N = bearing_params.roller_count
        D = bearing_params.pitch_diameter
        d = bearing_params.roller_diameter
        alpha = self._deg_to_rad(bearing_params.contact_angle_deg)
        f_r = self._rpm_to_hz(rpm)

        ratio = d / D
        cos_alpha = np.cos(alpha)

        bpfo = (N / 2.0) * f_r * (1.0 - ratio * cos_alpha)
        bpfi = (N / 2.0) * f_r * (1.0 + ratio * cos_alpha)
        bsf = (D / (2.0 * d)) * f_r * (1.0 - (ratio ** 2) * (cos_alpha ** 2))
        ftf = 0.5 * f_r * (1.0 - ratio * cos_alpha)

        return {
            'BPFO': float(bpfo),
            'BPFI': float(bpfi),
            'BSF': float(bsf),
            'FTF': float(ftf),
            'BPFO_rpm': self._hz_to_rpm(bpfo),
            'BPFI_rpm': self._hz_to_rpm(bpfi),
            'BSF_rpm': self._hz_to_rpm(bsf),
            'FTF_rpm': self._hz_to_rpm(ftf),
            'rotational_freq': float(f_r),
            'rotational_freq_rpm': float(rpm)
        }

    def calculate_gear_mesh_frequency(self,
                                       gear_params: GearParameters) -> Dict[str, float]:
        if not gear_params.validate():
            raise ValueError("Invalid gear parameters")

        Z = gear_params.tooth_count
        f_r = self._rpm_to_hz(gear_params.rpm)
        gmf = Z * f_r

        return {
            'GMF': float(gmf),
            'GMF_rpm': self._hz_to_rpm(gmf),
            'rotational_freq': float(f_r),
            'rotational_freq_rpm': float(gear_params.rpm),
            'tooth_count': Z
        }

    def calculate_gearset_frequencies(self,
                                       pinion_params: GearParameters,
                                       gear_params: Optional[GearParameters] = None,
                                       rpm_pinion: Optional[float] = None) -> Dict[str, float]:
        if rpm_pinion is not None:
            pinion_params.rpm = rpm_pinion

        if not pinion_params.validate():
            raise ValueError("Invalid pinion parameters")

        pinion_freqs = self.calculate_gear_mesh_frequency(pinion_params)

        if gear_params is None:
            return pinion_freqs

        if not gear_params.validate():
            raise ValueError("Invalid gear parameters")

        gear_ratio = pinion_params.tooth_count / gear_params.tooth_count
        gear_params.rpm = pinion_params.rpm * gear_ratio

        gear_freqs = self.calculate_gear_mesh_frequency(gear_params)

        return {
            'pinion': pinion_freqs,
            'gear': gear_freqs,
            'gear_ratio': float(gear_ratio),
            'GMF': pinion_freqs['GMF']
        }

    def check_frequency_match(self,
                                measured_freq: float,
                                theoretical_freq: float,
                                tolerance: Optional[float] = None,
                                include_harmonics: bool = True,
                                max_harmonics: int = 5,
                                include_sidebands: bool = False,
                                sideband_spacing: Optional[float] = None,
                                max_sidebands: int = 3) -> FrequencyMatch:
        tol = tolerance if tolerance is not None else self.HIT_TOLERANCE
        best_match = None
        min_deviation = float('inf')

        candidate_freqs = [(theoretical_freq, 1, None)]

        if include_harmonics:
            for n in range(2, max_harmonics + 1):
                candidate_freqs.append((theoretical_freq * n, n, None))

        if include_sidebands and sideband_spacing is not None:
            for n in range(1, max_harmonics + 1):
                for m in range(1, max_sidebands + 1):
                    candidate_freqs.append((theoretical_freq * n - sideband_spacing * m, n, -sideband_spacing * m))
                    candidate_freqs.append((theoretical_freq * n + sideband_spacing * m, n, sideband_spacing * m))

        for freq, harmonic, sideband in candidate_freqs:
            if freq <= 0:
                continue
            deviation = abs(measured_freq - freq) / freq * 100.0
            if deviation < min_deviation:
                min_deviation = deviation
                matched = deviation <= (tol * 100.0)
                best_match = FrequencyMatch(
                    target_freq=float(freq),
                    actual_freq=float(measured_freq),
                    deviation_percent=float(deviation),
                    tolerance_percent=float(tol * 100.0),
                    matched=matched,
                    harmonic_order=harmonic,
                    sideband=sideband
                )

        return best_match

    def find_feature_in_spectrum(self,
                                  freqs: np.ndarray,
                                  amplitudes: np.ndarray,
                                  theoretical_freq: float,
                                  tolerance: Optional[float] = None) -> Dict:
        tol = tolerance if tolerance is not None else self.HIT_TOLERANCE
        freqs = np.asarray(freqs, dtype=np.float64)
        amplitudes = np.asarray(amplitudes, dtype=np.float64)

        min_tol = theoretical_freq * (1 - tol)
        max_tol = theoretical_freq * (1 + tol)

        mask = (freqs >= min_tol) & (freqs <= max_tol)
        if not np.any(mask):
            closest_idx = np.argmin(np.abs(freqs - theoretical_freq))
            closest_freq = freqs[closest_idx]
            deviation = abs(closest_freq - theoretical_freq) / theoretical_freq * 100
            return {
                'theoretical_freq': float(theoretical_freq),
                'found': False,
                'closest_freq': float(closest_freq),
                'closest_amplitude': float(amplitudes[closest_idx]),
                'deviation_percent': float(deviation),
                'tolerance_percent': float(tol * 100)
            }

        filtered_indices = np.where(mask)[0]
        peak_idx = filtered_indices[np.argmax(amplitudes[filtered_indices])]
        found_freq = freqs[peak_idx]
        found_amp = amplitudes[peak_idx]
        deviation = abs(found_freq - theoretical_freq) / theoretical_freq * 100

        return {
            'theoretical_freq': float(theoretical_freq),
            'found': True,
            'closest_freq': float(found_freq),
            'closest_amplitude': float(found_amp),
            'deviation_percent': float(deviation),
            'tolerance_percent': float(tol * 100),
            'all_matches': [
                {
                    'frequency': float(freqs[idx]),
                    'amplitude': float(amplitudes[idx]),
                    'deviation_percent': float(abs(freqs[idx] - theoretical_freq) / theoretical_freq * 100)
                }
                for idx in filtered_indices
            ]
        }

    def analyze_bearing_spectrum(self,
                                  freqs: np.ndarray,
                                  amplitudes: np.ndarray,
                                  bearing_params: BearingParameters,
                                  rpm: float) -> Dict:
        bearing_freqs = self.calculate_bearing_frequencies(bearing_params, rpm)
        results = {}

        for key in ['BPFO', 'BPFI', 'BSF', 'FTF']:
            theoretical = bearing_freqs[key]
            match = self.find_feature_in_spectrum(freqs, amplitudes, theoretical)
            results[key] = match

        rotational_match = self.find_feature_in_spectrum(freqs, amplitudes, bearing_freqs['rotational_freq'])
        results['rotational'] = rotational_match

        return {
            'bearing_parameters': bearing_params.__dict__,
            'theoretical_frequencies': bearing_freqs,
            'matches': results
        }

    def analyze_gear_spectrum(self,
                               freqs: np.ndarray,
                               amplitudes: np.ndarray,
                               gear_params: GearParameters) -> Dict:
        gear_freqs = self.calculate_gear_mesh_frequency(gear_params)
        rotational_match = self.find_feature_in_spectrum(freqs, amplitudes, gear_freqs['rotational_freq'])
        gmf_match = self.find_feature_in_spectrum(freqs, amplitudes, gear_freqs['GMF'])

        gmf_harmonics = {}
        for n in range(2, 6):
            harmonic_freq = gear_freqs['GMF'] * n
            harmonic_match = self.find_feature_in_spectrum(freqs, amplitudes, harmonic_freq)
            gmf_harmonics[f'GMF_{n}x'] = harmonic_match

        return {
            'gear_parameters': gear_params.__dict__,
            'theoretical_frequencies': gear_freqs,
            'matches': {
                'rotational': rotational_match,
                'GMF': gmf_match,
                **gmf_harmonics
            }
        }

    def batch_check_matches(self,
                             measured_freqs: List[float],
                             theoretical_freqs: Dict[str, float],
                             tolerance: Optional[float] = None) -> Dict[str, List[FrequencyMatch]]:
        tol = tolerance if tolerance is not None else self.HIT_TOLERANCE
        results = {}

        for name, theoretical in theoretical_freqs.items():
            matches = []
            for measured in measured_freqs:
                match = self.check_frequency_match(measured, theoretical, tol)
                matches.append(match)
            results[name] = matches

        return results

    def calculate_bearing_life(self,
                                bearing_params: BearingParameters,
                                rpm: float,
                                dynamic_load_rating: float,
                                applied_load: float) -> Dict[str, float]:
        if applied_load <= 0:
            raise ValueError("Applied load must be positive")
        if dynamic_load_rating <= 0:
            raise ValueError("Dynamic load rating must be positive")

        n = rpm
        C = dynamic_load_rating
        P = applied_load

        L10_revs = (C / P) ** 3 * 1e6
        L10_hours = L10_revs / (60 * n)

        return {
            'L10_revolutions': float(L10_revs),
            'L10_hours': float(L10_hours),
            'L10_days': float(L10_hours / 24),
            'load_ratio': float(C / P)
        }
