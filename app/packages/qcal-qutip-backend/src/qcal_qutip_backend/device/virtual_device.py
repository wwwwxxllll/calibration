from __future__ import annotations

from dataclasses import replace

import numpy as np

from qcal_qutip_backend.config.schema import DeviceProfile
from qcal_contracts import ExperimentType
from qcal_qutip_backend.control.sequences import CompiledExperiment, CompiledPoint
from qcal_qutip_backend.device.results import InternalExecutionResult, InternalPointResult
from qcal_qutip_backend.measurement.input_output import InputOutputFields, map_input_output
from qcal_qutip_backend.measurement.iq_chain import IQChain, IQObservation
from qcal_qutip_backend.measurement.shot_sampler import gaussian_iq_shots
from qcal_qutip_backend.physics.couplings import dispersive_shift_hz
from qcal_qutip_backend.physics.qubit_response import FastQubitResponseModel
from qcal_qutip_backend.physics.readout_cavity import CavityState, QuTiPSteadyStateCavitySolver
from qcal_qutip_backend.scenarios.clock import VirtualClock
from qcal_qutip_backend.scenarios.drift import NoDrift, ProfileDrift
from qcal_qutip_backend.scenarios.faults import NoFaults, ProbabilisticFaults


class VirtualQuantumDevice:
    """Stateful simulator that knows no Agent tools, stores or fitting code."""

    def __init__(
        self,
        profile: DeviceProfile,
        *,
        clock: VirtualClock | None = None,
        drift: NoDrift | ProfileDrift | None = None,
        faults: NoFaults | ProbabilisticFaults | None = None,
    ) -> None:
        profile.validate()
        self._profile = profile
        self.clock = clock or VirtualClock()
        self.drift = drift or ProfileDrift(profile.drift, profile.seed)
        self.faults = faults or ProbabilisticFaults(profile.faults, profile.seed)
        self.cavity_solver = QuTiPSteadyStateCavitySolver(profile.quantum_system.readout_cavity)
        self.qubit_model = FastQubitResponseModel()
        self.iq_chain = IQChain(profile.measurement_chain)
        self.run_count = 0

    @property
    def profile(self) -> DeviceProfile:
        return self._profile

    @property
    def device_id(self) -> str:
        return self._profile.device_id

    @property
    def fidelity(self) -> str:
        return "fast_steady_state"

    def execute_sequence(
        self,
        experiment: CompiledExperiment,
    ) -> InternalExecutionResult:
        rng = np.random.default_rng(self._profile.seed + self.run_count)
        points = tuple(
            self._execute_point(experiment, point, point_index=index, rng=rng)
            for index, point in enumerate(experiment.points)
        )
        run_index = self.run_count
        self.run_count += 1
        elapsed = len(points) * experiment.repetitions * experiment.cycle_period_s
        self.clock.advance(elapsed)
        return InternalExecutionResult(experiment.experiment_type, experiment.sweep_name, points, run_index)

    def _execute_point(
        self,
        experiment: CompiledExperiment,
        point: CompiledPoint,
        *,
        point_index: int,
        rng: np.random.Generator,
    ) -> InternalPointResult:
        status = self.faults.point_status(point_index)
        if status != "ok":
            return self._missing_point(point, status)

        if experiment.experiment_type in {
            ExperimentType.POWER_RABI,
            ExperimentType.QUBIT_T1,
            ExperimentType.RAMSEY,
            ExperimentType.ECHO,
            ExperimentType.SINGLE_SHOT_HISTOGRAM,
        }:
            return self._execute_prepared_qubit_point(experiment, point, point_index=point_index, rng=rng)

        elapsed_s = self.clock.elapsed_s
        cavity = replace(
            self._profile.quantum_system.readout_cavity,
            frequency_hz=self._profile.quantum_system.readout_cavity.frequency_hz
            + self.drift.frequency_offset_hz("readout_frequency_hz", elapsed_s),
        )
        qubit = replace(
            self._profile.quantum_system.qubit,
            frequency_hz=self._profile.quantum_system.qubit.frequency_hz
            + self.drift.frequency_offset_hz("qubit_frequency_hz", elapsed_s),
        )
        chi_hz = dispersive_shift_hz(cavity, qubit, self._profile.quantum_system.couplings)
        pe = 0.0
        if point.qubit_drive.amplitude > 0.0:
            pe = self.qubit_model.excited_probability(
                qubit,
                point.qubit_drive,
                control=self._profile.control_chain,
            )
        fr_g_hz = cavity.frequency_hz - chi_hz
        fr_e_hz = cavity.frequency_hz + chi_hz
        state_g = self.cavity_solver.solve(point.readout_pulse, effective_cavity_frequency_hz=fr_g_hz)
        state_e = self.cavity_solver.solve(point.readout_pulse, effective_cavity_frequency_hz=fr_e_hz)
        fields_g = map_input_output(
            cavity,
            point.readout_pulse,
            state_g.intracavity_alpha,
            output_field=self._profile.measurement_chain.output_field,
        )
        fields_e = map_input_output(
            cavity,
            point.readout_pulse,
            state_e.intracavity_alpha,
            output_field=self._profile.measurement_chain.output_field,
        )
        mixed_state = self._mix_states(state_g, state_e, pe)
        mixed_fields = self._mix_fields(fields_g, fields_e, pe)
        observation = self.iq_chain.observe(
            mixed_fields.selected_output_field,
            adc_full_scale=point.readout_pulse.amplitude_sqrt_hz,
            output_scale=self._profile.control_chain.readout_sqrt_hz_per_dac_code,
            repetitions=experiment.repetitions,
            rng=rng,
        )
        return InternalPointResult(
            sweep_value=point.sweep_value,
            status="ok",
            observation=observation,
            excited_probability=pe,
            dispersive_chi_hz=chi_hz,
            effective_cavity_frequency_hz=(1.0 - pe) * fr_g_hz + pe * fr_e_hz,
            mean_photon_number=mixed_state.mean_photon_number,
            density_matrix=mixed_state.density_matrix,
        )

    def _execute_prepared_qubit_point(
        self,
        experiment: CompiledExperiment,
        point: CompiledPoint,
        *,
        point_index: int,
        rng: np.random.Generator,
    ) -> InternalPointResult:
        elapsed_s = self.clock.elapsed_s
        cavity = replace(
            self._profile.quantum_system.readout_cavity,
            frequency_hz=self._profile.quantum_system.readout_cavity.frequency_hz
            + self.drift.frequency_offset_hz("readout_frequency_hz", elapsed_s),
        )
        qubit = replace(
            self._profile.quantum_system.qubit,
            frequency_hz=self._profile.quantum_system.qubit.frequency_hz
            + self.drift.frequency_offset_hz("qubit_frequency_hz", elapsed_s),
        )
        chi_hz = dispersive_shift_hz(cavity, qubit, self._profile.quantum_system.couplings)
        pe = self._prepared_excited_probability(experiment, point, qubit)
        fr_g_hz = cavity.frequency_hz - chi_hz
        fr_e_hz = cavity.frequency_hz + chi_hz
        state_g = self.cavity_solver.solve(point.readout_pulse, effective_cavity_frequency_hz=fr_g_hz)
        state_e = self.cavity_solver.solve(point.readout_pulse, effective_cavity_frequency_hz=fr_e_hz)
        fields_g = map_input_output(
            cavity,
            point.readout_pulse,
            state_g.intracavity_alpha,
            output_field=self._profile.measurement_chain.output_field,
        )
        fields_e = map_input_output(
            cavity,
            point.readout_pulse,
            state_e.intracavity_alpha,
            output_field=self._profile.measurement_chain.output_field,
        )
        if experiment.experiment_type == ExperimentType.SINGLE_SHOT_HISTOGRAM:
            shot_count = int((experiment.metadata or {}).get("shot_count", 0))
            state_probability = 0.0 if point_index < shot_count else 1.0
            field = fields_g.selected_output_field if state_probability == 0.0 else fields_e.selected_output_field
            center_observation = self.iq_chain.observe(
                field,
                adc_full_scale=point.readout_pulse.amplitude_sqrt_hz,
                output_scale=self._profile.control_chain.readout_sqrt_hz_per_dac_code,
                repetitions=1,
                rng=rng,
            )
            separation = abs(fields_e.selected_output_field - fields_g.selected_output_field) / max(
                self._profile.control_chain.readout_sqrt_hz_per_dac_code,
                np.finfo(float).eps,
            )
            noise_std = max(0.18 * separation, 5.0)
            shot = gaussian_iq_shots(
                complex(center_observation.i_value, center_observation.q_value),
                shots=1,
                noise_std=noise_std,
                rng=rng,
            )[0]
            observation = IQObservation(float(np.real(shot)), float(np.imag(shot)))
            pe = state_probability
        else:
            mixed_state = self._mix_states(state_g, state_e, pe)
            mixed_fields = self._mix_fields(fields_g, fields_e, pe)
            observation = self.iq_chain.observe(
                mixed_fields.selected_output_field,
                adc_full_scale=point.readout_pulse.amplitude_sqrt_hz,
                output_scale=self._profile.control_chain.readout_sqrt_hz_per_dac_code,
                repetitions=experiment.repetitions,
                rng=rng,
            )
            return InternalPointResult(
                sweep_value=point.sweep_value,
                status="ok",
                observation=observation,
                excited_probability=pe,
                dispersive_chi_hz=chi_hz,
                effective_cavity_frequency_hz=(1.0 - pe) * fr_g_hz + pe * fr_e_hz,
                mean_photon_number=mixed_state.mean_photon_number,
                density_matrix=mixed_state.density_matrix,
            )
        selected_state = state_g if pe == 0.0 else state_e
        return InternalPointResult(
            sweep_value=point.sweep_value,
            status="ok",
            observation=observation,
            excited_probability=pe,
            dispersive_chi_hz=chi_hz,
            effective_cavity_frequency_hz=(1.0 - pe) * fr_g_hz + pe * fr_e_hz,
            mean_photon_number=selected_state.mean_photon_number,
            density_matrix=selected_state.density_matrix,
        )

    def _prepared_excited_probability(
        self,
        experiment: CompiledExperiment,
        point: CompiledPoint,
        qubit,
    ) -> float:
        thermal = qubit.thermal_excited_population
        if experiment.experiment_type == ExperimentType.POWER_RABI:
            detuning_hz = point.qubit_drive.frequency_hz - qubit.frequency_hz
            half_width_hz = 0.5 * qubit.linewidth_hz
            spectral = half_width_hz**2 / (detuning_hz**2 + half_width_hz**2)
            rabi = np.sin(0.5 * np.pi * point.qubit_drive.amplitude / qubit.pi_amplitude) ** 2
            return float(np.clip(thermal + (1.0 - thermal) * spectral * rabi, 0.0, 1.0))
        if experiment.experiment_type == ExperimentType.QUBIT_T1:
            wait_s = point.sweep_value
            return float(np.clip(thermal + (1.0 - thermal) * np.exp(-wait_s / qubit.t1_s), 0.0, 1.0))
        if experiment.experiment_type == ExperimentType.RAMSEY:
            wait_s = point.sweep_value
            point_metadata = point.metadata or {}
            ramsey_phase_rad = np.deg2rad(float(point_metadata.get("ramsey_angle_deg", 0.0)))
            detuning_hz = point.qubit_drive.frequency_hz - qubit.frequency_hz
            decay_time_s = qubit.pure_dephasing_time_s
            contrast = np.exp(-wait_s / decay_time_s)
            oscillation = 0.5 * (1.0 + np.cos(2.0 * np.pi * detuning_hz * wait_s + ramsey_phase_rad))
            return float(np.clip(thermal + (1.0 - thermal) * contrast * oscillation, 0.0, 1.0))
        if experiment.experiment_type == ExperimentType.ECHO:
            wait_s = point.sweep_value
            point_metadata = point.metadata or {}
            ramsey_phase_rad = np.deg2rad(float(point_metadata.get("ramsey_angle_deg", 0.0)))
            detuning_hz = point.qubit_drive.frequency_hz - qubit.frequency_hz
            # The Hahn echo's π pulse refocuses (quasi-static) dephasing, so the
            # decay is limited by energy relaxation (2*T1) rather than pure
            # dephasing. This keeps T2_echo >= T2* (Ramsey), as PPT Slide 9 requires.
            decay_time_s = max(2.0 * qubit.t1_s, qubit.pure_dephasing_time_s)
            contrast = np.exp(-wait_s / decay_time_s)
            oscillation = 0.5 * (1.0 + np.cos(2.0 * np.pi * detuning_hz * wait_s + ramsey_phase_rad))
            return float(np.clip(thermal + (1.0 - thermal) * contrast * oscillation, 0.0, 1.0))
        return thermal

    @staticmethod
    def _missing_point(point: CompiledPoint, status: str) -> InternalPointResult:
        return InternalPointResult(
            sweep_value=point.sweep_value,
            status=status,
            observation=IQObservation(np.nan, np.nan),
            excited_probability=np.nan,
            dispersive_chi_hz=np.nan,
            effective_cavity_frequency_hz=np.nan,
            mean_photon_number=np.nan,
            density_matrix=None,
        )

    @staticmethod
    def _mix_states(ground: CavityState, excited: CavityState, pe: float) -> CavityState:
        pg = 1.0 - pe
        return CavityState(
            intracavity_alpha=pg * ground.intracavity_alpha + pe * excited.intracavity_alpha,
            mean_photon_number=pg * ground.mean_photon_number + pe * excited.mean_photon_number,
            density_matrix=pg * ground.density_matrix + pe * excited.density_matrix,
        )

    @staticmethod
    def _mix_fields(ground: InputOutputFields, excited: InputOutputFields, pe: float) -> InputOutputFields:
        pg = 1.0 - pe
        transmitted = None
        if ground.transmitted_field is not None and excited.transmitted_field is not None:
            transmitted = pg * ground.transmitted_field + pe * excited.transmitted_field
        return InputOutputFields(
            input_field=ground.input_field,
            reflected_field=pg * ground.reflected_field + pe * excited.reflected_field,
            transmitted_field=transmitted,
            selected_output_field=pg * ground.selected_output_field + pe * excited.selected_output_field,
        )
