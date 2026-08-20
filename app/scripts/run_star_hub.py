"""Run the Star WebSocket Hub as an independent process."""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
from pathlib import Path
from typing import Any


async def run(host: str, port: int, message_dir: Path) -> None:
    try:
        from star_protocol.hub import HubServer
    except ImportError as exc:
        raise RuntimeError("请先按 README 安装项目固定的 star-protocol。") from exc

    hub = HubServer(host=host, port=port)
    _install_message_logger(hub, message_dir)
    _install_agent_left_notifier(hub)
    await hub.start()
    print(f"Star Hub is listening on ws://{host}:{port}", flush=True)
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for name in ("SIGINT", "SIGTERM"):
        if hasattr(signal, name):
            try:
                loop.add_signal_handler(getattr(signal, name), stop.set)
            except NotImplementedError:  # Windows
                pass
    try:
        await stop.wait()
    finally:
        await hub.stop()


def _install_message_logger(hub: Any, message_dir: Path) -> None:
    """Observe envelopes at the Hub routing boundary without changing routing."""
    original_route = hub.router.route_envelope

    async def route_and_log(envelope: Any, connection: Any) -> None:
        message_type = str(getattr(envelope.message, "message_type", "message"))
        if hasattr(envelope.message, "action"):
            label = "action"
        elif hasattr(envelope.message, "outcome"):
            label = "outcome"
        else:
            label = message_type.rsplit(".", 1)[-1].lower()
        rendered = json.dumps(envelope.to_dict(), ensure_ascii=False, indent=2)
        print(f"[Star Hub routing {label}]\n{rendered}", flush=True)
        action_id = str(getattr(envelope.message, "action_id", envelope.envelope_id))
        message_dir.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(char if char.isalnum() or char in "-_." else "_" for char in action_id)
        (message_dir / f"hub_routed_{label}_{safe_id}.json").write_text(
            rendered + "\n",
            encoding="utf-8",
        )
        await original_route(envelope, connection)

    hub.router.route_envelope = route_and_log


def _install_agent_left_notifier(hub: Any) -> None:
    """Notify an Agent's Environment after the Agent WebSocket closes."""
    from star_protocol.protocol import ClientType, Envelope, EnvelopeType, EventMessage

    original_add_connection = hub.connection_manager.add_connection
    original_handle_client = hub._handle_client
    client_info_by_socket: dict[int, Any] = {}

    def add_connection(websocket: Any, client_info: Any) -> bool:
        added = original_add_connection(websocket, client_info)
        if added:
            client_info_by_socket[id(websocket)] = client_info
        return added

    async def handle_client(websocket: Any) -> None:
        try:
            await original_handle_client(websocket)
        finally:
            client_info = client_info_by_socket.pop(id(websocket), None)
            if (
                client_info is not None
                and client_info.client_type == ClientType.AGENT
                and client_info.env_id
            ):
                env_connection = hub.connection_manager.get_connection(client_info.env_id)
                if env_connection is not None:
                    envelope = Envelope(
                        envelope_type=EnvelopeType.MESSAGE,
                        sender="hub",
                        recipient=client_info.env_id,
                        message=EventMessage(
                            event="agent_left",
                            data={"agent_id": client_info.client_id},
                        ),
                    )
                    await env_connection.send_envelope(envelope)

    hub.connection_manager.add_connection = add_connection
    hub._handle_client = handle_client


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--message-dir", type=Path, default=Path("data/star/star-messages"))
    arguments = parser.parse_args()
    try:
        asyncio.run(run(arguments.host, arguments.port, arguments.message_dir))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
