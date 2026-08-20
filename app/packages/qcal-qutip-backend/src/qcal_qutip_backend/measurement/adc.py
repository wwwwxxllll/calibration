"""Reserved boundary for future integration windows, quantization and clipping."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AcquisitionConfig:
    shots: int = 1
    integration_time_s: float = 2.0e-6
