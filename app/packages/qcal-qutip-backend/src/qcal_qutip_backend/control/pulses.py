from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReadoutPulse:
    frequency_hz: float
    amplitude_sqrt_hz: float
    duration_s: float


@dataclass(frozen=True, slots=True)
class QubitDrive:
    frequency_hz: float
    amplitude: float = 0.0
    gaussian_sigma_s: float = 0.0
    duration_s: float = 0.0
