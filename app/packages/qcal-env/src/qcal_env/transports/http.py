"""Small HTTP surface for WebUI state and saved experiment resources."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from qcal_env.events import Broker
from qcal_env.runtime import CalibrationEnv


def create_app(
    env: CalibrationEnv,
    *,
    star_transport: Any | None = None,
    broker: Broker | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        del app
        task = asyncio.create_task(star_transport.run()) if star_transport else None
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="QCal Env", version="0.2.0", lifespan=lifespan)

    @app.get("/state")
    def state() -> dict[str, object]:
        return {
            "status": "ok",
            "backend_mode": env.backend_mode,
            "device_id": env.store.device_id,
            "qubit_id": env.store.qubit_id,
        }

    @app.get("/tools")
    def tools() -> dict[str, object]:
        return {"tools": env.public_tools}

    @app.get("/agents")
    def agents() -> dict[str, object]:
        if star_transport is None:
            return {"hub_connected": False, "agents": []}
        return {
            "hub_connected": star_transport.hub_connected,
            "agents": star_transport.connected_agent_list(),
        }

    @app.get("/actions")
    def actions() -> dict[str, object]:
        return {"actions": env.store.list_actions()}

    @app.get("/actions/{action_id}")
    def action(action_id: str) -> dict[str, object]:
        try:
            return env.store.get_action(action_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/actions/{action_id}/events")
    def action_events(action_id: str) -> dict[str, object]:
        try:
            return {
                "action_id": action_id,
                "events": env.store.get_action_events(action_id),
            }
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/calibrations")
    def calibrations() -> dict[str, object]:
        return env.store.calibrations()

    @app.get("/events")
    async def events() -> StreamingResponse:
        async def stream():
            # Ask the EventSource to auto-reconnect after a 2s gap.
            yield "retry: 2000\n\n"
            if broker is None:
                # No Star transport wired (manual mode): keep the connection
                # open but idle.
                while True:
                    yield ": ping\n\n"
                    await asyncio.sleep(15)
                return  # pragma: no cover
            async for event in broker.subscribe():
                if event is None:
                    yield ": ping\n\n"
                else:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/files/{action_id}/{filename:path}")
    def file(action_id: str, filename: str) -> FileResponse:
        action_dir = env.store.action_dir(action_id)
        path = (action_dir / filename).resolve()
        if action_dir not in path.parents or not path.is_file():
            raise HTTPException(status_code=404, detail="文件不存在。")
        return FileResponse(path, filename=Path(filename).name)

    return app
