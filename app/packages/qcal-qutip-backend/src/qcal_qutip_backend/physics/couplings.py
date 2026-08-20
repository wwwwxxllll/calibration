from qcal_qutip_backend.config.schema import CouplingsConfig, QubitConfig, ReadoutCavityConfig


def dispersive_shift_hz(
    cavity: ReadoutCavityConfig,
    qubit: QubitConfig,
    couplings: CouplingsConfig,
) -> float:
    detuning_hz = qubit.frequency_hz - cavity.frequency_hz
    if detuning_hz == 0.0:
        raise ValueError("Qubit and readout cavity cannot have zero detuning.")
    alpha_hz = qubit.anharmonicity_hz
    if abs(alpha_hz) < 1.0:
        # 无非简谐度时退化到二能级近似 χ = g²/Δ
        return couplings.qubit_readout_g_hz**2 / detuning_hz
    # transmon 三能级色散频移：χ = g²α / (Δ(Δ + α))
    return (
        couplings.qubit_readout_g_hz**2 * alpha_hz
        / (detuning_hz * (detuning_hz + alpha_hz))
    )