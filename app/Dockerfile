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

WORKDIR /app/app

COPY app/pyproject.toml app/uv.lock app/requirements.txt ./
COPY app/packages ./packages

RUN uv sync --verbose --frozen --all-packages --extra server --extra star \
    && uv pip install --python .venv/bin/python --no-deps \
      "git+https://github.com/GCYYfun/star-protocol.git@99a87c6b43bc4142fc50fba88c76bd32220927c8"

COPY app/profiles ./profiles
COPY app/scripts ./scripts

CMD [".venv/bin/python", "scripts/run_env.py", "--config", "profiles/env.docker.json"]
