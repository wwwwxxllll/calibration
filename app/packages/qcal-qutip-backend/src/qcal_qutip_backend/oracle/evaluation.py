"""Test-harness-only access to effective calibration targets."""

from __future__ import annotations

from dataclasses import dataclass

from qcal_qutip_backend.config.schema import DeviceProfile
from qcal_qutip_backend.physics.couplings import dispersive_shift_hz


@dataclass(frozen=True, slots=True)
class OracleTruth:
    qubit_frequency_hz: float
    readout_frequency_g_hz: float
    readout_frequency_e_hz: float
    dispersive_chi_hz: float
    readout_state_separation_hz: float
    pi_amplitude: float
    t1_s: float
    chi_convention: str = "half_separation"


class DeviceOracle:
    """Construct this only in evaluation code, never in normal Agent tools."""

    def __init__(self, profile: DeviceProfile):
        self._profile = profile

    def current_truth(self) -> OracleTruth:
        quantum_system = self._profile.quantum_system
        qubit = quantum_system.qubit
        readout = quantum_system.readout_cavity
        chi_hz = dispersive_shift_hz(readout, qubit, quantum_system.couplings)
        fr_g_hz = readout.frequency_hz - chi_hz
        fr_e_hz = readout.frequency_hz + chi_hz
        return OracleTruth(
            qubit_frequency_hz=qubit.frequency_hz,
            readout_frequency_g_hz=fr_g_hz,
            readout_frequency_e_hz=fr_e_hz,
            dispersive_chi_hz=chi_hz,
            readout_state_separation_hz=fr_e_hz - fr_g_hz,
            pi_amplitude=qubit.pi_amplitude,
            t1_s=qubit.t1_s,
        )
