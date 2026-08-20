FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

WORKDIR /app/app

COPY app/pyproject.toml app/uv.lock app/requirements.txt ./
COPY app/packages ./packages

RUN uv sync --frozen --all-packages --extra server --extra star \
    && uv pip install --python .venv/bin/python --no-deps \
      "git+https://github.com/GCYYfun/star-protocol.git@99a87c6b43bc4142fc50fba88c76bd32220927c8"

COPY app/profiles ./profiles
COPY app/scripts ./scripts

CMD [".venv/bin/python", "scripts/run_env.py", "--config", "profiles/env.docker.json"]
