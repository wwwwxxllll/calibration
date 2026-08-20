from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from qcal_qutip_backend.config.schema import FaultsConfig


@dataclass(frozen=True, slots=True)
class NoFaults:
    def point_status(self, point_index: int) -> str:
        del point_index
        return "ok"


@dataclass(slots=True)
class ProbabilisticFaults:
    params: FaultsConfig
    seed: int

    def point_status(self, point_index: int) -> str:
        if self._event(point_index, self.params.timeout_probability, salt=211):
            return "timeout"
        if self._event(point_index, self.params.missing_point_probability, salt=101):
            return "missing"
        return "ok"

    def _event(self, point_index: int, probability: float, *, salt: int) -> bool:
        if probability <= 0.0:
            return False
        rng = np.random.default_rng(self.seed + salt + int(point_index))
        return bool(rng.random() < probability)
