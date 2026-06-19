import json
from signal_simulator import SignalSimulator, SampleRate, FaultType, Severity
from routers.analysis import (
    _extract_time_domain_features,
    _extract_frequency_domain_features,
    _calculate_health_index,
)

results = []
for did, fault in [(1, FaultType.NORMAL), (3, FaultType.BEARING_FAULT)]:
    for sev in [Severity.MILD, Severity.SEVERE]:
        sim = SignalSimulator(SampleRate.SR_10240, fault, sev, 3000, 30.0)
        _, signal = sim.generate(duration=0.2)
        td = _extract_time_domain_features(signal)
        fd = _extract_frequency_domain_features(signal, sim.sample_rate.value)
        health, status_text, anomalies = _calculate_health_index(td, fd)
        results.append(
            "device=%d sev=%s len=%d rms=%.4f freq=%.2f health=%.1f status=%s"
            % (did, sev.value, len(signal), td.rms, fd.dominant_frequency, health, status_text)
        )

with open("_push_out.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print("done")
