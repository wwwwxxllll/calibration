"""Reserved boundary for shot-level sampling, kept from feature_adapter_1."""

from typing import Protocol

import numpy as np


class ShotSampler(Protocol):
    def sample(self, mean_iq: complex, shots: int, rng: np.random.Generator) -> np.ndarray: ...


def gaussian_iq_shots(
    center: complex,
    *,
    shots: int,
    noise_std: float,
    rng: np.random.Generator,
) -> np.ndarray:
    if shots <= 0:
        raise ValueError("shots 必须大于 0。")
    if noise_std < 0.0:
        raise ValueError("noise_std 不能为负数。")
    i_values = rng.normal(center.real, noise_std, shots)
    q_values = rng.normal(center.imag, noise_std, shots)
    return i_values + 1j * q_values


def discrimination_axis(ground_center: complex, excited_center: complex) -> complex:
    vector = excited_center - ground_center
    if abs(vector) == 0.0:
        raise ValueError("g/e 两个 single-shot 中心重合，无法判别。")
    return vector / abs(vector)


def project_onto_axis(values: np.ndarray, origin: complex, axis: complex) -> np.ndarray:
    return np.real((values - origin) * np.conjugate(axis))


def best_threshold(ground_projection: np.ndarray, excited_projection: np.ndarray) -> tuple[float, float]:
    ground_projection = np.asarray(ground_projection, dtype=float)
    excited_projection = np.asarray(excited_projection, dtype=float)
    candidates = np.linspace(float(np.min(ground_projection)), float(np.max(excited_projection)), 1000)
    best_fidelity = -1.0
    best_cut = float(candidates[0])
    for threshold in candidates:
        p_ground_correct = np.mean(ground_projection < threshold)
        p_excited_correct = np.mean(excited_projection >= threshold)
        fidelity = 0.5 * (p_ground_correct + p_excited_correct)
        if fidelity > best_fidelity:
            best_fidelity = float(fidelity)
            best_cut = float(threshold)
    return best_cut, best_fidelity
