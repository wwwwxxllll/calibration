FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple

RUN sed -i \
    -e 's|http://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
    -e 's|https://deb.debian.org/debian|https://mirrors.aliyun.com/debian|g' \
    /etc/apt/sources.list.d/debian.sources

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir \
      -i https://pypi.tuna.tsinghua.edu.cn/simple/ uv

WORKDIR /app/agent

RUN uv venv --python 3.13 .venv \
    && uv pip install --python .venv/bin/python \
      "git+https://github.com/GCYYfun/MengLong.git@fe999c4c56be122072164b0015abf920e476a570" \
    && uv pip install --python .venv/bin/python --no-deps \
      "git+https://github.com/GCYYfun/star-protocol.git@99a87c6b43bc4142fc50fba88c76bd32220927c8"

COPY agent/calibration_agent.py agent/configs.example.toml ./

ENTRYPOINT [".venv/bin/python", "calibration_agent.py"]
