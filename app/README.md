# qcal Step1/Step2 Env

这是依据 `env架构设计描述.md` 收敛后的第一版：Env 外包装 QuTiP/Hardware Adapter，目前只实现 Step1、Step2 和 Agent 确认。

## 结构

- `qcal-contracts`：两个简单 Plan 和一个 RawResult。
- `qcal-env`：显式 Tool 列表、直接运行流程、拟合/报告和轻量文件 Store。
- `qcal-qutip-backend`：以 `feature_adapter_1` 为核心的 QuTiP Adapter 和虚拟设备；自己加载 Profile。
- `qcal-hardware-backend`：未实现占位。

## 安装和测试

```bash
conda activate qutip
uv sync --all-packages --extra server
uv run pytest -q
```

## 安装 Star Protocol

工作区已固定官方 MengLong SDK，并从 Star Protocol 官方仓库固定提交安装
Star SDK：

```bash
uv sync --all-packages --extra server --extra star
uv pip install --no-deps \
  "git+https://github.com/GCYYfun/star-protocol.git@99a87c6b43bc4142fc50fba88c76bd32220927c8"
```

当前官方源码的实际 API 与 README 示例存在差异：类名是 `HubServer`，Client
构造参数是 `hub_url`，线上 Action 字段是 `message.action`、
`message.action_id` 和 `message.parameters`。本项目以固定提交的实际代码和
真实 WebSocket 验证结果为准。

## 真实 Star WebSocket Step1/Step2 验证

打开三个终端，并都进入本目录、激活 `qutip` 环境。

终端 1，启动独立 Hub：

```bash
uv run python scripts/run_star_hub.py
```

终端 2，启动连接 Hub 的 QCal Env：

```bash
uv run python scripts/run_env.py --config profiles/env.star.json
```

终端 3，启动模拟 AgentClient：

```bash
uv run python examples/star_agent_demo.py
```

模拟流程依次为：Agent 加入、工具发现、Step1、读取 Step1 报告、确认 Step1、
Step2、读取 Step2 报告、确认 Step2。Agent 端会打印四次完整 Action 信封、各自的
`action_id`、两个报告中的 `candidate_id` 和收到的完整 Outcome；
Agent 加入后还会先接收并打印 Env 单播的 `tools_discovered` 工具清单；Env 端会打印
工具清单发送记录和从 Hub 收到的 Action 信封。消息和实验输出保存在：

```text
data/star/
├── star-messages/
│   ├── agent_sent_{action_id}.json
│   ├── agent_received_tools_{agent_id}.json
│   ├── env_sent_tools_{agent_id}.json
│   ├── env_received_{action_id}.json
│   └── agent_received_{action_id}.json
├── actions/{action_id}/
│   ├── result.json
│   ├── data.csv
│   ├── plot.png
│   └── report.md
└── calibrations.json
```

当前不再保留绕过 Star 直接调用 Env 的独立实验示例。模拟 Agent 的请求统一由
`examples/star_agent_demo.py` 发送；当前流程覆盖 Step1/Step2 及两个候选结果的确认。

## 启动 WebUI 查询 API

```bash
uv run python scripts/run_env.py --config profiles/env.example.json
```

主要资源：

```text
GET /state
GET /agents
GET /tools
GET /actions
GET /actions/{action_id}
GET /actions/{action_id}/events
GET /calibrations
GET /files/{action_id}/report.md
GET /files/{action_id}/plot.png
```

普通配置中 Star 默认关闭；`profiles/env.star.json` 专门用于真实 Hub 联调。

进一步说明见 `docs/architecture.md`、`docs/id_contract.md` 和 `docs/matlab_mapping.md`。

## 知识手册与预设文档（人工维护）

`ReadKnowledge` / `GetPreset` 两个只读工具直接返回以下 Markdown 文件的全文；
文件缺失时返回"尚未填写"提示。内容由人类专家创建与维护，后期可由 Agent 维护。

- 知识手册：`{Env 数据目录}/knowledge/handbook.md`——建议结构：
  判据 / 初始参数与调参经验 / 常见问题。历史默认值（来自 MATLAB 源码，供 Agent
  首次调用参考）可参考下表：

  | 工具 | 参数 | 历史默认值 |
  |---|---|---|
  | MeasureReadoutFrequencyG / E | Readoutstep1 | 1e6 Hz |
  | MeasureReadoutFrequencyG | readout_amp / measuretime / waittime / expected_cycle_length | 4000 / 2000 ns / 100 ns / 200000 |
  | MeasureQubitFrequency | Qubitstep1 / amp180 / mysigma / coeff | 1e6 Hz / 700 / 20 ns / 30 |
  | MeasurePiPulseAmplitude | numstep / RabiStep | 41 / 350 |
  | MeasureT1 | numstep / timeStep | 41 / 5000 ns |
  | MeasureT2Star | numstep / timeStep | 81 / 2500 ns |
  | MeasureT2Echo | numstep / timeStep | 81 / 2000 ns |
  | MeasureSingleShotReadout | bin | 200 |

- 预设文档：`{Env 数据目录}/presets/{device_id}.md`——记录样品固有属性的预设范围
  （出厂先验，非标定结果），模板：

  ```markdown
  # 预设值：{device_id}（人工填写）

  | 步骤 | 标定目标 | 预设范围 | 单位 | 说明 |
  |---|---|---|---|---|
  | Step1 | readout.frequency.g | | Hz | 例：7.5e9 – 7.7e9 |
  | Step2 | qubit.frequency | | Hz | |
  | Step3 | qubit.pi_pulse.amplitude | | a.u. | |
  | Step4 | readout.frequency.e | | Hz | |
  | Step5 | qubit.t1 | | s | |
  | Step6 | qubit.t2 / qubit.t2_echo | | s | |
  | Step7 | readout.single_shot.threshold | | a.u. | |
  ```
