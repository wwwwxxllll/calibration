from __future__ import annotations

import numpy as np

from qcal_qutip_backend.config.schema import ControlChainConfig, QubitConfig
from qcal_qutip_backend.control.pulses import QubitDrive


class FastQubitResponseModel:
    def excited_probability(
        self,
        params: QubitConfig,
        drive: QubitDrive,
        *,
        control: ControlChainConfig,
    ) -> float:
        if drive.amplitude <= 0.0:
            return params.thermal_excited_population
        half_width_hz = 0.5 * params.linewidth_hz
        detuning_hz = drive.frequency_hz - params.frequency_hz
        spectral = half_width_hz**2 / (detuning_hz**2 + half_width_hz**2)
        bandwidth = np.exp(-0.5 * (detuning_hz / control.gaussian_bandwidth_hz) ** 2)
        effective_amplitude = drive.amplitude * bandwidth
        rabi = np.sin(0.5 * np.pi * effective_amplitude / params.pi_amplitude) ** 2
        thermal = params.thermal_excited_population
        return float(np.clip(thermal + (1.0 - thermal) * spectral * rabi, 0.0, 1.0))
