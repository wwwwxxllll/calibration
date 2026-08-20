# QCal Agent（独立项目）

真实 LLM 校准 Agent：连接 Star Hub 与 Env，自动发现 Env 工具，驱动模型完成
Step1–Step7 校准（实验 → read_file → confirm_calibration → 下一步）。

本分支只包含 Agent 项目本身，与 Env/Backend 项目解耦；依赖仅 `menglong` 与
`star-protocol`。

## 依赖安装

```bash
uv pip install "git+https://github.com/GCYYfun/MengLong.git@fe999c4c56be122072164b0015abf920e476a570"
uv pip install --no-deps \
  "git+https://github.com/GCYYfun/star-protocol.git@99a87c6b43bc4142fc50fba88c76bd32220927c8"
```

注意：star-protocol 官方仓库的 pyproject 在 `[tool.uv.sources]` 里把
`menglong` 声明为 `{ path = "../MengLong" }`（作者本地目录布局），从 git
安装时 uv 会把它改写为仓库内不存在的子目录而失败，因此必须单独安装
menglong，并给 star-protocol 加 `--no-deps` 跳过其依赖解析（与
根目录 README 相同的处理方式）。

## 配置

```bash
cp configs.example.toml configs.toml   # 填入真实凭据；configs.toml 已被 .gitignore 排除
```

## 本地检查（不联网）

```bash
python -m pytest tests -q
```

## 真实运行

先启动 Star Hub 与 Env（见 `app/scripts/`），然后：

```bash
python calibration_agent.py \
  --config configs.toml \
  --server-url ws://127.0.0.1:8765 \
  --env-id qcal-env \
  --model deepseek/deepseek-v4-flash \
  --max-rounds 120 \
  --max-actions 120 \
  "帮我校准"
```
