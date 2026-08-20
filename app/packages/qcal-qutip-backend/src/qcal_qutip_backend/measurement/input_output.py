from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qcal_qutip_backend.config.schema import ReadoutCavityConfig
from qcal_qutip_backend.control.pulses import ReadoutPulse

TWOPI = 2.0 * np.pi


@dataclass(frozen=True, slots=True)
class InputOutputFields:
    input_field: complex
    reflected_field: complex
    transmitted_field: complex | None
    selected_output_field: complex


def map_input_output(
    cavity: ReadoutCavityConfig,
    pulse: ReadoutPulse,
    intracavity_alpha: complex,
    *,
    output_field: str,
) -> InputOutputFields:
    input_field = complex(pulse.amplitude_sqrt_hz)
    leaked_field = np.sqrt(TWOPI * cavity.kappa_external_hz) * intracavity_alpha
    transmitted = -leaked_field
    reflected = input_field - leaked_field
    if output_field == "transmission":
        selected = transmitted
    elif output_field == "reflection":
        selected = reflected
    else:
        raise ValueError("output_field must be 'transmission' or 'reflection'.")
    return InputOutputFields(
        input_field=input_field,
        reflected_field=complex(reflected),
        transmitted_field=complex(transmitted),
        selected_output_field=complex(selected),
    )
