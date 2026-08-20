from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from qcal_contracts import ExperimentType
from qcal_qutip_backend.measurement.iq_chain import IQObservation

if TYPE_CHECKING:
    import qutip as qt


@dataclass(frozen=True, slots=True)
class InternalPointResult:
    sweep_value: float
    status: str
    observation: IQObservation
    excited_probability: float
    dispersive_chi_hz: float
    effective_cavity_frequency_hz: float
    mean_photon_number: float
    density_matrix: qt.Qobj | None


@dataclass(frozen=True, slots=True)
class InternalExecutionResult:
    experiment_type: ExperimentType
    sweep_name: str
    points: tuple[InternalPointResult, ...]
    run_index: int
