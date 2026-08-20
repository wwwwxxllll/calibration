from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from qcal_qutip_backend.config.schema import MeasurementChainConfig


@dataclass(frozen=True, slots=True)
class IQObservation:
    i_value: float
    q_value: float


class IQChain:
    def __init__(self, params: MeasurementChainConfig):
        self.params = params

    def observe(
        self,
        field: complex,
        *,
        adc_full_scale: float,
        output_scale: float,
        repetitions: int,
        rng: np.random.Generator,
    ) -> IQObservation:
        rotated = self.params.gain * field * np.exp(1j * self.params.iq_rotation_rad)
        scale = max(float(output_scale), np.finfo(float).eps)
        full_scale = max(float(adc_full_scale) / scale, 1.0)
        i_value = rotated.real / scale + full_scale * self.params.i_offset
        q_value = rotated.imag / scale + full_scale * self.params.q_offset
        single_shot_noise = full_scale * (self.params.amplifier_noise + self.params.adc_noise)
        mean_noise = single_shot_noise / np.sqrt(repetitions)
        if mean_noise > 0.0:
            i_value += rng.normal(0.0, mean_noise)
            q_value += rng.normal(0.0, mean_noise)
        if self.params.adc_clip > 0.0:
            clip = self.params.adc_clip * full_scale
            i_value = float(np.clip(i_value, -clip, clip))
            q_value = float(np.clip(q_value, -clip, clip))
        return IQObservation(float(i_value), float(q_value))
