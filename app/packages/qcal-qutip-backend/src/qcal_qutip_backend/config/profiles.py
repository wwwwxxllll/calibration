from __future__ import annotations

from dataclasses import replace

from qcal_qutip_backend.config.schema import DeviceProfile, MeasurementChainConfig


def without_measurement_noise(profile: DeviceProfile) -> DeviceProfile:
    return replace(
        profile,
        measurement_chain=replace(profile.measurement_chain, amplifier_noise=0.0, adc_noise=0.0),
    )


def ideal_output_profile(profile: DeviceProfile) -> DeviceProfile:
    return replace(
        profile,
        measurement_chain=MeasurementChainConfig(
            output_field=profile.measurement_chain.output_field,
            gain=1.0,
            iq_rotation_rad=0.0,
            i_offset=0.0,
            q_offset=0.0,
            amplifier_noise=0.0,
            adc_noise=0.0,
            adc_clip=0.0,
        ),
    )
