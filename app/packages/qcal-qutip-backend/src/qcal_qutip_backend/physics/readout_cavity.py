from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import qutip as qt

from qcal_qutip_backend.config.schema import ReadoutCavityConfig
from qcal_qutip_backend.control.pulses import ReadoutPulse

TWOPI = 2.0 * np.pi


@dataclass(frozen=True, slots=True)
class CavityState:
    intracavity_alpha: complex
    mean_photon_number: float
    density_matrix: qt.Qobj


class QuTiPSteadyStateCavitySolver:
    def __init__(self, params: ReadoutCavityConfig):
        params.validate()
        self.params = params
        self.a = qt.destroy(params.hilbert_dim)

    def solve(self, pulse: ReadoutPulse, *, effective_cavity_frequency_hz: float) -> CavityState:
        detuning = TWOPI * (pulse.frequency_hz - effective_cavity_frequency_hz)
        kappa_external = TWOPI * self.params.kappa_external_hz
        input_field = pulse.amplitude_sqrt_hz
        drive_hamiltonian = 1j * np.sqrt(kappa_external) * (
            input_field * self.a.dag() - np.conjugate(input_field) * self.a
        )
        hamiltonian = detuning * self.a.dag() * self.a + drive_hamiltonian
        density_matrix = qt.steadystate(hamiltonian, self._collapse_operators(), method="direct")
        alpha = complex(qt.expect(self.a, density_matrix))
        photons = float(np.real(qt.expect(self.a.dag() * self.a, density_matrix)))
        return CavityState(alpha, photons, density_matrix)

    def _collapse_operators(self) -> list[qt.Qobj]:
        rates = (
            TWOPI * self.params.kappa_external_hz,
            TWOPI * self.params.kappa_internal_hz,
        )
        return [np.sqrt(rate) * self.a for rate in rates if rate > 0.0]
