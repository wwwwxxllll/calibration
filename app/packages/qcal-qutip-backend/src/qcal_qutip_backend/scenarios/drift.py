from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qcal_qutip_backend.config.schema import DriftConfig


@dataclass(frozen=True, slots=True)
class NoDrift:
    def frequency_offset_hz(self, parameter: str, elapsed_s: float) -> float:
        del parameter, elapsed_s
        return 0.0


@dataclass(slots=True)
class ProfileDrift:
    params: DriftConfig
    seed: int

    def frequency_offset_hz(self, parameter: str, elapsed_s: float) -> float:
        elapsed_s = max(float(elapsed_s), 0.0)
        if parameter == "qubit_frequency_hz" and self.params.qubit_frequency.model == "random_walk":
            sigma = self.params.qubit_frequency.sigma_hz_per_sqrt_s * np.sqrt(elapsed_s)
            if sigma <= 0.0:
                return 0.0
            rng = np.random.default_rng(self.seed + int(elapsed_s * 1.0e6) + 17)
            return float(rng.normal(0.0, sigma))
        if parameter == "readout_frequency_hz" and self.params.readout_frequency.model == "slow_sinusoid":
            config = self.params.readout_frequency
            return float(config.amplitude_hz * np.sin(2.0 * np.pi * elapsed_s / config.period_s))
        return 0.0
