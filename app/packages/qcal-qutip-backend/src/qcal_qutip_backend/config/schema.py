"""Private, versioned virtual-device configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class QubitConfig:
    frequency_hz: float = 5.076e9
    anharmonicity_hz: float = -220.0e6
    levels: int = 3
    t1_s: float = 45.0e-6
    pure_dephasing_time_s: float = 80.0e-6
    thermal_excited_population: float = 0.025
    linewidth_hz: float = 5.0e6
    pi_amplitude: float = 1.0

    def validate(self) -> None:
        if self.levels < 2:
            raise ValueError("quantum_system.qubit.levels must be at least 2.")
        if min(self.t1_s, self.pure_dephasing_time_s, self.linewidth_hz, self.pi_amplitude) <= 0.0:
            raise ValueError("Qubit lifetime, linewidth and pi amplitude must be positive.")
        if not 0.0 <= self.thermal_excited_population <= 1.0:
            raise ValueError("thermal_excited_population must be in [0, 1].")


@dataclass(frozen=True, slots=True)
class ReadoutCavityConfig:
    frequency_hz: float = 7.556e9
    hilbert_dim: int = 20
    kappa_external_hz: float = 1.8e6
    kappa_internal_hz: float = 0.3e6

    @property
    def total_kappa_hz(self) -> float:
        return self.kappa_external_hz + self.kappa_internal_hz

    def validate(self) -> None:
        if self.hilbert_dim < 4 or min(self.kappa_external_hz, self.kappa_internal_hz) < 0.0:
            raise ValueError("Invalid readout cavity dimension or loss rate.")
        if self.total_kappa_hz <= 0.0:
            raise ValueError("Total readout loss must be positive.")


@dataclass(frozen=True, slots=True)
class StorageCavityConfig:
    enabled: bool = False
    frequency_hz: float = 4.2e9
    hilbert_dim: int = 15
    lifetime_s: float = 1.2e-3

    def validate(self) -> None:
        if self.hilbert_dim < 2 or self.lifetime_s <= 0.0:
            raise ValueError("Invalid storage cavity configuration.")


@dataclass(frozen=True, slots=True)
class CouplingsConfig:
    qubit_readout_g_hz: float = 85.0e6
    qubit_storage_g_hz: float = 12.0e6

    def validate(self) -> None:
        if self.qubit_readout_g_hz <= 0.0 or self.qubit_storage_g_hz < 0.0:
            raise ValueError("Invalid coupling rate.")


@dataclass(frozen=True, slots=True)
class QuantumSystemConfig:
    qubit: QubitConfig = field(default_factory=QubitConfig)
    readout_cavity: ReadoutCavityConfig = field(default_factory=ReadoutCavityConfig)
    storage_cavity: StorageCavityConfig = field(default_factory=StorageCavityConfig)
    couplings: CouplingsConfig = field(default_factory=CouplingsConfig)

    def validate(self) -> None:
        self.qubit.validate()
        self.readout_cavity.validate()
        self.storage_cavity.validate()
        self.couplings.validate()


@dataclass(frozen=True, slots=True)
class ControlChainConfig:
    qubit_amplitude_scale: float = 1.0e6
    gaussian_bandwidth_hz: float = 150.0e6
    readout_sqrt_hz_per_dac_code: float = 2.5
    qubit_pi_dac_code: float = 700.0

    def validate(self) -> None:
        positive = (
            self.qubit_amplitude_scale,
            self.gaussian_bandwidth_hz,
            self.readout_sqrt_hz_per_dac_code,
            self.qubit_pi_dac_code,
        )
        if min(positive) <= 0.0:
            raise ValueError("Invalid control-chain scale.")


@dataclass(frozen=True, slots=True)
class MeasurementChainConfig:
    output_field: str = "transmission"
    gain: float = 1.2
    iq_rotation_rad: float = 0.25
    i_offset: float = 0.04
    q_offset: float = -0.02
    amplifier_noise: float = 0.08
    adc_noise: float = 0.015
    adc_clip: float = 1.0

    def validate(self) -> None:
        if self.output_field not in {"transmission", "reflection"}:
            raise ValueError("measurement_chain.output_field must be 'transmission' or 'reflection'.")
        if min(self.amplifier_noise, self.adc_noise, self.adc_clip) < 0.0:
            raise ValueError("Measurement noise and clipping must be non-negative.")


@dataclass(frozen=True, slots=True)
class QubitFrequencyDriftConfig:
    model: str = "random_walk"
    sigma_hz_per_sqrt_s: float = 1500.0

    def validate(self) -> None:
        if self.model not in {"none", "random_walk"} or self.sigma_hz_per_sqrt_s < 0.0:
            raise ValueError("Invalid qubit drift configuration.")


@dataclass(frozen=True, slots=True)
class ReadoutFrequencyDriftConfig:
    model: str = "slow_sinusoid"
    amplitude_hz: float = 80000.0
    period_s: float = 3600.0

    def validate(self) -> None:
        if self.model not in {"none", "slow_sinusoid"}:
            raise ValueError("Invalid readout drift model.")
        if self.amplitude_hz < 0.0 or self.period_s <= 0.0:
            raise ValueError("Invalid readout drift scale.")


@dataclass(frozen=True, slots=True)
class DriftConfig:
    qubit_frequency: QubitFrequencyDriftConfig = field(default_factory=QubitFrequencyDriftConfig)
    readout_frequency: ReadoutFrequencyDriftConfig = field(default_factory=ReadoutFrequencyDriftConfig)

    def validate(self) -> None:
        self.qubit_frequency.validate()
        self.readout_frequency.validate()


@dataclass(frozen=True, slots=True)
class FaultsConfig:
    missing_point_probability: float = 0.001
    timeout_probability: float = 0.0005

    def validate(self) -> None:
        if not 0.0 <= self.missing_point_probability <= 1.0:
            raise ValueError("missing_point_probability must be in [0, 1].")
        if not 0.0 <= self.timeout_probability <= 1.0:
            raise ValueError("timeout_probability must be in [0, 1].")


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    schema_version: int = 1
    device_id: str = "virtual_device_A"
    seed: int = 20260810
    quantum_system: QuantumSystemConfig = field(default_factory=QuantumSystemConfig)
    control_chain: ControlChainConfig = field(default_factory=ControlChainConfig)
    measurement_chain: MeasurementChainConfig = field(default_factory=MeasurementChainConfig)
    drift: DriftConfig = field(default_factory=DriftConfig)
    faults: FaultsConfig = field(default_factory=FaultsConfig)

    def validate(self) -> None:
        if self.schema_version != 1 or not self.device_id:
            raise ValueError("Unsupported profile schema or empty device_id.")
        self.quantum_system.validate()
        self.control_chain.validate()
        self.measurement_chain.validate()
        self.drift.validate()
        self.faults.validate()


def default_device_profile() -> DeviceProfile:
    profile = DeviceProfile()
    profile.validate()
    return profile
