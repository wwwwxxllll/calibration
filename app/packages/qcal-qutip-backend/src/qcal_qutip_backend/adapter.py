"""Env-facing adapter; DeviceProfile remains owned by the QuTiP module."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from qcal_contracts import ExperimentPlan, RawResult
from qcal_qutip_backend.config.loader import load_device_profile
from qcal_qutip_backend.config.schema import DeviceProfile
from qcal_qutip_backend.control.compiler import ExperimentCompiler
from qcal_qutip_backend.control.sequences import CompiledExperiment
from qcal_qutip_backend.device.virtual_device import VirtualQuantumDevice
from qcal_qutip_backend.physics.couplings import dispersive_shift_hz


class QuTiPAdapter:
    """Load/manage the virtual device and return raw I/Q observations only."""

    def __init__(self, profile: DeviceProfile):
        self._device = VirtualQuantumDevice(profile)
        self._compiler = ExperimentCompiler(profile.control_chain)

    @classmethod
    def from_config(cls, profile_path: str | Path) -> "QuTiPAdapter":
        # Env passes only a path. Profile parsing and truth ownership stay here.
        return cls(load_device_profile(profile_path))

    def validate(self, plan: ExperimentPlan) -> None:
        compiled = self._compiler.compile(plan)
        if not compiled.points:
            raise ValueError("ExperimentPlan 至少需要一个扫描点。")

    def compile(self, plan: ExperimentPlan) -> CompiledExperiment:
        self.validate(plan)
        return self._compiler.compile(plan)

    def execute(self, plan: ExperimentPlan) -> RawResult:
        compiled = self.compile(plan)
        internal = self._device.execute_sequence(compiled)
        i_values = np.asarray(
            [point.observation.i_value for point in internal.points],
            dtype=float,
        )
        q_values = np.asarray(
            [point.observation.q_value for point in internal.points],
            dtype=float,
        )
        metadata = {"backend": "qutip", "fidelity": self._device.fidelity}
        readout = self._device.profile.quantum_system.readout_cavity
        qubit = self._device.profile.quantum_system.qubit
        chi_hz = dispersive_shift_hz(readout, qubit, self._device.profile.quantum_system.couplings)
        metadata["expected_readout_g_hz"] = readout.frequency_hz - chi_hz
        metadata["expected_readout_e_hz"] = readout.frequency_hz + chi_hz
        if compiled.metadata:
            metadata.update(compiled.metadata)
        if "shot_count" in metadata:
            shot_count = int(metadata["shot_count"])
            metadata["state_labels"] = ["g"] * shot_count + ["e"] * shot_count
        return RawResult(
            experiment_type=internal.experiment_type,
            sweep_name=internal.sweep_name,
            sweep_values=np.asarray(compiled.sweep_values, dtype=float),
            i_values=i_values,
            q_values=q_values,
            point_status=[point.status for point in internal.points],
            metadata=metadata,
        )
