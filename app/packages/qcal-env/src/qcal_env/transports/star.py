"""Real Star WebSocket transport using the official repository's current API."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

from qcal_env.runtime import ActionContext, CalibrationEnv


EnvelopeHandler = Callable[[Any], Awaitable[dict[str, object]]]


class StarTransport:
    """Connect one CalibrationEnv to Hub and handle full Action envelopes."""

    def __init__(self, env: CalibrationEnv, client: Any, *, message_dir: str | Path | None = None) -> None:
        self.env = env
        self.client = client
        self.message_dir = Path(message_dir) if message_dir else env.store.root / "star-messages"
        self.connected_agents: dict[str, dict[str, object]] = {}

    @property
    def hub_connected(self) -> bool:
        return bool(getattr(self.client, "connected", False))

    def connected_agent_list(self) -> list[dict[str, object]]:
        return list(self.connected_agents.values()) if self.hub_connected else []

    def bind(self) -> None:
        self.client.qcal_action_receiver = self._handler
        self.client.event("agent_joined")(self._handle_agent_joined)
        self.client.event("agent_left")(self._handle_agent_left)

    async def _handle_agent_joined(self, message: Any) -> None:
        agent_id = (message.data or {}).get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            print("[QCal Env ignored invalid agent_joined event]", flush=True)
            return
        metadata = (message.data or {}).get("agent_metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        name = metadata.get("name")
        self.connected_agents[agent_id] = {
            "agent_id": agent_id,
            "name": name if isinstance(name, str) and name else agent_id,
            "connected_at": datetime.now(UTC).isoformat(),
            "metadata": metadata,
        }

        tools = self.env.public_tools
        await self.client.send_event(
            "tools_discovered",
            {"tools": tools},
            recipient=agent_id,
        )
        rendered = json.dumps(
            {"recipient": agent_id, "tools": tools},
            ensure_ascii=False,
            indent=2,
        )
        print(f"[QCal Env sent tools_discovered]\n{rendered}", flush=True)
        self.message_dir.mkdir(parents=True, exist_ok=True)
        (self.message_dir / f"env_sent_tools_{_safe_id(agent_id)}.json").write_text(
            rendered + "\n",
            encoding="utf-8",
        )

    async def _handle_agent_left(self, message: Any) -> None:
        agent_id = (message.data or {}).get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            self.connected_agents.pop(agent_id, None)
            print(f"[QCal Env agent left] {agent_id}", flush=True)

    async def _handler(self, envelope: Any) -> dict[str, object]:
        message = envelope.message
        action_name = str(message.action)
        action_id = str(message.action_id)
        agent_id = str(envelope.sender)
        parameters = dict(message.parameters or {})
        calibration_id = parameters.pop("calibration_id", None)
        if self.env.store.find_action(action_id) is None:
            self.env.store.append_action_event(
                action_id,
                "received",
                f"Env 收到 {action_name} Action",
                {
                    "action": action_name,
                    "agent_id": agent_id,
                    "calibration_id": calibration_id,
                },
            )
        if not isinstance(calibration_id, str) or not calibration_id:
            outcome = {"isError": True, "content": "Action 执行失败：parameters.calibration_id 必须是非空字符串。"}
            self.env.store.save_action(
                action_id,
                {
                    "action_id": action_id,
                    "calibration_id": calibration_id,
                    "agent_id": agent_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "name": action_name,
                    "experiment": action_name,
                    "backend_mode": self.env.backend_mode,
                    "status": "failed",
                    "inputs": parameters,
                    "request_inputs": parameters,
                    "error": outcome["content"],
                    "outcome": outcome,
                },
            )
            self.env.store.append_action_event(
                action_id,
                "failed",
                "Action 执行失败",
                {"error": outcome["content"]},
            )
            return outcome
        context = ActionContext(
            action_id=action_id,
            calibration_id=calibration_id,
            agent_id=agent_id,
        )

        full_message = envelope.to_dict()
        rendered = json.dumps(full_message, ensure_ascii=False, indent=2)
        print(f"[QCal Env received Star Action]\n{rendered}", flush=True)
        print(
            "[QCal Env parsed Action]\n"
            + json.dumps(
                {
                    "sender": agent_id,
                    "action_id": action_id,
                    "action": action_name,
                    "calibration_id": calibration_id,
                    "experiment_parameters": parameters,
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        self.message_dir.mkdir(parents=True, exist_ok=True)
        (self.message_dir / f"env_received_{_safe_id(action_id)}.json").write_text(
            rendered + "\n",
            encoding="utf-8",
        )
        result = await asyncio.to_thread(
            self.env.handle_action,
            action_name,
            parameters,
            context,
        )
        result_rendered = json.dumps(result, ensure_ascii=False, indent=2)
        print(f"[QCal Env completed Action]\n{result_rendered}", flush=True)
        (self.message_dir / f"env_result_{_safe_id(action_id)}.json").write_text(
            result_rendered + "\n",
            encoding="utf-8",
        )
        return result

    async def run(self) -> None:
        self.bind()
        await self.client.connect()
        heartbeat_task = asyncio.create_task(self._send_heartbeats())
        try:
            await asyncio.Event().wait()
        finally:
            heartbeat_task.cancel()
            await _close_client(self.client)

    async def _send_heartbeats(self) -> None:
        """定期向 Hub 发送心跳，避免空闲时被 Hub 判定超时断开。"""
        from star_protocol.protocol import Envelope, EnvelopeType, HeartbeatInfo

        while True:
            await asyncio.sleep(30)
            try:
                if not getattr(self.client, "connected", False):
                    return
                envelope = Envelope(
                    envelope_type=EnvelopeType.HEARTBEAT,
                    sender=self.client.client_id,
                    recipient="hub",
                    message=HeartbeatInfo(status="alive"),
                )
                await self.client.send_envelope(envelope)
            except Exception:
                pass


def create_star_environment_client(
    server_url: str,
    env_id: str,
    *,
    metadata: dict[str, object] | None = None,
):
    try:
        from star_protocol.client import EnvironmentClient
        from star_protocol.protocol import OutcomeMessage
    except ImportError as exc:  # pragma: no cover - installation error
        raise RuntimeError("请先按 README 安装项目固定的 star-protocol。") from exc

    class QCalEnvironmentClient(EnvironmentClient):
        qcal_action_receiver: EnvelopeHandler | None = None

        async def on_action(self, envelope: Any) -> None:
            message = envelope.message
            if self.qcal_action_receiver is None:
                result: dict[str, object] = {"isError": True, "content": "Action 执行失败：Env 尚未绑定 Action handler。"}
            else:
                try:
                    result = await self.qcal_action_receiver(envelope)
                except Exception as exc:  # transport-level failure
                    result = {"isError": True, "content": f"Action 执行失败：{exc}"}
            outcome = OutcomeMessage(
                outcome=message.action,
                action_id=message.action_id,
                data=result,
            )
            await self.send_message(outcome, envelope.sender)

    # The current official source uses hub_url, not the README's server_url.
    return QCalEnvironmentClient(env_id=env_id, hub_url=server_url, metadata=metadata)


async def _close_client(client: Any) -> None:
    """Close the SDK socket directly; its current disconnect() calls a missing context.stop()."""
    websocket = getattr(client, "websocket", None)
    if websocket is not None:
        await websocket.close()
    client.connected = False
    client.websocket = None


def _safe_id(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_." else "_" for char in value)
