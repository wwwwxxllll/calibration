# QCal Dashboard 前端

Vue 3 + Vite + Element Plus 实现的量子校准监控面板，对接 `qcal-env` 的 WebUI 只读接口。

## 技术栈

- Vue 3（Composition API + `<script setup>`）
- Vite（开发服务器 + proxy）
- Element Plus（表格、标签、描述列表、时间线）

## 对接的后端接口

| 前端调用 | 后端端点 | 用途 | 轮询 |
|---------|---------|------|------|
| `api.getState()` | `GET /state` | Env 状态 | 一次性 |
| `api.getAgents()` | `GET /agents` | 在线 Agent | 每 1.5s |
| `api.getTools()` | `GET /tools` | 工具清单 | 一次性 |
| `api.getActions()` | `GET /actions` | Action 历史 | 一次性 |
| `api.getAction(id)` | `GET /actions/{id}` | Action 详情 | 选中时 |
| `api.getActionEvents(id)` | `GET /actions/{id}/events` | 执行时间线 | 每 800ms，遇 completed/failed 停止 |
| `api.getCalibrations()` | `GET /calibrations` | 候选值 + 已确认标定 | 一次性 |

## 设计约束

- **前端是纯只读监控**，不通过 HTTP 绕过 Star 发起实验。实验必须走 `AgentClient → Star Hub → QCal Env`。
- 产物地址（`artifacts.plot` 等）是相对路径，前端直接使用（经 Vite proxy 同源转发）。
- `/agents` 和 `/actions/{id}/events` 若后端尚未实现，前端会静默降级（显示空态），不影响其他功能。

## 运行

```bash
# 1. 先启动后端（另开终端）
uv run python scripts/run_env.py --config profiles/env.example.json

# 2. 安装前端依赖并启动
cd web
npm install
npm run dev
```

前端默认跑在 `http://127.0.0.1:5173`，通过 Vite proxy 把 `/state`、`/agents`、`/actions` 等请求转发到后端 `http://127.0.0.1:8000`。

## 目录结构

```
web/
├── index.html
├── package.json
├── vite.config.js          # proxy 配置
└── src/
    ├── main.js             # 入口，注册 Element Plus
    ├── App.vue             # 主布局 + 数据加载 + 轮询 + 按 calibration_id 分组
    ├── api/client.js       # 后端 API 客户端
    ├── utils/format.js     # 格式化工具
    └── components/
        ├── StepTimeline.vue     # 顶部横向 step1-7 校准流程时间线
        ├── ActionList.vue       # Action 历史（当前校准 / 历史校准折叠）
        ├── ActionDetail.vue     # Action 详情（拟合 + 候选值 / 实验参数 / 产物 / Outcome）
        ├── EventTimeline.vue    # 执行事件时间线（横向）
        ├── AgentPanel.vue       # 顶栏在线 Agent 徽章 + 下拉
        ├── ToolPanel.vue        # 工具清单（可折叠）
        └── CalibrationPanel.vue # 已确认标定 + 候选值（可折叠）
```
