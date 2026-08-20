"""Reserved Hardware Adapter position; no hardware control is implemented yet."""

from qcal_contracts import ExperimentPlan, RawResult


class HardwareAdapter:
    def execute(self, plan: ExperimentPlan) -> RawResult:
        del plan
        raise NotImplementedError("Hardware Adapter 尚未实现。")
