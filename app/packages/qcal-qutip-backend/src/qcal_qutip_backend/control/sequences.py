from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qcal_contracts import ExperimentType
from qcal_qutip_backend.control.pulses import QubitDrive, ReadoutPulse


@dataclass(frozen=True, slots=True)
class CompiledPoint:
    sweep_value: float
    qubit_drive: QubitDrive
    readout_pulse: ReadoutPulse
    metadata: dict[str, object] | None = None


@dataclass(frozen=True, slots=True)
class CompiledExperiment:
    experiment_type: ExperimentType
    sweep_name: str
    sweep_values: np.ndarray
    repetitions: int
    cycle_period_s: float
    points: tuple[CompiledPoint, ...]
    metadata: dict[str, object] | None = None
