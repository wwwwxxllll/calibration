"""All Agent tools are deliberately visible in one list."""

TOOL_DEFINITIONS = [
    {
        "name": "MeasureReadoutFrequencyG",
        "description": "Step1: Sweep and fit the readout resonator frequency for the qubit's ground (g) state.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session this action belongs to.",
                },
                "ReadoutStartFreq1": {
                    "type": "number",
                    "minimum": 100000000,
                    "maximum": 20000000000,
                    "description": "Start frequency of the readout sweep (Hz).",
                },
                "ReadoutStopFreq1": {
                    "type": "number",
                    "minimum": 100000000,
                    "maximum": 20000000000,
                    "description": "Stop frequency of the readout sweep (Hz).",
                },
                "Readoutstep1": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Frequency step size of the readout sweep (Hz).",
                },
                "readout_amp": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000,
                    "description": "Readout pulse amplitude.",
                },
                "roundRobin": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 5000,
                    "description": "Number of repeated acquisitions averaged at each sweep point.",
                },
                "measuretime": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000000,
                    "description": "Measurement time per acquisition.",
                },
                "waittime": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000000,
                    "description": "Wait time before each acquisition.",
                },
                "expected_cycle_length": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Expected total length of one full sweep cycle.",
                },
            },
            "required": [
                "calibration_id",
                "ReadoutStartFreq1",
                "ReadoutStopFreq1",
                "Readoutstep1",
                "readout_amp",
                "roundRobin",
                "measuretime",
                "waittime",
                "expected_cycle_length",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "MeasureQubitFrequency",
        "description": "Step2: Sweep and fit the qubit frequency using the confirmed readout frequency. readout_amp / measuretime / waittime are inherited from the confirmed Step1.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session this action belongs to.",
                },
                "QubitStartFreq1": {
                    "type": "number",
                    "minimum": 100000000,
                    "maximum": 20000000000,
                    "description": "Start frequency of the qubit drive sweep (Hz).",
                },
                "QubitStopFreq1": {
                    "type": "number",
                    "minimum": 100000000,
                    "maximum": 20000000000,
                    "description": "Stop frequency of the qubit drive sweep (Hz).",
                },
                "Qubitstep1": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Frequency step size of the qubit drive sweep (Hz).",
                },
                "amp180": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000,
                    "description": "Pi-pulse amplitude used for state preparation (a.u.).",
                },
                "mysigma": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000000,
                    "description": "Gaussian pulse sigma width (ns).",
                },
                "coeff": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000,
                    "description": "Pulse amplitude coefficient (a.u.).",
                },
                "roundRobin": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 2000,
                    "description": "Number of repeated acquisitions averaged at each sweep point.",
                },
                "expected_cycle_length": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Expected total length of one full sweep cycle.",
                },
            },
            "required": [
                "calibration_id",
                "QubitStartFreq1",
                "QubitStopFreq1",
                "Qubitstep1",
                "amp180",
                "mysigma",
                "coeff",
                "roundRobin",
                "expected_cycle_length",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "MeasurePiPulseAmplitude",
        "description": "Step3: Sweep the drive amplitude at the fixed qubit frequency to fit the pi-pulse amplitude. readout_amp / measuretime / waittime are inherited from the confirmed Step1.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session this action belongs to.",
                },
                "numstep": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Number of drive amplitude sweep points.",
                },
                "RabiStep": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000,
                    "description": "Amplitude step size of the Rabi sweep (a.u.).",
                },
                "mysigma": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000000,
                    "description": "Gaussian pulse sigma width (ns).",
                },
                "coeff": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000,
                    "description": "Pulse amplitude coefficient (a.u.).",
                },
                "roundRobin": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 450,
                    "description": "Number of repeated acquisitions averaged at each sweep point.",
                },
                "expected_cycle_length": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Expected total length of one full sweep cycle.",
                },
            },
            "required": [
                "calibration_id",
                "numstep",
                "RabiStep",
                "mysigma",
                "coeff",
                "roundRobin",
                "expected_cycle_length",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "MeasureReadoutFrequencyE",
        "description": "Step4: Prepare the qubit in the excited (e) state, then sweep the readout frequency to fit the e-state readout frequency. measuretime / waittime are inherited from the confirmed Step1; readout_amp / qubit / pi amplitude / pulse shape from Steps 1-3.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session this action belongs to.",
                },
                "ReadoutStartFreq1": {
                    "type": "number",
                    "minimum": 100000000,
                    "maximum": 20000000000,
                    "description": "Start frequency of the readout sweep (Hz).",
                },
                "ReadoutStopFreq1": {
                    "type": "number",
                    "minimum": 100000000,
                    "maximum": 20000000000,
                    "description": "Stop frequency of the readout sweep (Hz).",
                },
                "Readoutstep1": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Frequency step size of the readout sweep (Hz).",
                },
                "roundRobin": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1000,
                    "description": "Number of repeated acquisitions averaged at each sweep point.",
                },
                "expected_cycle_length": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Expected total length of one full sweep cycle.",
                },
            },
            "required": [
                "calibration_id",
                "ReadoutStartFreq1",
                "ReadoutStopFreq1",
                "Readoutstep1",
                "roundRobin",
                "expected_cycle_length",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "MeasureT1",
        "description": "Step5: Sweep the wait time after a pi pulse to fit the qubit T1 relaxation time. readout_amp / measuretime / waittime are inherited from Step1; mysigma / coeff from the confirmed Step3.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session this action belongs to.",
                },
                "numstep": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Number of wait-time sweep points.",
                },
                "timeStep": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000000,
                    "description": "Wait-time step size between consecutive points.",
                },
                "roundRobin": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 450,
                    "description": "Number of repeated acquisitions averaged at each sweep point.",
                },
                "expected_cycle_length": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Expected total length of one full sweep cycle.",
                },
            },
            "required": [
                "calibration_id",
                "numstep",
                "timeStep",
                "roundRobin",
                "expected_cycle_length",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "MeasureT2Star",
        "description": "Step6.1: Sweep the Ramsey delay and final pi/2 phase to fit the qubit T2* coherence time. measuretime is inherited from the confirmed Step1.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session this action belongs to.",
                },
                "numstep": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Number of Ramsey delay sweep points.",
                },
                "timeStep": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000000,
                    "description": "Ramsey delay step size between consecutive points.",
                },
                "roundRobin": {
                    "type": "integer",
                    "minimum": 230,
                    "default": 230,
                    "description": "Number of repeated acquisitions averaged at each sweep point.",
                },
                "expected_cycle_length": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Expected total length of one full sweep cycle.",
                },
            },
            "required": [
                "calibration_id",
                "numstep",
                "timeStep",
                "roundRobin",
                "expected_cycle_length",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "MeasureT2Echo",
        "description": "Step6.2: Sweep the echo delay and final pi/2 phase to fit the T2 coherence time under echo protection. measuretime is inherited from the confirmed Step1.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session this action belongs to.",
                },
                "numstep": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Number of echo delay sweep points.",
                },
                "timeStep": {
                    "type": "number",
                    "minimum": 0.001,
                    "maximum": 1000000000,
                    "description": "Echo delay step size between consecutive points.",
                },
                "roundRobin": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 230,
                    "description": "Number of repeated acquisitions averaged at each sweep point.",
                },
                "expected_cycle_length": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Expected total length of one full sweep cycle.",
                },
            },
            "required": [
                "calibration_id",
                "numstep",
                "timeStep",
                "roundRobin",
                "expected_cycle_length",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "MeasureSingleShotReadout",
        "description": "Step7: Prepare g/e states separately and acquire I/Q scatter points to fit the readout distinguishability. readout_amp / measuretime are inherited from Step1; mysigma / coeff from the confirmed Step3.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session this action belongs to.",
                },
                "roundRobin": {
                    "type": "integer",
                    "minimum": 20,
                    "default": 9000,
                    "description": "Number of repeated acquisitions averaged per state.",
                },
                "bin": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100000,
                    "description": "Number of histogram bins for the I/Q scatter.",
                },
                "expected_cycle_length": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 1000000000,
                    "description": "Expected total length of one full sweep cycle.",
                },
            },
            "required": [
                "calibration_id",
                "roundRobin",
                "bin",
                "expected_cycle_length",
            ],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_file",
        "description": "Read an artifact saved by QCal Env; currently supports UTF-8 Markdown reports only.",
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session the artifact belongs to.",
                },
                "path": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Logical resource path returned by the Env, e.g. /files/{action_id}/report.md.",
                },
            },
            "required": ["calibration_id", "path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ConfirmCalibration",
        "description": (
            "把你判定为当前实验最合理的候选标定值正式生效。"
            "仅当候选值通过了你的合格判定、且你明确认可该数值时才调用；"
            "确认后该值将用于后续所有依赖步骤。"
            "对没有把握的候选不要调用本工具；需要回顾或比较候选时先调用 ListCandidates。"
        ),
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Identifier of the calibration session.",
                },
                "candidate_ids": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string"},
                    "description": "Candidate IDs selected by the Agent to confirm.",
                },
                "note": {
                    "type": ["string", "null"],
                    "description": "Optional note attached to the confirmation.",
                },
            },
            "required": ["calibration_id", "candidate_ids"],
            "additionalProperties": False,
        },
    },
    {
        "name": "GetCalibrationStatus",
        "description": (
            "查询当前校准会话的权威进度与已生效标定值。"
            "Finish 结束流程前必须调用本工具，核对全部实验步骤均已确认；"
            "也可在流程中随时调用以了解当前进度。"
        ),
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "校准会话标识（与实验工具中的会话字段一致）。",
                },
            },
            "required": ["calibration_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ListCandidates",
        "description": (
            "查询指定步骤当前全部候选值及各自的拟合指标。"
            "当你需要回顾历史扫描、比较多个候选并挑选最优值时调用本工具；"
            "确认前建议先调用本工具核对。"
        ),
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "校准会话标识（与实验工具中的会话字段一致）。",
                },
                "step_no": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 7,
                    "description": (
                        "实验步骤编号：1 读取腔 g 态频率；2 比特频率；3 π 脉冲；"
                        "4 读取腔 e 态频率；5 T1；6 Ramsey 与 Echo；7 单次测量判态。"
                    ),
                },
            },
            "required": ["calibration_id", "step_no"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ReadKnowledge",
        "description": (
            "查询量子校准的通用知识与经验手册（判据、初始参数建议、调参经验、常见问题）。"
            "首次标定某步骤前、以及调参无方向时调用。当前仅支持通用手册（common）。"
        ),
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "校准会话标识（Env 要求每次 Action 都携带，用于归属与审计）。",
                },
                "topic": {
                    "type": "string",
                    "enum": ["common"],
                    "default": "common",
                    "description": "知识主题；当前只有通用手册 common，后续扩展分主题内容。",
                },
            },
            "required": ["calibration_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "GetPreset",
        "description": (
            "查询待标定样品的固有属性预设范围文档。这是样品出厂特性的先验范围"
            "（标定目标本身的预期区间），不是调参经验；首次标定某步骤前调用以确定"
            "初始扫描范围。每次调用返回完整预设文档。"
        ),
        "inputSchema": {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "calibration_id": {
                    "type": "string",
                    "minLength": 1,
                    "description": "校准会话标识（用于校验会话归属）。",
                },
            },
            "required": ["calibration_id"],
            "additionalProperties": False,
        },
    },
]

_HANDLERS = {
    "MeasureReadoutFrequencyG": "run_sweep_readout",
    "MeasureQubitFrequency": "run_sweep_qubit",
    "MeasurePiPulseAmplitude": "run_power_rabi",
    "MeasureReadoutFrequencyE": "run_sweep_readout_e",
    "MeasureT1": "run_qubit_t1",
    "MeasureT2Star": "run_ramsey",
    "MeasureT2Echo": "run_echo",
    "MeasureSingleShotReadout": "run_single_shot_histogram",
    "read_file": "read_file",
    "ConfirmCalibration": "confirm_calibration",
    "GetCalibrationStatus": "get_calibration_status",
    "ListCandidates": "list_candidates",
    "ReadKnowledge": "read_knowledge",
    "GetPreset": "get_preset",
}


def handler_for(name: str) -> str:
    """Map a public tool name to the CalibrationEnv method that runs it."""
    return _HANDLERS[name]


__all__ = ["TOOL_DEFINITIONS", "handler_for"]
