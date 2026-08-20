from __future__ import annotations

import json
from pathlib import Path

from qcal_qutip_backend.config.schema import (
    ControlChainConfig,
    CouplingsConfig,
    DeviceProfile,
    DriftConfig,
    FaultsConfig,
    MeasurementChainConfig,
    QuantumSystemConfig,
    QubitConfig,
    QubitFrequencyDriftConfig,
    ReadoutCavityConfig,
    ReadoutFrequencyDriftConfig,
    StorageCavityConfig,
)


def _section(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object.")
    return value


def load_device_profile(path: str | Path) -> DeviceProfile:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    quantum = _section(payload, "quantum_system")
    drift = _section(payload, "drift")
    profile = DeviceProfile(
        schema_version=int(payload.get("schema_version", 1)),
        device_id=str(payload["device_id"]),
        seed=int(payload["seed"]),
        quantum_system=QuantumSystemConfig(
            qubit=QubitConfig(**_section(quantum, "qubit")),
            readout_cavity=ReadoutCavityConfig(**_section(quantum, "readout_cavity")),
            storage_cavity=StorageCavityConfig(**_section(quantum, "storage_cavity")),
            couplings=CouplingsConfig(**_section(quantum, "couplings")),
        ),
        control_chain=ControlChainConfig(**_section(payload, "control_chain")),
        measurement_chain=MeasurementChainConfig(**_section(payload, "measurement_chain")),
        drift=DriftConfig(
            qubit_frequency=QubitFrequencyDriftConfig(**_section(drift, "qubit_frequency")),
            readout_frequency=ReadoutFrequencyDriftConfig(**_section(drift, "readout_frequency")),
        ),
        faults=FaultsConfig(**_section(payload, "faults")),
    )
    profile.validate()
    return profile
