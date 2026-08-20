from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np


class ExperimentType(StrEnum):
    READOUT_SPECTROSCOPY = "readout_spectroscopy"
    QUBIT_SPECTROSCOPY = "qubit_spectroscopy"
    POWER_RABI = "power_rabi"
    READOUT_SPECTROSCOPY_E = "readout_spectroscopy_e"
    QUBIT_T1 = "qubit_t1"
    RAMSEY = "ramsey"
    ECHO = "echo"
    SINGLE_SHOT_HISTOGRAM = "single_shot_histogram"


@dataclass(slots=True)
class SweepReadoutPlan:
    """Step1 实验语义；字段与 MATLAB/Agent 参数直接对应。"""

    ReadoutStartFreq1: float
    ReadoutStopFreq1: float
    Readoutstep1: float
    readout_amp: float
    roundRobin: int
    measuretime: float
    waittime: float
    expected_cycle_length: float
    experiment_type: ExperimentType = field(
        default=ExperimentType.READOUT_SPECTROSCOPY,
        init=False,
    )


@dataclass(slots=True)
class SweepQubitPlan:
    """Step2 实验语义；ReadoutFreq 由 Env 从已确认标定结果补入。"""

    QubitStartFreq1: float
    QubitStopFreq1: float
    Qubitstep1: float
    amp180: float
    mysigma: float
    coeff: float
    ReadoutFreq: float
    readout_amp: float
    roundRobin: int
    measuretime: float
    waittime: float
    expected_cycle_length: float
    experiment_type: ExperimentType = field(
        default=ExperimentType.QUBIT_SPECTROSCOPY,
        init=False,
    )


@dataclass(slots=True)
class PowerRabiPlan:
    """Step3 实验语义；QubitFreq 由 Env 从已确认标定结果补入。"""

    numstep: int
    RabiStep: float
    QubitFreq: float
    ReadoutFreq: float
    mysigma: float
    coeff: float
    readout_amp: float
    roundRobin: int
    measuretime: float
    waittime: float
    expected_cycle_length: float
    experiment_type: ExperimentType = field(
        default=ExperimentType.POWER_RABI,
        init=False,
    )


@dataclass(slots=True)
class SweepReadoutEPlan:
    """Step4 实验语义；用已确认 pi pulse 先制备 e 态，再扫读取腔频率。"""

    ReadoutStartFreq1: float
    ReadoutStopFreq1: float
    Readoutstep1: float
    QubitFreq: float
    amp180: float
    mysigma: float
    coeff: float
    readout_amp: float
    roundRobin: int
    measuretime: float
    waittime: float
    expected_cycle_length: float
    experiment_type: ExperimentType = field(
        default=ExperimentType.READOUT_SPECTROSCOPY_E,
        init=False,
    )


@dataclass(slots=True)
class QubitT1Plan:
    """Step5 实验语义；numstep 和 timeStep 生成 T1 等待时间列表。"""

    numstep: int
    timeStep: float
    QubitFreq: float
    amp180: float
    mysigma: float
    coeff: float
    ReadoutFreq: float
    readout_amp: float
    roundRobin: int
    measuretime: float
    waittime: float
    expected_cycle_length: float
    experiment_type: ExperimentType = field(
        default=ExperimentType.QUBIT_T1,
        init=False,
    )


@dataclass(slots=True)
class RamseyPlan:
    """Step6.1 实验语义；numstep 和 timeStep 生成 Ramsey 延迟与相位列表。"""

    numstep: int
    timeStep: float
    QubitFreq: float
    amp180: float
    mysigma: float
    coeff: float
    ReadoutFreq: float
    readout_amp: float
    roundRobin: int
    measuretime: float
    expected_cycle_length: float
    experiment_type: ExperimentType = field(
        default=ExperimentType.RAMSEY,
        init=False,
    )


@dataclass(slots=True)
class EchoPlan:
    """Step6.2 实验语义；π/2 - π - π/2 pulse，扫描 Echo 延迟。"""

    numstep: int
    timeStep: float
    QubitFreq: float
    amp180: float
    mysigma: float
    coeff: float
    ReadoutFreq: float
    readout_amp: float
    roundRobin: int
    measuretime: float
    expected_cycle_length: float
    experiment_type: ExperimentType = field(
        default=ExperimentType.ECHO,
        init=False,
    )


@dataclass(slots=True)
class SingleShotHistogramPlan:
    """Step7 实验语义；分别制备 g/e 态并保存 I/Q 散点。"""

    roundRobin: int
    bin: int
    QubitFreq: float
    amp180: float
    mysigma: float
    coeff: float
    ReadoutFreq: float
    readout_amp: float
    measuretime: float
    expected_cycle_length: float
    experiment_type: ExperimentType = field(
        default=ExperimentType.SINGLE_SHOT_HISTOGRAM,
        init=False,
    )


ExperimentPlan = (
    SweepReadoutPlan
    | SweepQubitPlan
    | PowerRabiPlan
    | SweepReadoutEPlan
    | QubitT1Plan
    | RamseyPlan
    | EchoPlan
    | SingleShotHistogramPlan
)


@dataclass(slots=True)
class RawResult:
    """QuTiP/Hardware 返回给 Env 的简单原始观测结果。"""

    experiment_type: ExperimentType
    sweep_name: str
    sweep_values: np.ndarray
    i_values: np.ndarray
    q_values: np.ndarray
    point_status: list[str]
    metadata: dict[str, object] = field(default_factory=dict)

    @property
    def amplitudes(self) -> np.ndarray:
        return np.abs(self.i_values + 1j * self.q_values)
