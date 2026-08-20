"""Start the simplified calibration Env."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from qcal_env import CalibrationEnv, FileStore, TOOL_DEFINITIONS
from qcal_env.transports import StarTransport, create_app, create_star_environment_client
from qcal_hardware_backend import HardwareAdapter
from qcal_qutip_backend import QuTiPAdapter


@dataclass
class AppConfig:
    backend_mode: str
    device_id: str
    qubit_id: str
    data_root: Path
    qutip_profile_path: Path
    http_host: str
    http_port: int
    star_enabled: bool
    star_server_url: str
    star_env_id: str


def load_app_config(path: str | Path, *, backend_override: str | None = None) -> AppConfig:
    config_path = Path(path).resolve()
    value = json.loads(config_path.read_text(encoding="utf-8"))
    base = config_path.parent

    def relative(raw: str) -> Path:
        candidate = Path(raw)
        return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()

    mode = backend_override or str(value.get("backend_mode", "qutip"))
    if mode not in {"qutip", "hardware"}:
        raise ValueError("backend_mode 只支持 qutip 或 hardware。")
    http = value.get("http", {})
    star = value.get("star", {})
    # Accept the local manual config created before this simplification without
    # retaining the former SQLite runtime.
    legacy_storage = value.get("storage", {})
    legacy_qutip = value.get("qutip", {})
    data_root_value = value.get("data_root", legacy_storage.get("artifact_root", "../data"))
    profile_value = value.get("qutip_profile_path", legacy_qutip.get("device_profile_path", "default.json"))
    return AppConfig(
        backend_mode=mode,
        device_id=str(value.get("device_id", "virtual_device_A")),
        qubit_id=str(value.get("qubit_id", "q0")),
        data_root=relative(str(data_root_value)),
        qutip_profile_path=relative(str(profile_value)),
        http_host=str(http.get("host", "127.0.0.1")),
        http_port=int(http.get("port", 8000)),
        star_enabled=bool(star.get("enabled", False)),
        star_server_url=str(star.get("server_url", star.get("hub_url", "ws://127.0.0.1:8765"))),
        star_env_id=str(star.get("env_id", "qcal-env")),
    )


def build_env(config: AppConfig) -> CalibrationEnv:
    if config.backend_mode == "qutip":
        # The adapter, not Env, reads and owns DeviceProfile truth.
        adapter = QuTiPAdapter.from_config(config.qutip_profile_path)
    else:
        adapter = HardwareAdapter()
    store = FileStore(
        config.data_root,
        device_id=config.device_id,
        qubit_id=config.qubit_id,
    )
    return CalibrationEnv(adapter=adapter, store=store, backend_mode=config.backend_mode)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("profiles/env.example.json"))
    parser.add_argument("--backend-mode", choices=("qutip", "hardware"))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--print-tools", action="store_true")
    arguments = parser.parse_args()

    if arguments.print_tools:
        public = [{key: value for key, value in item.items() if key != "handler"} for item in TOOL_DEFINITIONS]
        print(json.dumps(public, ensure_ascii=False, indent=2))
        return

    config = load_app_config(arguments.config, backend_override=arguments.backend_mode)
    env = build_env(config)
    if arguments.check:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "backend_mode": config.backend_mode,
                    "device_id": config.device_id,
                    "qubit_id": config.qubit_id,
                    "tools": [item["name"] for item in TOOL_DEFINITIONS],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    star_transport = None
    if config.star_enabled:
        client = create_star_environment_client(
            config.star_server_url,
            config.star_env_id,
            metadata={"mode": env.backend_mode, "tools": env.public_tools},
        )
        star_transport = StarTransport(env, client)
    app = create_app(env, star_transport=star_transport)

    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("请安装 qcal-env[server] 后启动 HTTP 服务。") from exc
    uvicorn.run(app, host=config.http_host, port=config.http_port)


if __name__ == "__main__":
    main()
