"""A direct, readable Step1-Step7 Env runtime."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, Protocol

import numpy as np

from qcal_contracts import (
    EchoPlan,
    ExperimentPlan,
    ExperimentType,
    PowerRabiPlan,
    QubitT1Plan,
    RamseyPlan,
    RawResult,
    SingleShotHistogramPlan,
    SweepQubitPlan,
    SweepReadoutEPlan,
    SweepReadoutPlan,
)
from qcal_env.analysis import (
    analyze_single_shot,
    estimate_iq_rotation_angle,
    fit_lorentzian,
    fit_power_rabi,
    fit_ramsey,
    fit_t1,
    PLOT_AXES_BY_EXPERIMENT,
    rotate_iq,
    save_fit_plot,
    save_power_rabi_plot,
    save_raw_csv,
    save_single_shot_plot,
    save_xy_fit_plot,
)
from qcal_env.store import FileStore
from qcal_env.tools import TOOL_DEFINITIONS, handler_for

STEP1_OUTCOME_TEMPLATE = (
    "SweepReadout 已完成：ReadoutFreq 候选值为 {center_ghz:.9f} GHz，"
    "拟合 R²={r_squared:.4f}，状态为 pending_agent_review。"
    "候选标定：{candidate_ids}。详细报告：{report_path}"
)
STEP2_OUTCOME_TEMPLATE = (
    "SweepQubit 已完成：QubitFreq 候选值为 {center_ghz:.9f} GHz，"
    "拟合 R²={r_squared:.4f}，状态为 pending_agent_review。"
    "候选标定：{candidate_ids}。详细报告：{report_path}"
)
STEP3_OUTCOME_TEMPLATE = (
    "PowerRabi 已完成：amp180 候选值为 {result_value:.6g} a.u.，"
    "拟合 R²={r_squared:.4f}，状态为 pending_agent_review。"
    "候选标定：{candidate_ids}。详细报告：{report_path}"
)
STEP4_OUTCOME_TEMPLATE = (
    "SweepReadoutE 已完成：ReadoutFreqE 候选值为 {center_ghz:.9f} GHz，"
    "拟合 R²={r_squared:.4f}，状态为 pending_agent_review。"
    "候选标定：{candidate_ids}。详细报告：{report_path}"
)
STEP5_OUTCOME_TEMPLATE = (
    "QubitT1 已完成：T1 候选值为 {result_value:.6g} s，"
    "拟合 R²={r_squared:.4f}，状态为 pending_agent_review。"
    "候选标定：{candidate_ids}。详细报告：{report_path}"
)
STEP6_OUTCOME_TEMPLATE = (
    "Ramsey 已完成：T2* 候选值为 {result_value:.6g} s，"
    "拟合 R²={r_squared:.4f}，状态为 pending_agent_review。"
    "候选标定：{candidate_ids}。详细报告：{report_path}"
)
STEP6_ECHO_OUTCOME_TEMPLATE = (
    "Echo 已完成：T2Echo 候选值为 {result_value:.6g} s，"
    "拟合 R²={r_squared:.4f}，状态为 pending_agent_review。"
    "候选标定：{candidate_ids}。详细报告：{report_path}"
)
STEP7_OUTCOME_TEMPLATE = (
    "SingleShotHistogram 已完成：RayleighRatio 候选值为 {result_value:.6g}，"
    "判态保真度={assignment_fidelity:.4f}，状态为 pending_agent_review。"
    "候选标定：{candidate_ids}。详细报告：{report_path}"
)

# 查询工具的步骤视图：顺序即校准推进顺序；Step6 覆盖 Ramsey 与 Echo 两个 key。
_CALIBRATION_STEPS: list[tuple[int, str, tuple[str, ...]]] = [
    (1, "读取腔 g 态频率", ("readout.frequency.g",)),
    (2, "比特频率", ("qubit.frequency",)),
    (3, "π 脉冲幅度、波形参数与 IQ 旋转角", ("qubit.pi_pulse.amplitude", "qubit.pulse.mysigma", "qubit.pulse.coeff", "readout.iq_rotation_angle")),
    (4, "读取腔 e 态频率", ("readout.frequency.e",)),
    (5, "T1", ("qubit.t1",)),
    (6, "T2* (Ramsey)", ("qubit.t2",)),
    (6, "T2 Echo", ("qubit.t2_echo",)),
    (7, "单次测量判态", ("readout.single_shot.rayleigh_ratio",)),
]

_STEP_KEYS_BY_NO: dict[int, tuple[str, ...]] = {
    step_no: tuple(
        key
        for item_step_no, _description, keys in _CALIBRATION_STEPS
        if item_step_no == step_no
        for key in keys
    )
    for step_no in {item[0] for item in _CALIBRATION_STEPS}
}


class ExperimentAdapter(Protocol):
    def execute(self, plan: ExperimentPlan) -> RawResult: ...


@dataclass(frozen=True, slots=True)
class ActionContext:
    """Identifiers carried beside experiment parameters inside Env."""

    action_id: str
    calibration_id: str
    agent_id: str


class CalibrationEnv:
    def __init__(
        self,
        *,
        adapter: ExperimentAdapter,
        store: FileStore,
        backend_mode: str,
    ) -> None:
        self.adapter = adapter
        self.store = store
        self.backend_mode = backend_mode
        # One explicit list connects schema, name and handler. No hidden registries.
        self.tools = [
            {**definition, "callable": getattr(self, handler_for(str(definition["name"])))}
            for definition in TOOL_DEFINITIONS
        ]

    @property
    def public_tools(self) -> list[dict[str, object]]:
        return TOOL_DEFINITIONS

    def handle_action(
        self,
        name: str,
        parameters: Mapping[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        if not context.action_id or not context.calibration_id or not context.agent_id:
            return {"isError": True, "content": "Action 执行失败：action_id、calibration_id 和 agent_id 均不能为空。"}
        existing = self.store.find_action(context.action_id)
        if existing is not None:
            if (
                existing.get("calibration_id") != context.calibration_id
                or existing.get("name") != name
                or existing.get("request_inputs", existing.get("inputs")) != dict(parameters)
            ):
                return {"isError": True, "content": "同一 action_id 不能用于不同的 Action、calibration_id 或实验参数。"}
            outcome = existing.get("outcome")
            if isinstance(outcome, dict):
                return outcome
            return {"isError": True, "content": f"Action 已存在，当前状态为 {existing.get('status')}。"}

        timestamp = datetime.now(UTC).isoformat()
        action_record: dict[str, object] = {
            "action_id": context.action_id,
            "calibration_id": context.calibration_id,
            "agent_id": context.agent_id,
            "timestamp": timestamp,
            "name": name,
            "experiment": name,
            "backend_mode": self.backend_mode,
            "status": "received",
            "inputs": dict(parameters),
            "request_inputs": dict(parameters),
        }
        self.store.save_action(context.action_id, action_record)
        try:
            self.store.get_action_events(context.action_id)
        except KeyError:
            self.store.append_action_event(
                context.action_id,
                "received",
                f"Env 收到 {name} Action",
                {
                    "action": name,
                    "agent_id": context.agent_id,
                    "calibration_id": context.calibration_id,
                },
            )
        self.store.append_action_event(
            context.action_id,
            "validating",
            f"正在校验 {name} 请求",
        )
        tool = next((item for item in self.tools if item["name"] == name), None)
        if tool is None:
            outcome = {"isError": True, "content": f"Action 执行失败：未知 Action：{name}。"}
            self.store.save_action(
                context.action_id,
                {**action_record, "status": "failed", "error": outcome["content"], "outcome": outcome},
            )
            self.store.append_action_event(
                context.action_id,
                "failed",
                "Action 执行失败",
                {"error": outcome["content"]},
            )
            return outcome
        try:
            outcome = tool["callable"](dict(parameters), context)
            current = self.store.get_action(context.action_id)
            if current.get("status") == "received":
                self.store.save_action(
                    context.action_id,
                    {**current, "status": "succeeded", "outcome": outcome},
                )
            self.store.append_action_event(
                context.action_id,
                "completed",
                "Action 处理完成，Outcome 已生成",
                {"outcome": outcome},
            )
            return outcome
        except Exception as exc:
            outcome = {"isError": True, "content": f"{name} 执行失败：{exc}"}
            current = self.store.get_action(context.action_id)
            self.store.save_action(
                context.action_id,
                {**current, "status": "failed", "error": str(exc), "outcome": outcome},
            )
            self.store.append_action_event(
                context.action_id,
                "failed",
                f"{name} 执行失败",
                {"error": outcome["content"]},
            )
            return outcome

    def run_sweep_readout(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        plan = _step1_plan(parameters)
        return self._run_experiment(
            step="Step1",
            experiment="SweepReadout",
            plan=plan,
            inputs=parameters,
            context=context,
            calibration_key="readout.frequency.g",
            result_name="ReadoutFreq",
            template_name="step1.md",
            outcome_template=STEP1_OUTCOME_TEMPLATE,
        )

    def run_sweep_qubit(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        readout = self.store.active("readout.frequency.g", context.calibration_id)
        if readout is None:
            raise ValueError("Step2 需要同一 calibration_id 下 Agent 已确认的 Step1 读取频率。")
        parameters = self._inherit_step1(
            parameters,
            readout=readout,
            step="Step2",
            fields=("readout_amp", "measuretime", "waittime"),
        )
        plan = _step2_plan(parameters, readout_frequency_hz=float(readout["value"]))
        return self._run_experiment(
            step="Step2",
            experiment="SweepQubit",
            plan=plan,
            inputs={**parameters, "ReadoutFreq": plan.ReadoutFreq},
            context=context,
            calibration_key="qubit.frequency",
            result_name="QubitFreq",
            template_name="step2.md",
            outcome_template=STEP2_OUTCOME_TEMPLATE,
        )

    def run_power_rabi(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        readout = self._active_required("readout.frequency.g", context.calibration_id, "Step3 需要同一 calibration_id 下 Agent 已确认的 Step1 读取频率。")
        qubit = self._active_required("qubit.frequency", context.calibration_id, "Step3 需要同一 calibration_id 下 Agent 已确认的 Step2 比特频率。")
        parameters = self._inherit_step1(
            parameters,
            readout=readout,
            step="Step3",
            fields=("readout_amp", "measuretime", "waittime"),
        )
        plan = _step3_plan(
            parameters,
            readout_frequency_hz=float(readout["value"]),
            qubit_frequency_hz=float(qubit["value"]),
        )
        return self._run_experiment(
            step="Step3",
            experiment="PowerRabi",
            plan=plan,
            inputs={**parameters, "ReadoutFreq": plan.ReadoutFreq, "QubitFreq": plan.QubitFreq},
            context=context,
            calibration_key="qubit.pi_pulse.amplitude",
            result_name="amp180",
            template_name="step3.md",
            extra_calibrations=[
                {"key": "qubit.pulse.mysigma", "value": plan.mysigma, "unit": "ns"},
                {"key": "qubit.pulse.coeff", "value": plan.coeff, "unit": "a.u."},
            ],
            outcome_template=STEP3_OUTCOME_TEMPLATE,
        )

    def run_sweep_readout_e(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        readout = self._active_required("readout.frequency.g", context.calibration_id, "Step4 需要同一 calibration_id 下 Agent 已确认的 Step1 读取频率。")
        qubit = self._active_required("qubit.frequency", context.calibration_id, "Step4 需要同一 calibration_id 下 Agent 已确认的 Step2 比特频率。")
        pi_amp = self._active_required("qubit.pi_pulse.amplitude", context.calibration_id, "Step4 需要同一 calibration_id 下 Agent 已确认的 Step3 pi pulse 强度。")
        mysigma = self._active_required("qubit.pulse.mysigma", context.calibration_id, "Step4 需要同一 calibration_id 下 Agent 已确认的 Step3 mysigma。")
        coeff = self._active_required("qubit.pulse.coeff", context.calibration_id, "Step4 需要同一 calibration_id 下 Agent 已确认的 Step3 coeff。")
        parameters = self._inherit_step1(
            parameters,
            readout=readout,
            step="Step4",
            fields=("measuretime", "waittime"),
        )
        readout_amp = self._step1_input(readout, "readout_amp")
        plan = _step4_plan(
            parameters,
            qubit_frequency_hz=float(qubit["value"]),
            pi_amplitude=float(pi_amp["value"]),
            mysigma=float(mysigma["value"]),
            coeff=float(coeff["value"]),
            readout_amplitude=float(readout_amp),
        )
        return self._run_experiment(
            step="Step4",
            experiment="SweepReadoutE",
            plan=plan,
            inputs={
                **parameters,
                "QubitFreq": plan.QubitFreq,
                "amp180": plan.amp180,
                "mysigma": plan.mysigma,
                "coeff": plan.coeff,
                "readout_amp": plan.readout_amp,
            },
            context=context,
            calibration_key="readout.frequency.e",
            result_name="ReadoutFreqE",
            template_name="step4.md",
            extra_report_values={"center_g_hz": float(readout["value"])},
            outcome_template=STEP4_OUTCOME_TEMPLATE,
        )

    def run_qubit_t1(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        readout = self._active_required("readout.frequency.g", context.calibration_id, "Step5 需要同一 calibration_id 下 Agent 已确认的 Step1 读取频率。")
        qubit = self._active_required("qubit.frequency", context.calibration_id, "Step5 需要同一 calibration_id 下 Agent 已确认的 Step2 比特频率。")
        pi_amp = self._active_required("qubit.pi_pulse.amplitude", context.calibration_id, "Step5 需要同一 calibration_id 下 Agent 已确认的 Step3 pi pulse 强度。")
        mysigma = self._active_required("qubit.pulse.mysigma", context.calibration_id, "Step5 需要同一 calibration_id 下 Agent 已确认的 Step3 mysigma。")
        coeff = self._active_required("qubit.pulse.coeff", context.calibration_id, "Step5 需要同一 calibration_id 下 Agent 已确认的 Step3 coeff。")
        parameters = self._inherit_step1(
            parameters,
            readout=readout,
            step="Step5",
            fields=("readout_amp", "measuretime", "waittime"),
        )
        plan = _step5_plan(
            parameters,
            readout_frequency_hz=float(readout["value"]),
            qubit_frequency_hz=float(qubit["value"]),
            pi_amplitude=float(pi_amp["value"]),
            mysigma=float(mysigma["value"]),
            coeff=float(coeff["value"]),
        )
        return self._run_experiment(
            step="Step5",
            experiment="QubitT1",
            plan=plan,
            inputs={
                **parameters,
                "ReadoutFreq": plan.ReadoutFreq,
                "QubitFreq": plan.QubitFreq,
                "amp180": plan.amp180,
                "mysigma": plan.mysigma,
                "coeff": plan.coeff,
            },
            context=context,
            calibration_key="qubit.t1",
            result_name="T1",
            template_name="step5.md",
            outcome_template=STEP5_OUTCOME_TEMPLATE,
        )

    def run_ramsey(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        readout = self._active_required("readout.frequency.g", context.calibration_id, "Step6 需要同一 calibration_id 下 Agent 已确认的 Step1 读取频率。")
        qubit = self._active_required("qubit.frequency", context.calibration_id, "Step6 需要同一 calibration_id 下 Agent 已确认的 Step2 比特频率。")
        pi_amp = self._active_required("qubit.pi_pulse.amplitude", context.calibration_id, "Step6 需要同一 calibration_id 下 Agent 已确认的 Step3 pi pulse 强度。")
        mysigma = self._active_required("qubit.pulse.mysigma", context.calibration_id, "Step6 需要同一 calibration_id 下 Agent 已确认的 Step3 mysigma。")
        coeff = self._active_required("qubit.pulse.coeff", context.calibration_id, "Step6 需要同一 calibration_id 下 Agent 已确认的 Step3 coeff。")
        parameters = self._inherit_step1(
            parameters,
            readout=readout,
            step="Step6",
            fields=("measuretime",),
        )
        readout_amp = self._step1_input(readout, "readout_amp")
        plan = _step6_plan(
            parameters,
            readout_frequency_hz=float(readout["value"]),
            qubit_frequency_hz=float(qubit["value"]),
            pi_amplitude=float(pi_amp["value"]),
            mysigma=float(mysigma["value"]),
            coeff=float(coeff["value"]),
            readout_amplitude=float(readout_amp),
        )
        return self._run_experiment(
            step="Step6.1",
            experiment="Ramsey",
            plan=plan,
            inputs={
                **parameters,
                "ReadoutFreq": plan.ReadoutFreq,
                "QubitFreq": plan.QubitFreq,
                "amp180": plan.amp180,
                "mysigma": plan.mysigma,
                "coeff": plan.coeff,
                "readout_amp": plan.readout_amp,
            },
            context=context,
            calibration_key="qubit.t2",
            result_name="T2Star",
            template_name="step6_ramsey.md",
            outcome_template=STEP6_OUTCOME_TEMPLATE,
        )

    def run_echo(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        readout = self._active_required("readout.frequency.g", context.calibration_id, "Step6.2 需要同一 calibration_id 下 Agent 已确认的 Step1 读取频率。")
        qubit = self._active_required("qubit.frequency", context.calibration_id, "Step6.2 需要同一 calibration_id 下 Agent 已确认的 Step2 比特频率。")
        pi_amp = self._active_required("qubit.pi_pulse.amplitude", context.calibration_id, "Step6.2 需要同一 calibration_id 下 Agent 已确认的 Step3 pi pulse 强度。")
        mysigma = self._active_required("qubit.pulse.mysigma", context.calibration_id, "Step6.2 需要同一 calibration_id 下 Agent 已确认的 Step3 mysigma。")
        coeff = self._active_required("qubit.pulse.coeff", context.calibration_id, "Step6.2 需要同一 calibration_id 下 Agent 已确认的 Step3 coeff。")
        parameters = self._inherit_step1(
            parameters,
            readout=readout,
            step="Step6.2",
            fields=("measuretime",),
        )
        readout_amp = self._step1_input(readout, "readout_amp")
        plan = _step6_echo_plan(
            parameters,
            readout_frequency_hz=float(readout["value"]),
            qubit_frequency_hz=float(qubit["value"]),
            pi_amplitude=float(pi_amp["value"]),
            mysigma=float(mysigma["value"]),
            coeff=float(coeff["value"]),
            readout_amplitude=float(readout_amp),
        )
        return self._run_experiment(
            step="Step6.2",
            experiment="Echo",
            plan=plan,
            inputs={
                **parameters,
                "ReadoutFreq": plan.ReadoutFreq,
                "QubitFreq": plan.QubitFreq,
                "amp180": plan.amp180,
                "mysigma": plan.mysigma,
                "coeff": plan.coeff,
                "readout_amp": plan.readout_amp,
            },
            context=context,
            calibration_key="qubit.t2_echo",
            result_name="T2Echo",
            template_name="step6_echo.md",
            outcome_template=STEP6_ECHO_OUTCOME_TEMPLATE,
        )

    def run_single_shot_histogram(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        readout_g = self._active_required("readout.frequency.g", context.calibration_id, "Step7 需要同一 calibration_id 下 Agent 已确认的 Step1 读取频率。")
        readout_e = self.store.active("readout.frequency.e", context.calibration_id)
        qubit = self._active_required("qubit.frequency", context.calibration_id, "Step7 需要同一 calibration_id 下 Agent 已确认的 Step2 比特频率。")
        pi_amp = self._active_required("qubit.pi_pulse.amplitude", context.calibration_id, "Step7 需要同一 calibration_id 下 Agent 已确认的 Step3 pi pulse 强度。")
        mysigma = self._active_required("qubit.pulse.mysigma", context.calibration_id, "Step7 需要同一 calibration_id 下 Agent 已确认的 Step3 mysigma。")
        coeff = self._active_required("qubit.pulse.coeff", context.calibration_id, "Step7 需要同一 calibration_id 下 Agent 已确认的 Step3 coeff。")
        parameters = self._inherit_step1(
            parameters,
            readout=readout_g,
            step="Step7",
            fields=("readout_amp", "measuretime"),
        )
        center_readout_hz = 0.5 * (float(readout_g["value"]) + float(readout_e["value"])) if readout_e else float(readout_g["value"])
        plan = _step7_plan(
            parameters,
            readout_frequency_hz=center_readout_hz,
            qubit_frequency_hz=float(qubit["value"]),
            pi_amplitude=float(pi_amp["value"]),
            mysigma=float(mysigma["value"]),
            coeff=float(coeff["value"]),
        )
        return self._run_experiment(
            step="Step7",
            experiment="SingleShotHistogram",
            plan=plan,
            inputs={
                **parameters,
                "ReadoutFreq": plan.ReadoutFreq,
                "QubitFreq": plan.QubitFreq,
                "amp180": plan.amp180,
                "mysigma": plan.mysigma,
                "coeff": plan.coeff,
            },
            context=context,
            calibration_key="readout.single_shot.rayleigh_ratio",
            result_name="RayleighRatio",
            template_name="step7.md",
            outcome_template=STEP7_OUTCOME_TEMPLATE,
        )

    def confirm_calibration(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        allowed = {"candidate_ids", "note"}
        _require_exact(parameters, {"candidate_ids"}, allowed)
        candidate_ids = parameters["candidate_ids"]
        if not isinstance(candidate_ids, list) or not candidate_ids or not all(isinstance(item, str) for item in candidate_ids):
            raise ValueError("candidate_ids 必须是非空字符串数组。")
        self.store.append_action_event(
            context.action_id,
            "validated",
            "确认标定请求校验通过",
            {"candidate_ids": candidate_ids},
        )
        values = self.store.confirm(
            calibration_id=context.calibration_id,
            candidate_ids=candidate_ids,
            confirmed_by=context.agent_id,
            note=parameters.get("note") if isinstance(parameters.get("note"), str) else None,
        )
        confirmed_keys = ", ".join(str(value["key"]) for value in values)
        return {
            "isError": False,
            "content": f"标定结果已确认并生效：{confirmed_keys}。",
        }

    def get_calibration_status(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        _require_exact(parameters, set(), {"calibration_id"})
        confirmed_lines: list[str] = []
        unfinished: list[str] = []
        current_step: int | None = None
        for step_no, description, keys in _CALIBRATION_STEPS:
            values: list[str] = []
            for key in keys:
                item = self.store.active(key, context.calibration_id)
                if item is not None:
                    values.append(f"{key} = {item['value']:g} {item['unit']}")
            if len(values) == len(keys):
                confirmed_lines.append(f"- Step{step_no} {description}：{'；'.join(values)}")
            else:
                if current_step is None:
                    current_step = step_no
                unfinished.append(f"Step{step_no} {description}")
        stage = f"Step {current_step}" if current_step is not None else "全部完成"
        confirmed_text = "\n".join(confirmed_lines) if confirmed_lines else "（尚无已确认的标定值）"
        unfinished_text = "、".join(unfinished) if unfinished else "（无）"
        content = (
            f"当前阶段位于：**{stage}**\n\n"
            f"已确认的标定值：\n{confirmed_text}\n\n"
            f"未完成：{unfinished_text}"
        )
        return {"isError": False, "content": content}

    def list_candidates(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        _require_exact(parameters, {"step_no"}, {"step_no", "calibration_id"})
        step_no = parameters["step_no"]
        if not isinstance(step_no, int) or isinstance(step_no, bool) or not 1 <= step_no <= 7:
            raise ValueError("step_no 必须是 1 到 7 的整数。")
        keys = _STEP_KEYS_BY_NO[step_no]
        items = [
            item
            for item in self.store.calibrations()["candidates"]
            if item.get("calibration_id") == context.calibration_id
            and item.get("key") in keys
            and item.get("status") == "pending_agent_review"
        ]
        if not items:
            return {
                "isError": False,
                "content": f"Step{step_no} 当前没有待确认的候选值。",
            }
        lines = []
        for item in items:
            action = self.store.find_action(str(item["action_id"]))
            r_squared = ((action or {}).get("fit") or {}).get("r_squared")
            r2_text = f"R²={float(r_squared):.4f}" if isinstance(r_squared, (int, float)) else "R²=—"
            lines.append(
                f"- {item['value']:g} {item['unit']}：{r2_text}，"
                f"candidate_id={item['candidate_id']}，时间 {item['created_at']}"
            )
        return {
            "isError": False,
            "content": f"Step{step_no} 的候选值：\n\n" + "\n".join(lines),
        }

    def read_knowledge(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        _require_exact(parameters, set(), {"calibration_id", "topic"})
        topic = parameters.get("topic", "common")
        if not isinstance(topic, str):
            raise ValueError("topic 必须是非空字符串。")
        content = self.store.read_knowledge_document(topic)
        return {"isError": False, "content": content}

    def get_preset(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        _require_exact(parameters, set(), {"calibration_id"})
        content = self.store.read_preset_document()
        return {"isError": False, "content": content}

    def read_file(
        self,
        parameters: dict[str, object],
        context: ActionContext,
    ) -> dict[str, object]:
        _require_exact(parameters, {"path"}, {"path"})
        path = parameters["path"]
        if not isinstance(path, str) or not path:
            raise ValueError("path 必须是非空字符串。")
        self.store.append_action_event(
            context.action_id,
            "validated",
            "文件读取请求校验通过",
            {"path": path},
        )
        content = self.store.read_markdown_artifact(
            path,
            calibration_id=context.calibration_id,
        )
        self.store.append_action_event(
            context.action_id,
            "file_read",
            "Markdown 报告读取完成",
            {"path": path},
        )
        return {"isError": False, "content": content}

    def _run_experiment(
        self,
        *,
        step: str,
        experiment: str,
        plan: ExperimentPlan,
        inputs: dict[str, object],
        context: ActionContext,
        calibration_key: str,
        result_name: str,
        template_name: str,
        extra_calibrations: list[dict[str, object]] | None = None,
        outcome_template: str | None = None,
        extra_report_values: dict[str, object] | None = None,
    ) -> dict[str, object]:
        plan_data = _plan_dict(plan)
        self.store.append_action_event(
            context.action_id,
            "validated",
            f"参数校验通过，已生成 {type(plan).__name__}",
            {"plan": plan_data},
        )

        timestamp = datetime.now(UTC)
        action_dir = self.store.action_dir(context.action_id)
        received_record = self.store.get_action(context.action_id)
        base_record: dict[str, object] = {
            "action_id": context.action_id,
            "calibration_id": context.calibration_id,
            "agent_id": context.agent_id,
            "timestamp": timestamp.isoformat(),
            "step": step,
            "name": received_record.get("name"),
            "experiment": experiment,
            "backend_mode": self.backend_mode,
            "status": "running",
            "inputs": inputs,
            "request_inputs": received_record.get("request_inputs", inputs),
            "plan": plan_data,
        }
        self.store.save_action(context.action_id, base_record)
        try:
            self.store.append_action_event(
                context.action_id,
                "executing",
                f"已分发到 {self.backend_mode} 后端",
                {"backend_mode": self.backend_mode},
            )
            raw = self.adapter.execute(plan)
            # 统一 IQ 旋转：step3 计算旋转角，step4-6 复用已确认的旋转角。
            iq_angle_rad = 0.0
            if step in ("Step3", "Step4", "Step5", "Step6"):
                if step == "Step3":
                    iq_angle_rad = estimate_iq_rotation_angle(raw.i_values, raw.q_values)
                else:
                    angle_record = self.store.active("readout.iq_rotation_angle", context.calibration_id)
                    if angle_record is not None:
                        iq_angle_rad = float(angle_record["value"])
                rotated_i, rotated_q = rotate_iq(raw.i_values, raw.q_values, iq_angle_rad)
                raw = RawResult(
                    experiment_type=raw.experiment_type,
                    sweep_name=raw.sweep_name,
                    sweep_values=raw.sweep_values,
                    i_values=rotated_i,
                    q_values=rotated_q,
                    point_status=raw.point_status,
                    metadata={**raw.metadata, "iq_rotation_angle_rad": iq_angle_rad},
                )
            valid_point_count = sum(status == "ok" for status in raw.point_status)
            self.store.append_action_event(
                context.action_id,
                "raw_result_received",
                "后端原始扫描数据已返回",
                {
                    "sweep_name": raw.sweep_name,
                    "point_count": int(raw.sweep_values.size),
                    "valid_point_count": valid_point_count,
                },
            )
            save_raw_csv(raw, action_dir / "data.csv")
            self.store.append_action_event(
                context.action_id,
                "fitting",
                "正在分析实验数据",
                {"experiment_type": raw.experiment_type.value},
            )
            analysis = _analyze_and_plot(raw, step=step, experiment=experiment, path=action_dir / "plot.png")
            fit = analysis["fit"]
            self.store.append_action_event(
                context.action_id,
                "fit_completed",
                "实验数据分析完成",
                {
                    "model": fit["model"],
                    "result_name": result_name,
                    "result_value": analysis["result_value"],
                    "result_unit": analysis["unit"],
                    "r_squared": fit.get("r_squared"),
                },
            )
            candidate = self.store.add_candidate(
                action_id=context.action_id,
                calibration_id=context.calibration_id,
                key=calibration_key,
                value=float(analysis["result_value"]),
                unit=str(analysis["unit"]),
            )
            candidates = [candidate]
            for calibration in extra_calibrations or []:
                candidates.append(
                    self.store.add_candidate(
                        action_id=context.action_id,
                        calibration_id=context.calibration_id,
                        key=str(calibration["key"]),
                        value=float(calibration["value"]),
                        unit=str(calibration["unit"]),
                    )
                )
            if step == "Step3":
                candidates.append(
                    self.store.add_candidate(
                        action_id=context.action_id,
                        calibration_id=context.calibration_id,
                        key="readout.iq_rotation_angle",
                        value=float(iq_angle_rad),
                        unit="rad",
                    )
                )
            candidate_ids = ", ".join(str(item["candidate_id"]) for item in candidates)
            report_path = f"/files/{context.action_id}/report.md"
            plot_path = f"/files/{context.action_id}/plot.png"
            extra_values = dict(extra_report_values or {})
            if "center_g_hz" in extra_values and "center_hz" in fit:
                extra_values["center_e_hz"] = fit["center_hz"]
                extra_values["chi_hz"] = float(fit["center_hz"]) - float(extra_values["center_g_hz"])
            t2_value = fit.get("t2_s")
            t2_primary = t2_value[0] if isinstance(t2_value, list) and t2_value else t2_value
            report_values = {
                **inputs,
                **fit,
                **extra_values,
                "action_id": context.action_id,
                "run_id": context.action_id,
                "calibration_id": context.calibration_id,
                "timestamp": timestamp.isoformat(),
                "step": step,
                "experiment": experiment,
                "fit_model": fit["model"],
                "result_name": result_name,
                "result_value": analysis["result_value"],
                "result_unit": analysis["unit"],
                "center_hz": fit.get("center_hz", ""),
                "half_width_hz": fit.get("half_width_hz", ""),
                result_name: analysis["result_value"],
                "amp180_fit": analysis["result_value"],
                "T1": analysis["result_value"],
                "T2_star": t2_primary if t2_primary is not None else analysis["result_value"],
                "T2_echo": t2_primary if t2_primary is not None else analysis["result_value"],
                "detuning_hz": fit.get("detuning_hz", ""),
                "single_shot_threshold": fit.get("threshold", ""),
                "fidelity": fit.get("assignment_fidelity", ""),
                "g_center": f"({fit.get('g_center_i', '')}, {fit.get('g_center_q', '')})",
                "e_center": f"({fit.get('e_center_i', '')}, {fit.get('e_center_q', '')})",
                "candidate_id": candidate["candidate_id"],
                "candidate_ids": candidate_ids,
                "candidate_status": candidate["status"],
                "plot_path": plot_path,
            }
            template = (Path(__file__).parent / "templates" / template_name).read_text(encoding="utf-8")
            (action_dir / "report.md").write_text(template.format(**report_values), encoding="utf-8")
            artifacts = {
                "data": f"/files/{context.action_id}/data.csv",
                "plot": plot_path,
                "report": report_path,
            }
            self.store.append_action_event(
                context.action_id,
                "artifacts_saved",
                "实验产物已保存",
                artifacts,
            )
            public_fit = {
                key: value
                for key, value in fit.items()
                if key not in {"parameters", "fit_frequencies_hz", "fit_x", "fit_response"}
            }
            if outcome_template is not None:
                outcome_content = outcome_template.format(
                    center_ghz=float(fit.get("center_hz", analysis["result_value"])) / 1.0e9,
                    r_squared=float(fit.get("r_squared", 0.0)),
                    result_value=float(analysis["result_value"]),
                    assignment_fidelity=float(fit.get("assignment_fidelity", 0.0)),
                    candidate_ids=candidate_ids,
                    report_path=report_path,
                )
            else:
                outcome_content = f"{step} 执行完成，报告：{report_path}。候选标定：{candidate_ids}。"
            outcome: dict[str, object] = {"isError": False, "content": outcome_content}
            record = {
                **base_record,
                "status": "succeeded",
                "fit": public_fit,
                "result": {"parameter": result_name, "value": analysis["result_value"], "unit": analysis["unit"]},
                "candidate": candidate,
                "candidates": candidates,
                "artifacts": artifacts,
                "raw": {
                    "sweep_name": raw.sweep_name,
                    "point_count": int(raw.sweep_values.size),
                    "valid_point_count": valid_point_count,
                    "metadata": raw.metadata,
                },
                "outcome": outcome,
            }
            self.store.save_action(context.action_id, record)
            return outcome
        except Exception as exc:
            self.store.save_action(context.action_id, {**base_record, "status": "failed", "error": str(exc)})
            raise

    def _active_required(self, key: str, calibration_id: str, message: str) -> dict[str, object]:
        value = self.store.active(key, calibration_id)
        if value is None:
            raise ValueError(message)
        return value

    def _inherit_step1(
        self,
        parameters: dict[str, object],
        *,
        readout: dict[str, object],
        step: str,
        fields: tuple[str, ...],
    ) -> dict[str, object]:
        merged = dict(parameters)
        for field in fields:
            value = self._step1_input(readout, field)
            if field in merged and merged[field] != value:
                raise ValueError(f"{step} 的 {field} 必须与已确认 Step1 保持一致。")
            merged[field] = float(value)
        return merged

    def _step1_input(self, readout: dict[str, object], field: str) -> object:
        step1_action = self.store.get_action(str(readout["action_id"]))
        step1_inputs = step1_action.get("inputs")
        if not isinstance(step1_inputs, dict) or field not in step1_inputs:
            raise ValueError(f"已确认的 Step1 记录缺少 {field}。")
        return step1_inputs[field]


def _step1_plan(parameters: dict[str, object]) -> SweepReadoutPlan:
    required = {
        "ReadoutStartFreq1", "ReadoutStopFreq1", "Readoutstep1", "readout_amp",
        "roundRobin", "measuretime", "waittime", "expected_cycle_length",
    }
    _require_exact(parameters, required, required)
    plan = SweepReadoutPlan(**{key: parameters[key] for key in required})
    _validate_common(
        start=plan.ReadoutStartFreq1,
        stop=plan.ReadoutStopFreq1,
        step=plan.Readoutstep1,
        amplitude=plan.readout_amp,
        repetitions=plan.roundRobin,
        measuretime=plan.measuretime,
        waittime=plan.waittime,
        cycle=plan.expected_cycle_length,
    )
    return plan


def _step2_plan(parameters: dict[str, object], *, readout_frequency_hz: float) -> SweepQubitPlan:
    required = {
        "QubitStartFreq1", "QubitStopFreq1", "Qubitstep1", "amp180", "mysigma", "coeff",
        "readout_amp", "roundRobin", "measuretime", "waittime", "expected_cycle_length",
    }
    _require_exact(parameters, required, required)
    plan = SweepQubitPlan(
        **{key: parameters[key] for key in required},
        ReadoutFreq=readout_frequency_hz,
    )
    _validate_common(
        start=plan.QubitStartFreq1,
        stop=plan.QubitStopFreq1,
        step=plan.Qubitstep1,
        amplitude=plan.readout_amp,
        repetitions=plan.roundRobin,
        measuretime=plan.measuretime,
        waittime=plan.waittime,
        cycle=plan.expected_cycle_length,
    )
    if min(plan.amp180, plan.mysigma, plan.coeff) <= 0.0:
        raise ValueError("amp180、mysigma 和 coeff 必须为正数。")
    return plan


def _step3_plan(
    parameters: dict[str, object],
    *,
    readout_frequency_hz: float,
    qubit_frequency_hz: float,
) -> PowerRabiPlan:
    required = {
        "numstep", "RabiStep", "mysigma", "coeff",
        "readout_amp", "roundRobin", "measuretime", "waittime", "expected_cycle_length",
    }
    _require_exact(parameters, required, required)
    plan = PowerRabiPlan(
        **{key: parameters[key] for key in required},
        ReadoutFreq=readout_frequency_hz,
        QubitFreq=qubit_frequency_hz,
    )
    if isinstance(plan.numstep, bool) or not isinstance(plan.numstep, int) or plan.numstep < 2:
        raise ValueError("numstep 必须是不小于 2 的整数。")
    _validate_common(
        start=0.0,
        stop=(plan.numstep - 1) * plan.RabiStep,
        step=plan.RabiStep,
        amplitude=plan.readout_amp,
        repetitions=plan.roundRobin,
        measuretime=plan.measuretime,
        waittime=plan.waittime,
        cycle=plan.expected_cycle_length,
        allow_zero_start=True,
    )
    if min(plan.mysigma, plan.coeff) <= 0.0:
        raise ValueError("mysigma 和 coeff 必须为正数。")
    return plan


def _step4_plan(
    parameters: dict[str, object],
    *,
    qubit_frequency_hz: float,
    pi_amplitude: float,
    mysigma: float,
    coeff: float,
    readout_amplitude: float,
) -> SweepReadoutEPlan:
    required = {
        "ReadoutStartFreq1", "ReadoutStopFreq1", "Readoutstep1",
        "roundRobin", "measuretime", "waittime", "expected_cycle_length",
    }
    _require_exact(parameters, required, required)
    plan = SweepReadoutEPlan(
        **{key: parameters[key] for key in required},
        QubitFreq=qubit_frequency_hz,
        amp180=pi_amplitude,
        mysigma=mysigma,
        coeff=coeff,
        readout_amp=readout_amplitude,
    )
    _validate_common(
        start=plan.ReadoutStartFreq1,
        stop=plan.ReadoutStopFreq1,
        step=plan.Readoutstep1,
        amplitude=plan.readout_amp,
        repetitions=plan.roundRobin,
        measuretime=plan.measuretime,
        waittime=plan.waittime,
        cycle=plan.expected_cycle_length,
    )
    if min(plan.amp180, plan.mysigma, plan.coeff) <= 0.0:
        raise ValueError("amp180、mysigma 和 coeff 必须为正数。")
    return plan


def _step5_plan(
    parameters: dict[str, object],
    *,
    readout_frequency_hz: float,
    qubit_frequency_hz: float,
    pi_amplitude: float,
    mysigma: float,
    coeff: float,
) -> QubitT1Plan:
    required = {
        "numstep", "timeStep",
        "readout_amp", "roundRobin", "measuretime", "waittime", "expected_cycle_length",
    }
    _require_exact(parameters, required, required)
    plan = QubitT1Plan(
        **{key: parameters[key] for key in required},
        ReadoutFreq=readout_frequency_hz,
        QubitFreq=qubit_frequency_hz,
        amp180=pi_amplitude,
        mysigma=mysigma,
        coeff=coeff,
    )
    if isinstance(plan.numstep, bool) or not isinstance(plan.numstep, int) or plan.numstep < 5:
        raise ValueError("numstep 必须是不小于 5 的整数。")
    _validate_common(
        start=0.0,
        stop=(plan.numstep - 1) * plan.timeStep,
        step=plan.timeStep,
        amplitude=plan.readout_amp,
        repetitions=plan.roundRobin,
        measuretime=plan.measuretime,
        waittime=plan.waittime,
        cycle=plan.expected_cycle_length,
        allow_zero_start=True,
    )
    if min(plan.amp180, plan.mysigma, plan.coeff) <= 0.0:
        raise ValueError("amp180、mysigma 和 coeff 必须为正数。")
    return plan


def _step6_plan(
    parameters: dict[str, object],
    *,
    readout_frequency_hz: float,
    qubit_frequency_hz: float,
    pi_amplitude: float,
    mysigma: float,
    coeff: float,
    readout_amplitude: float,
) -> RamseyPlan:
    required = {
        "numstep", "timeStep", "roundRobin", "measuretime", "expected_cycle_length",
    }
    _require_exact(parameters, required, required)
    plan = RamseyPlan(
        **{key: parameters[key] for key in required},
        ReadoutFreq=readout_frequency_hz,
        QubitFreq=qubit_frequency_hz,
        amp180=pi_amplitude,
        mysigma=mysigma,
        coeff=coeff,
        readout_amp=readout_amplitude,
    )
    if isinstance(plan.numstep, bool) or not isinstance(plan.numstep, int) or plan.numstep < 8:
        raise ValueError("numstep 必须是不小于 8 的整数。")
    _validate_common(
        start=0.0,
        stop=(plan.numstep - 1) * plan.timeStep,
        step=plan.timeStep,
        amplitude=plan.readout_amp,
        repetitions=plan.roundRobin,
        measuretime=plan.measuretime,
        waittime=0.0,
        cycle=plan.expected_cycle_length,
        allow_zero_start=True,
    )
    if min(plan.amp180, plan.mysigma, plan.coeff) <= 0.0:
        raise ValueError("amp180、mysigma 和 coeff 必须为正数。")
    return plan


def _step6_echo_plan(
    parameters: dict[str, object],
    *,
    readout_frequency_hz: float,
    qubit_frequency_hz: float,
    pi_amplitude: float,
    mysigma: float,
    coeff: float,
    readout_amplitude: float,
) -> EchoPlan:
    required = {
        "numstep", "timeStep", "roundRobin", "measuretime", "expected_cycle_length",
    }
    _require_exact(parameters, required, required)
    plan = EchoPlan(
        **{key: parameters[key] for key in required},
        ReadoutFreq=readout_frequency_hz,
        QubitFreq=qubit_frequency_hz,
        amp180=pi_amplitude,
        mysigma=mysigma,
        coeff=coeff,
        readout_amp=readout_amplitude,
    )
    if isinstance(plan.numstep, bool) or not isinstance(plan.numstep, int) or plan.numstep < 8:
        raise ValueError("numstep 必须是不小于 8 的整数。")
    _validate_common(
        start=0.0,
        stop=(plan.numstep - 1) * plan.timeStep,
        step=plan.timeStep,
        amplitude=plan.readout_amp,
        repetitions=plan.roundRobin,
        measuretime=plan.measuretime,
        waittime=0.0,
        cycle=plan.expected_cycle_length,
        allow_zero_start=True,
    )
    if min(plan.amp180, plan.mysigma, plan.coeff) <= 0.0:
        raise ValueError("amp180、mysigma 和 coeff 必须为正数。")
    return plan


def _step7_plan(
    parameters: dict[str, object],
    *,
    readout_frequency_hz: float,
    qubit_frequency_hz: float,
    pi_amplitude: float,
    mysigma: float,
    coeff: float,
) -> SingleShotHistogramPlan:
    required = {
        "roundRobin", "bin",
        "readout_amp", "measuretime", "expected_cycle_length",
    }
    _require_exact(parameters, required, required)
    plan = SingleShotHistogramPlan(
        **{key: parameters[key] for key in required},
        ReadoutFreq=readout_frequency_hz,
        QubitFreq=qubit_frequency_hz,
        amp180=pi_amplitude,
        mysigma=mysigma,
        coeff=coeff,
    )
    values = (plan.readout_amp, plan.measuretime, plan.expected_cycle_length, plan.mysigma, plan.coeff, plan.amp180)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise ValueError("幅度和时间参数必须是数字。")
    if isinstance(plan.roundRobin, bool) or not isinstance(plan.roundRobin, int) or plan.roundRobin < 20:
        raise ValueError("roundRobin 必须是不小于 20 的整数。")
    if isinstance(plan.bin, bool) or not isinstance(plan.bin, int) or plan.bin <= 0:
        raise ValueError("bin 必须是正整数。")
    if min(plan.readout_amp, plan.measuretime, plan.expected_cycle_length, plan.mysigma, plan.coeff, plan.amp180) <= 0.0:
        raise ValueError("幅度和正时间参数必须为正数。")
    if plan.expected_cycle_length < plan.measuretime:
        raise ValueError("expected_cycle_length 无效。")
    return plan


def _analyze_and_plot(raw: RawResult, *, step: str, experiment: str, path: Path) -> dict[str, object]:
    if raw.experiment_type == ExperimentType.READOUT_SPECTROSCOPY:
        response = raw.amplitudes
        fit = fit_lorentzian(raw.sweep_values, response)
        save_fit_plot(
            raw=raw,
            response=response,
            fit=fit,
            title="Readout Spectroscopy: g-State Effective Frequency",
            x_label=PLOT_AXES_BY_EXPERIMENT["SweepReadout"][0],
            y_label="A",
            x_scale=1.0e9,
            path=path,
            data_label="real (f, A)",
            center_label=f"fit g-state readout = {float(fit['center_hz']) / 1.0e9:.9f} GHz",
        )
        return {"fit": fit, "result_value": float(fit["center_hz"]), "unit": "Hz"}
    if raw.experiment_type == ExperimentType.QUBIT_SPECTROSCOPY:
        response = _baseline_removed_amplitude(raw)
        fit = fit_lorentzian(raw.sweep_values, response)
        save_fit_plot(
            raw=raw,
            response=response,
            fit=fit,
            title="Qubit Spectroscopy Lorentzian Fit",
            x_label="qubit drive frequency f (GHz)",
            y_label="A",
            x_scale=1.0e9,
            path=path,
            data_label="real (f, A)",
            center_label=f"fit center = {float(fit['center_hz']) / 1.0e9:.9f} GHz",
        )
        return {"fit": fit, "result_value": float(fit["center_hz"]), "unit": "Hz"}
    if raw.experiment_type == ExperimentType.POWER_RABI:
        # raw 已在 _run_experiment 中完成 IQ 旋转，这里直接拟合旋转后的 I/Q。
        response = raw.i_values
        fit = fit_power_rabi(raw.sweep_values, response)
        q_fit = fit_power_rabi(raw.sweep_values, raw.q_values)
        save_power_rabi_plot(raw=raw, response=response, fit=fit, q_fit=q_fit, title=step, path=path)
        return {"fit": fit, "result_value": float(fit["pi_amplitude"]), "unit": "a.u."}
    if raw.experiment_type == ExperimentType.READOUT_SPECTROSCOPY_E:
        response = raw.amplitudes
        fit = fit_lorentzian(raw.sweep_values, response)
        save_fit_plot(
            raw=raw,
            response=response,
            fit=fit,
            title=f"{step}: f vs A",
            x_label=PLOT_AXES_BY_EXPERIMENT["SweepReadoutE"][0],
            y_label=PLOT_AXES_BY_EXPERIMENT["SweepReadoutE"][1],
            x_scale=1.0e9,
            path=path,
        )
        return {"fit": fit, "result_value": float(fit["center_hz"]), "unit": "Hz"}
    if raw.experiment_type == ExperimentType.QUBIT_T1:
        response = raw.i_values
        finite = np.isfinite(raw.sweep_values) & np.isfinite(response)
        if np.count_nonzero(finite) >= 2:
            finite_response = response[finite]
            if finite_response[-1] < finite_response[0]:
                response = response.copy()
                response[finite] = finite_response[0] + finite_response[-1] - finite_response
        fit = fit_t1(raw.sweep_values, response)
        annotation = f"T1={float(fit['decay_time_s']) / 1.0e-6:.4f} us"
        save_xy_fit_plot(
            raw=raw,
            response=response,
            fit=fit,
            title=f"{step}: T vs I",
            x_label=PLOT_AXES_BY_EXPERIMENT["QubitT1"][0],
            y_label=PLOT_AXES_BY_EXPERIMENT["QubitT1"][1],
            x_scale=1.0e-6,
            path=path,
            annotation=annotation,
        )
        return {"fit": fit, "result_value": float(fit["decay_time_s"]), "unit": "s"}
    if raw.experiment_type == ExperimentType.RAMSEY:
        response = raw.i_values
        fit = fit_ramsey(raw.sweep_values, response, ramsey_angle_hz=float(raw.metadata.get("ramsey_angle_hz", 0.0)))
        t2_values = fit["t2_s"] if isinstance(fit["t2_s"], list) else [fit["t2_s"]]
        detuning_values = fit["detuning_hz"] if isinstance(fit["detuning_hz"], list) else [fit["detuning_hz"]]
        annotation = "\n".join(
            [
                "T2*=" + ", ".join(f"{float(value) / 1.0e-6:.4f} us" for value in t2_values),
                "detuning=" + ", ".join(f"{float(value) / 1.0e3:.4f} kHz" for value in detuning_values),
                f"R2={float(fit['r_squared']):.4f}",
            ]
        )
        save_xy_fit_plot(
            raw=raw,
            response=response,
            fit=fit,
            title=f"{step}: T vs I",
            x_label=PLOT_AXES_BY_EXPERIMENT["Ramsey"][0],
            y_label=PLOT_AXES_BY_EXPERIMENT["Ramsey"][1],
            x_scale=1.0e-6,
            path=path,
            annotation=annotation,
        )
        return {"fit": fit, "result_value": float(t2_values[0]), "unit": "s"}
    if raw.experiment_type == ExperimentType.ECHO:
        response = raw.i_values
        fit = fit_ramsey(raw.sweep_values, response, ramsey_angle_hz=float(raw.metadata.get("echo_angle_hz", 0.0)))
        t2_values = fit["t2_s"] if isinstance(fit["t2_s"], list) else [fit["t2_s"]]
        detuning_values = fit["detuning_hz"] if isinstance(fit["detuning_hz"], list) else [fit["detuning_hz"]]
        annotation = "\n".join(
            [
                "T2Echo=" + ", ".join(f"{float(value) / 1.0e-6:.4f} us" for value in t2_values),
                "detuning=" + ", ".join(f"{float(value) / 1.0e3:.4f} kHz" for value in detuning_values),
                f"R2={float(fit['r_squared']):.4f}",
            ]
        )
        save_xy_fit_plot(
            raw=raw,
            response=response,
            fit=fit,
            title=f"{step}: T vs I",
            x_label=PLOT_AXES_BY_EXPERIMENT["Echo"][0],
            y_label=PLOT_AXES_BY_EXPERIMENT["Echo"][1],
            x_scale=1.0e-6,
            path=path,
            annotation=annotation,
        )
        return {"fit": fit, "result_value": float(t2_values[0]), "unit": "s"}
    if raw.experiment_type == ExperimentType.SINGLE_SHOT_HISTOGRAM:
        fit = analyze_single_shot(raw)
        save_single_shot_plot(raw=raw, analysis=fit, title=f"{step}: I vs Q", path=path)
        return {"fit": fit, "result_value": float(fit["rayleigh_ratio"]), "unit": "ratio"}
    raise TypeError(f"Unsupported experiment type: {raw.experiment_type}")


def _baseline_removed_amplitude(raw: RawResult) -> np.ndarray:
    iq = raw.i_values + 1j * raw.q_values
    finite = np.isfinite(iq)
    if np.count_nonzero(finite) < 5:
        return raw.amplitudes
    valid_iq = iq[finite]
    edge_count = max(2, min(valid_iq.size // 5, 10))
    baseline = np.mean(np.concatenate([valid_iq[:edge_count], valid_iq[-edge_count:]]))
    return np.abs(iq - baseline)



def _require_exact(parameters: dict[str, object], required: set[str], allowed: set[str]) -> None:
    missing = required - set(parameters)
    unknown = set(parameters) - allowed
    if missing:
        raise ValueError(f"缺少参数: {sorted(missing)}")
    if unknown:
        raise ValueError(f"未知参数: {sorted(unknown)}")


def _validate_common(
    *,
    start: float,
    stop: float,
    step: float,
    amplitude: float,
    repetitions: int,
    measuretime: float,
    waittime: float,
    cycle: float,
    allow_zero_start: bool = False,
) -> None:
    values = (start, stop, step, amplitude, measuretime, waittime, cycle)
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise ValueError("频率、幅度和时间参数必须是数字。")
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions <= 0:
        raise ValueError("roundRobin 必须是正整数。")
    start_invalid = start < 0.0 if allow_zero_start else start <= 0.0
    if start_invalid or stop <= start or step <= 0.0 or amplitude <= 0.0:
        raise ValueError("扫描范围、步长和幅度无效。")
    if measuretime <= 0.0 or waittime < 0.0 or cycle < measuretime + waittime:
        raise ValueError("measuretime、waittime 或 expected_cycle_length 无效。")
    if int((stop - start) / step) + 1 < 5:
        raise ValueError("扫描至少需要 5 个频点。")


def _plan_dict(plan: ExperimentPlan) -> dict[str, object]:
    value = asdict(plan)
    value["experiment_type"] = plan.experiment_type.value
    return value
