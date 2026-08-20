from __future__ import annotations

from math import floor

import numpy as np

from qcal_contracts import (
    EchoPlan,
    ExperimentPlan,
    PowerRabiPlan,
    QubitT1Plan,
    RamseyPlan,
    SingleShotHistogramPlan,
    SweepQubitPlan,
    SweepReadoutEPlan,
    SweepReadoutPlan,
)
from qcal_qutip_backend.config.schema import ControlChainConfig
from qcal_qutip_backend.control.pulses import QubitDrive, ReadoutPulse
from qcal_qutip_backend.control.sequences import CompiledExperiment, CompiledPoint

# MATLAB step61_T2.m / step62_T2E.m ramp the Ramsey phase through
# `numcycles = (numstep - 1) / 8` full cycles across the sweep (10 cycles for
# the default 81 steps). The reference frequency the Env fit subtracts is
# derived from this same ramp rate.


class ExperimentCompiler:
    def __init__(self, control: ControlChainConfig, *, readout_ssb_hz: float = 50.0e6):
        self._control = control
        self._readout_ssb_hz = readout_ssb_hz

    def compile(self, plan: ExperimentPlan) -> CompiledExperiment:
        if isinstance(plan, SweepReadoutPlan):
            return self._readout(plan)
        if isinstance(plan, SweepQubitPlan):
            return self._qubit(plan)
        if isinstance(plan, PowerRabiPlan):
            return self._power_rabi(plan)
        if isinstance(plan, SweepReadoutEPlan):
            return self._readout_e(plan)
        if isinstance(plan, QubitT1Plan):
            return self._t1(plan)
        if isinstance(plan, RamseyPlan):
            return self._ramsey(plan)
        if isinstance(plan, EchoPlan):
            return self._echo(plan)
        if isinstance(plan, SingleShotHistogramPlan):
            return self._single_shot(plan)
        raise TypeError(f"Unsupported ExperimentPlan: {type(plan).__name__}")

    def _readout(self, plan: SweepReadoutPlan) -> CompiledExperiment:
        frequencies_hz = _inclusive_sweep(
            plan.ReadoutStartFreq1,
            plan.ReadoutStopFreq1,
            plan.Readoutstep1,
        ) - self._readout_ssb_hz
        amplitude = plan.readout_amp * self._control.readout_sqrt_hz_per_dac_code
        readout_duration_s = plan.measuretime * 1.0e-9
        points = tuple(
            CompiledPoint(
                sweep_value=float(frequency_hz),
                qubit_drive=QubitDrive(frequency_hz=0.0),
                readout_pulse=ReadoutPulse(
                    frequency_hz=float(frequency_hz),
                    amplitude_sqrt_hz=amplitude,
                    duration_s=readout_duration_s,
                ),
            )
            for frequency_hz in frequencies_hz
        )
        return CompiledExperiment(
            plan.experiment_type,
            "readout_frequency_hz",
            frequencies_hz,
            plan.roundRobin,
            plan.expected_cycle_length * 1.0e-9,
            points,
        )

    def _qubit(self, plan: SweepQubitPlan) -> CompiledExperiment:
        frequencies_hz = _inclusive_sweep(
            plan.QubitStartFreq1,
            plan.QubitStopFreq1,
            plan.Qubitstep1,
        )
        readout_amplitude = plan.readout_amp * self._control.readout_sqrt_hz_per_dac_code
        readout_duration_s = plan.measuretime * 1.0e-9
        # The fast model uses the profile's pi DAC code as amplitude scale.
        # coeff controls Gaussian duration in the MATLAB sequence, not this
        # normalized phenomenological drive strength.
        qubit_amplitude = plan.amp180 / self._control.qubit_pi_dac_code
        points = tuple(
            CompiledPoint(
                sweep_value=float(frequency_hz),
                qubit_drive=QubitDrive(
                    frequency_hz=float(frequency_hz),
                    amplitude=qubit_amplitude,
                    gaussian_sigma_s=plan.mysigma * 1.0e-9,
                    duration_s=4.0 * plan.mysigma * plan.coeff * 1.0e-9,
                ),
                readout_pulse=ReadoutPulse(
                    frequency_hz=plan.ReadoutFreq,
                    amplitude_sqrt_hz=readout_amplitude,
                    duration_s=readout_duration_s,
                ),
            )
            for frequency_hz in frequencies_hz
        )
        return CompiledExperiment(
            plan.experiment_type,
            "qubit_frequency_hz",
            frequencies_hz,
            plan.roundRobin,
            plan.expected_cycle_length * 1.0e-9,
            points,
        )

    def _power_rabi(self, plan: PowerRabiPlan) -> CompiledExperiment:
        amplitudes = np.arange(plan.numstep, dtype=float) * plan.RabiStep
        readout_amplitude = plan.readout_amp * self._control.readout_sqrt_hz_per_dac_code
        readout_duration_s = plan.measuretime * 1.0e-9
        points = tuple(
            CompiledPoint(
                sweep_value=float(amplitude),
                qubit_drive=QubitDrive(
                    frequency_hz=plan.QubitFreq,
                    amplitude=float(amplitude) / self._control.qubit_pi_dac_code,
                    gaussian_sigma_s=plan.mysigma * 1.0e-9,
                    duration_s=4.0 * plan.mysigma * plan.coeff * 1.0e-9,
                ),
                readout_pulse=ReadoutPulse(
                    frequency_hz=plan.ReadoutFreq,
                    amplitude_sqrt_hz=readout_amplitude,
                    duration_s=readout_duration_s,
                ),
            )
            for amplitude in amplitudes
        )
        return CompiledExperiment(
            plan.experiment_type,
            "qubit_drive_amplitude",
            amplitudes,
            plan.roundRobin,
            plan.expected_cycle_length * 1.0e-9,
            points,
            metadata={"qubit_frequency_hz": plan.QubitFreq},
        )

    def _readout_e(self, plan: SweepReadoutEPlan) -> CompiledExperiment:
        frequencies_hz = _inclusive_sweep(
            plan.ReadoutStartFreq1,
            plan.ReadoutStopFreq1,
            plan.Readoutstep1,
        ) - self._readout_ssb_hz
        readout_amplitude = plan.readout_amp * self._control.readout_sqrt_hz_per_dac_code
        readout_duration_s = plan.measuretime * 1.0e-9
        points = tuple(
            CompiledPoint(
                sweep_value=float(frequency_hz),
                qubit_drive=QubitDrive(
                    frequency_hz=plan.QubitFreq,
                    amplitude=plan.amp180 / self._control.qubit_pi_dac_code,
                    gaussian_sigma_s=plan.mysigma * 1.0e-9,
                    duration_s=4.0 * plan.mysigma * plan.coeff * 1.0e-9,
                ),
                readout_pulse=ReadoutPulse(
                    frequency_hz=float(frequency_hz),
                    amplitude_sqrt_hz=readout_amplitude,
                    duration_s=readout_duration_s,
                ),
            )
            for frequency_hz in frequencies_hz
        )
        return CompiledExperiment(
            plan.experiment_type,
            "readout_frequency_hz",
            frequencies_hz,
            plan.roundRobin,
            plan.expected_cycle_length * 1.0e-9,
            points,
        )

    def _t1(self, plan: QubitT1Plan) -> CompiledExperiment:
        waits_s = _indexed_delay_s(plan.numstep, plan.timeStep)
        readout_amplitude = plan.readout_amp * self._control.readout_sqrt_hz_per_dac_code
        readout_duration_s = plan.measuretime * 1.0e-9
        points = tuple(
            CompiledPoint(
                sweep_value=float(wait),
                qubit_drive=QubitDrive(
                    frequency_hz=plan.QubitFreq,
                    amplitude=plan.amp180 / self._control.qubit_pi_dac_code,
                    gaussian_sigma_s=plan.mysigma * 1.0e-9,
                    duration_s=4.0 * plan.mysigma * plan.coeff * 1.0e-9,
                ),
                readout_pulse=ReadoutPulse(
                    frequency_hz=plan.ReadoutFreq,
                    amplitude_sqrt_hz=readout_amplitude,
                    duration_s=readout_duration_s,
                ),
            )
            for wait in waits_s
        )
        return CompiledExperiment(
            plan.experiment_type,
            "waiting_time_s",
            waits_s,
            plan.roundRobin,
            plan.expected_cycle_length * 1.0e-9,
            points,
        )

    def _ramsey(self, plan: RamseyPlan) -> CompiledExperiment:
        waits_s = _indexed_delay_s(plan.numstep, plan.timeStep)
        ramsey_angles_deg = _ramsey_angles_deg(plan.numstep)
        readout_amplitude = plan.readout_amp * self._control.readout_sqrt_hz_per_dac_code
        readout_duration_s = plan.measuretime * 1.0e-9
        points = tuple(
            CompiledPoint(
                sweep_value=float(wait),
                qubit_drive=QubitDrive(
                    frequency_hz=plan.QubitFreq,
                    amplitude=0.5 * plan.amp180 / self._control.qubit_pi_dac_code,
                    gaussian_sigma_s=plan.mysigma * 1.0e-9,
                    duration_s=4.0 * plan.mysigma * plan.coeff * 1.0e-9,
                ),
                readout_pulse=ReadoutPulse(
                    frequency_hz=plan.ReadoutFreq,
                    amplitude_sqrt_hz=readout_amplitude,
                    duration_s=readout_duration_s,
                ),
                metadata={"ramsey_angle_deg": float(angle_deg)},
            )
            for wait, angle_deg in zip(waits_s, ramsey_angles_deg, strict=True)
        )
        return CompiledExperiment(
            plan.experiment_type,
            "waiting_time_s",
            waits_s,
            plan.roundRobin,
            plan.expected_cycle_length * 1.0e-9,
            points,
            metadata={
                "ramsey_angles_deg": ramsey_angles_deg.tolist(),
                "ramsey_angle_hz": _ramsey_reference_hz(plan.numstep, plan.timeStep),
                "sequence": "ramsey",
            },
        )

    def _echo(self, plan: EchoPlan) -> CompiledExperiment:
        waits_s = _indexed_delay_s(plan.numstep, plan.timeStep)
        ramsey_angles_deg = _ramsey_angles_deg(plan.numstep)
        readout_amplitude = plan.readout_amp * self._control.readout_sqrt_hz_per_dac_code
        readout_duration_s = plan.measuretime * 1.0e-9
        points = tuple(
            CompiledPoint(
                sweep_value=float(wait),
                qubit_drive=QubitDrive(
                    frequency_hz=plan.QubitFreq,
                    amplitude=0.5 * plan.amp180 / self._control.qubit_pi_dac_code,
                    gaussian_sigma_s=plan.mysigma * 1.0e-9,
                    duration_s=4.0 * plan.mysigma * plan.coeff * 1.0e-9,
                ),
                readout_pulse=ReadoutPulse(
                    frequency_hz=plan.ReadoutFreq,
                    amplitude_sqrt_hz=readout_amplitude,
                    duration_s=readout_duration_s,
                ),
                metadata={"ramsey_angle_deg": float(angle_deg)},
            )
            for wait, angle_deg in zip(waits_s, ramsey_angles_deg, strict=True)
        )
        return CompiledExperiment(
            plan.experiment_type,
            "echo_delay_s",
            waits_s,
            plan.roundRobin,
            plan.expected_cycle_length * 1.0e-9,
            points,
            metadata={
                "sequence": "echo",
                "echo_angle_hz": _ramsey_reference_hz(plan.numstep, plan.timeStep),
            },
        )

    def _single_shot(self, plan: SingleShotHistogramPlan) -> CompiledExperiment:
        shot_indices = np.arange(plan.roundRobin * 2, dtype=float)
        readout_amplitude = plan.readout_amp * self._control.readout_sqrt_hz_per_dac_code
        readout_duration_s = plan.measuretime * 1.0e-9
        points = tuple(
            CompiledPoint(
                sweep_value=float(index),
                qubit_drive=QubitDrive(
                    frequency_hz=plan.QubitFreq,
                    amplitude=0.0 if index < plan.roundRobin else plan.amp180 / self._control.qubit_pi_dac_code,
                    gaussian_sigma_s=plan.mysigma * 1.0e-9,
                    duration_s=4.0 * plan.mysigma * plan.coeff * 1.0e-9,
                ),
                readout_pulse=ReadoutPulse(
                    frequency_hz=plan.ReadoutFreq,
                    amplitude_sqrt_hz=readout_amplitude,
                    duration_s=readout_duration_s,
                ),
            )
            for index in shot_indices
        )
        return CompiledExperiment(
            plan.experiment_type,
            "shot_index",
            shot_indices,
            1,
            plan.expected_cycle_length * 1.0e-9,
            points,
            metadata={
                "shot_count": plan.roundRobin,
                "histogram_bins": plan.bin,
                "measuretime": plan.measuretime,
                "readout_amp": plan.readout_amp,
            },
        )


def _inclusive_sweep(start: float, stop: float, step: float) -> np.ndarray:
    count = floor((stop - start) / step + 1.0e-9) + 1
    return start + step * np.arange(count, dtype=float)


def _indexed_delay_s(numstep: int, time_step_ns: float) -> np.ndarray:
    return np.arange(numstep, dtype=float) * time_step_ns * 1.0e-9


def _ramsey_num_cycles(numstep: int) -> float:
    return (numstep - 1) / 8.0


def _ramsey_angles_deg(numstep: int) -> np.ndarray:
    return np.arange(numstep, dtype=float) * _ramsey_num_cycles(numstep) * 360.0 / numstep


def _ramsey_reference_hz(numstep: int, time_step_ns: float) -> float:
    return _ramsey_num_cycles(numstep) / (float(numstep) * float(time_step_ns) * 1.0e-9)
