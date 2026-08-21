# QCal 量子校准系统

本项目包含量子校准后端（Env）、Star Hub、校准 Agent 和 Web 监控前端。

## 项目结构

```text
calibration/
├── app/       # QCal Env、QuTiP 虚拟设备、Star Hub 和 HTTP API
├── agent/     # 基于大模型的自动校准 Agent
├── web/       # Vue 3 校准监控页面
└── README.md  # 总体安装与启动说明
```

## 运行环境

请先安装：

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- Node.js 18+ 和 npm

检查版本：

```bash
python3 --version
uv --version
node --version
npm --version
```

## 首次安装

以下每个代码块均以项目根目录 `calibration/` 为起点。如果终端提示符已经显示在
`app`、`web` 或 `agent` 目录中，请不要重复执行对应的 `cd` 命令。

后端和 Agent 使用两个相互独立的虚拟环境：

- `app/.venv`：运行 Star Hub 和 QCal Env
- `agent/.venv`：运行校准 Agent

安装某个组件时，不要激活另一个组件的虚拟环境。如果终端提示符前已经出现
`(agent)`、`(.venv)` 等环境名称，可先执行 `deactivate`。

### 1. 安装后端依赖

```bash
cd app
uv sync --all-packages --extra server --extra star
uv pip install --python .venv/bin/python --no-deps \
  "git+https://github.com/GCYYfun/star-protocol.git@99a87c6b43bc4142fc50fba88c76bd32220927c8"
```

验证 `star-protocol` 已安装到后端环境：

```bash
cd app
uv run python -c "import star_protocol; print(star_protocol.__file__)"
```

### 2. 安装前端依赖

```bash
cd web
npm install
```

### 3. 配置 Agent

复制 Agent 配置模板：

```bash
cd agent
cp configs.example.toml configs.toml
uv venv --python 3.13 .venv
```

打开 `agent/configs.toml`，填写需要使用的模型及其 API Key。真实密钥不要提交到 Git。

Agent 依赖需要安装到运行 Agent 所使用的 Python 环境中：

```bash
cd agent
uv pip install --python .venv/bin/python \
  "git+https://github.com/GCYYfun/MengLong.git@fe999c4c56be122072164b0015abf920e476a570"
uv pip install --python .venv/bin/python --no-deps \
  "git+https://github.com/GCYYfun/star-protocol.git@99a87c6b43bc4142fc50fba88c76bd32220927c8"
```

这里显式指定 `.venv/bin/python`，可以避免依赖被误装到后端环境或系统 Python。

## 完整启动：Hub + Env + Agent + 前端

完整流程需要打开四个终端，并严格按照下面的顺序启动。

### 终端 1：启动 Star Hub

```bash
cd app
uv run python scripts/run_star_hub.py
```

Star Hub 默认监听：`ws://127.0.0.1:8765`

### 终端 2：启动 QCal Env

```bash
cd app
uv run python scripts/run_env.py --config profiles/env.star.json
```

该配置会同时：

- 连接 Star Hub
- 启动 QuTiP 虚拟设备
- 提供 `http://127.0.0.1:8000` 查询接口

看到 Env 成功连接 Hub 后，再启动 Agent。

### 终端 3：启动校准 Agent

```bash
cd agent
.venv/bin/python calibration_agent.py \
  --config configs.toml \
  --server-url ws://127.0.0.1:8765 \
  --env-id qcal-env \
  --model deepseek/deepseek-v4-flash \
  --max-rounds 120 \
  --max-actions 120 \
  "帮我校准"
```

请把 `--model` 改成 `agent/configs.toml` 中已配置并可用的模型。

### 终端 4：启动监控前端

```bash
cd web
npm run dev
```

浏览器打开：<http://127.0.0.1:5173>

## 启动关系

```text
校准 Agent ──WebSocket──> Star Hub ──WebSocket──> QCal Env
                                                    │
                                                    ├── QuTiP 虚拟设备
                                                    └── HTTP API :8000
                                                              │
                                                              v
                                                        Web 前端 :5173
```

前端只负责查看状态和实验结果，不会直接发起校准实验。实验请求必须由 Agent 经过 Star Hub 发送给 Env。

## Docker Compose 部署

Docker 部署包含以下服务：

- `star-hub`：容器内部端口 `8765`
- `qcal-env`：容器内部端口 `8000`
- `frontend`：Web 容器服务，容器端口 `80` 映射到服务器端口 `3001`
- `agent`：按需运行，不长期驻留

只有前端的 `3001` 端口暴露给外部。后端和 Hub 仅通过 Docker 内部网络通信。

所有命令都在项目根目录执行：

```bash
cd /path/to/calibration
```

### 一、首次准备

首次部署前，请先确认服务器已经安装 Docker Engine 和 Docker Compose。

#### 1. 准备 Agent 配置

如果还没有配置文件：

```bash
cp agent/configs.example.toml agent/configs.toml
```

填写 `agent/configs.toml` 中对应模型的 API Key。真实密钥不要提交到 Git。

#### 2. 创建数据目录

```bash
mkdir -p deploy-data
```

实验结果和校准数据会保存在这里。

#### 3. 构建全部镜像

```bash
docker compose --profile agent build
```

只有首次部署，或代码、依赖发生变化时需要重新构建。

### 二、日常运行

#### 1. 启动基础服务

```bash
docker compose up -d star-hub qcal-env frontend
```

启动顺序由 Compose 自动处理：

```text
Star Hub
   ↓
QCal Env
   ↓
Web 前端
```

等待约 20 秒，然后检查：

```bash
docker compose ps
```

预期状态：

```text
star-hub   healthy
qcal-env   healthy
web        running
```

本机打开前端：

<http://127.0.0.1:3001>

部署到公网服务器后，也可以使用服务器 IP 访问，例如：

<http://8.145.32.114:3001>

服务器的云安全组和系统防火墙需要放行 TCP `3001`。不需要对公网开放 `8000` 和
`8765`。

此时没有 Action 是正常的，因为 Agent 尚未发送校准任务。

#### 2. 运行校准 Agent

基础服务健康后，按需执行 Agent。使用默认请求“帮我校准”：

```bash
docker compose --profile agent run --rm agent
```

临时更换模型或请求内容：

```bash
QCAL_MODEL=deepseek/deepseek-v4-flash \
QCAL_REQUEST="帮我校准" \
docker compose --profile agent run --rm agent
```

内部通信关系是：

```text
Agent
  ↓ ws://star-hub:8765
Star Hub
  ↓
QCal Env
  ↓
生成 Action、报告、CSV、图片和校准结果
```

Agent 是一次性任务容器：

- 启动后执行校准
- 完成后自动退出
- `--rm` 会删除已经退出的 Agent 容器
- 实验数据不会删除

如果 Agent 配置文件不在默认的 `agent/configs.toml`，可以指定路径：

```bash
AGENT_CONFIG_PATH=./secrets/configs.toml \
docker compose --profile agent run --rm agent
```

#### 3. 查看执行情况

Agent 当前终端会显示大模型和工具调用过程。

另开终端查看后端日志：

```bash
docker compose logs -f star-hub qcal-env
```

回到浏览器刷新页面：

<http://127.0.0.1:3001>

即可查看：

- Action 列表
- Agent 状态
- 执行时间线
- I/Q 曲线
- 候选校准值
- 已确认的校准结果

前端可能不会自动加载新产生的 Action，因此 Agent 开始运行后建议手动刷新一次浏览器。

#### 4. 查看数据文件

宿主机数据位置：

```text
deploy-data/star/
├── star-messages/
├── actions/
├── calibrations.json
├── knowledge/
└── presets/
```

这些数据独立于容器。停止或重新构建容器后仍然保留。

#### 5. 停止和重新启动

停止基础服务：

```bash
docker compose down
```

之后重新启动：

```bash
docker compose up -d star-hub qcal-env frontend
```

再次发起校准：

```bash
docker compose --profile agent run --rm agent
```

不要执行：

```bash
docker compose down -v
```

虽然当前主要使用宿主机目录持久化，但仍不建议使用带 `-v` 的清理命令。

#### 6. 修改代码后的流程

修改后端、前端或 Agent 代码后：

```bash
docker compose --profile agent build
docker compose up -d star-hub qcal-env frontend
docker compose --profile agent run --rm agent
```

日常最常用的一套命令就是：

```bash
cd /path/to/calibration
docker compose up -d star-hub qcal-env frontend
docker compose --profile agent run --rm agent
```

然后访问：

<http://127.0.0.1:3001>

## 数据输出

完整 Star 流程的数据默认保存在：

```text
app/data/star/
├── star-messages/            # Agent、Hub 和 Env 的消息记录
├── actions/{action_id}/      # 单次实验结果
│   ├── result.json
│   ├── data.csv
│   ├── plot.png
│   └── report.md
└── calibrations.json         # 已确认的校准结果
```

## 常用检查命令

检查后端配置及工具：

```bash
cd app
uv run python scripts/run_env.py --config profiles/env.star.json --check
uv run python scripts/run_env.py --config profiles/env.star.json --print-tools
```

运行后端测试：

```bash
cd app
uv run pytest -q
```

构建前端：

```bash
cd web
npm run build
```

## 常见问题

### 打开文件后没有“运行”按钮

本项目由多个服务组成，不能通过运行 `README.md`、`.vue` 或 `.json` 文件启动。请在终端中使用本说明提供的命令。Python 入口文件主要是：

- `app/scripts/run_star_hub.py`
- `app/scripts/run_env.py`
- `agent/calibration_agent.py`

### 前端页面没有数据

确认后端正在监听 `127.0.0.1:8000`。如果要查看 Agent 的实时校准流程，应使用 `app/profiles/env.star.json` 启动 Env，并同时启动 Hub 和 Agent。

### Agent 无法连接

依次检查：

1. Star Hub 是否已启动并监听 `127.0.0.1:8765`。
2. Env 是否使用 `app/profiles/env.star.json` 启动。
3. Agent 和 Env 的 `server-url` 是否一致。
4. Agent 的 `env-id` 是否为 `qcal-env`。

### 出现 `VIRTUAL_ENV ... does not match` 或 `No module named 'star_protocol'`

这通常表示当前激活了 `agent/.venv`，但正在安装或运行后端。先退出当前环境，
再把 `star-protocol` 明确安装到后端环境：

```bash
deactivate
cd app
uv sync --all-packages --extra server --extra star
uv pip install --python .venv/bin/python --no-deps \
  "git+https://github.com/GCYYfun/star-protocol.git@99a87c6b43bc4142fc50fba88c76bd32220927c8"
uv run python -c "import star_protocol; print(star_protocol.__file__)"
```

如果当前本来就没有激活虚拟环境，`deactivate` 命令不存在，可以直接从 `cd app`
开始。若终端已经位于 `app`，则不要再次执行 `cd app`。

### 端口被占用

默认端口：

- Star Hub：`8765`
- 后端 HTTP API：`8000`
- 前端 Vite：`5173`

先停止占用相应端口的旧进程，再重新启动服务。

## 停止服务

在各个运行服务的终端中按 `Ctrl+C`。建议按照 Agent、前端、Env、Hub 的顺序停止。

更多实现细节参见：

- `app/README.md`
- `agent/README.md`
- `web/README.md`

## 八、报错解决
- `docker pull python:3.13-slim`
- `docker pull node:20-alpine`
- `docker pull nginx:1.27-alpine`