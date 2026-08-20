#!/usr/bin/env python3
"""LLM-driven quantum calibration Agent using Generator and Star Env tools.

One user request owns one calibration_id for the complete calibration. Env tools
are discovered after the Star connection and are executed as Generator external
tools. The model, rather than Python branching code, decides whether to retry a
step, advance to the next step, or call Finish.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import math
import os
import re
import tomllib
import uuid
from collections.abc import Set as AbstractSet
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence

from menglong.schemas.chat import (
    Action,
    Assistant,
    Context,
    Response,
)
from menglong.schemas.tool import FunctionInfo, ToolInfo


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs.toml"
FINISH_TOOL_NAME = "Finish"
TOOL_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


ToolFunction = Callable[..., Any]


class ModelClient(Protocol):
    """Minimal model interface required by :class:`Generator`."""

    def chat(
        self,
        *,
        messages: Context,
        model: str | None,
        tools: Sequence[ToolFunction],
    ) -> Response: ...


class ToolRuntime(Protocol):
    """Tool registry boundary used by :class:`Generator`."""

    @property
    def tools(self) -> Sequence[ToolFunction]: ...

    @property
    def names(self) -> AbstractSet[str]: ...


class GeneratorError(RuntimeError):
    """Base exception raised by the model loop."""


class LoopPhase(str, Enum):
    """Generator 对外可见的三种状态。"""

    READY = "ready"
    WAITING_RESULT = "waiting_result"
    COMPLETED = "completed"


class EventKind(str, Enum):
    MODEL_CALL_STARTED = "model_call_started"
    EXTERNAL_RESULT_REQUIRED = "external_result_required"
    ERROR = "error"


@dataclass(slots=True)
class CalibrationMessage:
    """State belonging to one complete user calibration request."""

    calibration_id: str
    user_request: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    discovered_tools: list[dict[str, Any]] = field(default_factory=list)
    action_count: int = 0
    attempts: Counter[str] = field(default_factory=Counter)
    action_log: list[dict[str, Any]] = field(default_factory=list)
    status: str = "created"
    final_answer: str | None = None
    end_reason: str | None = None
    # 同一工具连续调用计数：换工具或 confirm 成功后由 Python 重置
    last_tool: str | None = None
    tool_streak: int = 0

    @classmethod
    def create(cls, user_request: str) -> "CalibrationMessage":
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        suffix = uuid.uuid4().hex[:8]
        return cls(
            calibration_id=f"cal_{timestamp}_{suffix}",
            user_request=user_request,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "user_request": self.user_request,
            "created_at": self.created_at,
            "discovered_tool_names": [
                tool.get("name") for tool in self.discovered_tools
            ],
            "action_count": self.action_count,
            "attempts": dict(self.attempts),
            "action_log": self.action_log,
            "status": self.status,
            "final_answer": self.final_answer,
            "end_reason": self.end_reason,
            "last_tool": self.last_tool,
            "tool_streak": self.tool_streak,
        }


class StarEnvToolRuntime:
    """Generator ToolRuntime whose Env tools are all externally executed."""

    def __init__(self, tools: Sequence[Callable[..., Any]]) -> None:
        self.tools = list(tools)
        names = [
            getattr(item, "__name__", None)
            or getattr(getattr(item, "function", None), "name", "")
            for item in self.tools
        ]
        if any(not name for name in names):
            raise TypeError("all model tools must have a name")
        if len(set(names)) != len(names):
            raise ValueError("duplicate model tool names")
        self._names = frozenset(names)

    @property
    def names(self) -> frozenset[str]:
        return self._names


@dataclass(frozen=True, slots=True)
class CalibrationRunResult:
    calibration_id: str
    status: str
    final_answer: str
    action_count: int
    attempts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "calibration_id": self.calibration_id,
            "status": self.status,
            "final_answer": self.final_answer,
            "action_count": self.action_count,
            "attempts": self.attempts,
        }


@dataclass(slots=True)
class ToolLoopState:
    """Runtime state owned by :class:`Generator`."""

    context: Context
    phase: LoopPhase = LoopPhase.READY
    round_number: int = 0
    active_calls: list[Action] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ToolLoopEvent:
    """One structured event emitted while the Generator is running."""

    kind: EventKind
    round_number: int
    text: str | None = None
    tool_call: Action | None = None


class EventSink(Protocol):
    """Observer interface for generator events."""

    def __call__(self, event: ToolLoopEvent) -> None: ...


class Generator:
    """Model loop that yields external tool calls to the caller.

    每次 run() 推进到：等待外部工具结果（返回 None，调用方通过
    find_waiting_call 取得调用、自行执行并 submit_tool_result 回灌），
    或模型给出最终回复（返回 Response）。工具一律由外部执行。
    """

    def __init__(
        self,
        model: ModelClient,
        context: Context,
        *,
        model_id: str | None = None,
        max_rounds: int = 8,
        on_event: EventSink | None = None,
        external_tools: Sequence[str] = (),
        tool_runtime: ToolRuntime,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")
        if not callable(getattr(model, "chat", None)):
            raise TypeError("model must implement chat()")
        if on_event is not None and not callable(on_event):
            raise TypeError("on_event must implement EventSink.__call__()")
        for attribute in ("tools", "names"):
            if not hasattr(tool_runtime, attribute):
                raise TypeError(f"tool_runtime must provide {attribute!r}")

        self.model = model
        self.tool_runtime = tool_runtime
        self.tools = list(self.tool_runtime.tools)
        self.model_id = model_id
        self.max_rounds = max_rounds
        self.on_event = on_event
        self.external_tools = set(external_tools)

        unknown_external_tools = self.external_tools.difference(self.tool_runtime.names)
        if unknown_external_tools:
            names = ", ".join(sorted(unknown_external_tools))
            raise ValueError(f"external tools are not registered: {names}")

        self.state = ToolLoopState(context=context)

    @property
    def context(self) -> Context:
        return self.state.context

    def _emit(
        self,
        kind: EventKind,
        *,
        text: str | None = None,
        tool_call: Action | None = None,
    ) -> None:
        if self.on_event:
            self.on_event(
                ToolLoopEvent(
                    kind=kind,
                    round_number=self.state.round_number,
                    text=text,
                    tool_call=tool_call,
                )
            )

    def run(self) -> Response | None:
        """推进到等待外部工具结果（返回 None）或模型给出最终回复。"""
        while True:
            if self.state.active_calls:
                # 上一轮模型产生了多个工具调用：继续等待下一个的结果
                self.state.phase = LoopPhase.WAITING_RESULT
                self._emit(
                    EventKind.EXTERNAL_RESULT_REQUIRED,
                    tool_call=self.state.active_calls[0],
                )
                return None

            if self.state.round_number >= self.max_rounds:
                raise GeneratorError(
                    f"generator exceeded max_rounds={self.max_rounds}; "
                    "the last model response still requested tools"
                )
            self.state.round_number += 1
            self._emit(EventKind.MODEL_CALL_STARTED)
            try:
                # 调用LLM
                response = self.model.chat(
                    messages=self.context,
                    model=self.model_id,
                    tools=self.tools,
                )
            except Exception as error:
                self._emit(EventKind.ERROR, text=f"{type(error).__name__}: {error}")
                raise
            # 直接把模型恢复加入上下文
            self.context.add(Assistant(response))

            tool_calls = response.tool_calls or []
            unknown = [
                call.name
                for call in tool_calls
                if call.name not in self.external_tools
            ]
            if unknown:
                raise GeneratorError(
                    "model called tools not registered as external: "
                    + ", ".join(unknown)
                )

            if tool_calls:
                self.state.active_calls = list(tool_calls)
                self.state.phase = LoopPhase.WAITING_RESULT
                self._emit(
                    EventKind.EXTERNAL_RESULT_REQUIRED,
                    tool_call=self.state.active_calls[0],
                )
                return None

            self.state.phase = LoopPhase.COMPLETED
            return response

    def _find_waiting_call(self, tool_call_id: Any | None = None) -> Action:
        waiting = self.state.active_calls
        if tool_call_id is not None:
            waiting = [call for call in waiting if call.id == tool_call_id]
        if len(waiting) != 1:
            raise GeneratorError("exactly one matching waiting tool call is required")
        return waiting[0]

    def submit_tool_result(
        self,
        result: Any,
        tool_call_id: Any | None = None,
        *,
        is_error: bool = False,
    ) -> None:
        """回灌一个外部工具的执行结果；随后可再次 run() 推进。"""
        if self.state.phase != LoopPhase.WAITING_RESULT:
            raise GeneratorError("generator is not waiting for an external result")
        call = self._find_waiting_call(tool_call_id)
        if is_error:
            error_text = (
                f"{type(result).__name__}: {result}"
                if isinstance(result, Exception)
                else str(result)
            )
            outcome = {"ok": False, "error": error_text}
        else:
            json.dumps(result, ensure_ascii=False)
            outcome = {"ok": True, "result": result}
        self.context.tool(
            tool_id=call.id,
            name=call.name,
            content=json.dumps(outcome, ensure_ascii=False),
        )
        self.state.active_calls.remove(call)
        self.state.phase = LoopPhase.READY


class CalibrationAgent:
    """Coordinate model decisions with dynamically discovered Star Env tools."""

    def __init__(
        self,
        *,
        server_url: str,
        env_id: str,
        agent_id: str,
        config_path: Path = DEFAULT_CONFIG_PATH,
        model_id: str | None = None,
        discovery_timeout: float = 15.0,
        action_timeout: float = 600.0,
        max_rounds: int = 120,
        max_actions: int = 120,
        max_tool_attempts: int = 3,
    ) -> None:
        if max_rounds < 1 or max_actions < 1 or max_tool_attempts < 1:
            raise ValueError("max_rounds, max_actions and max_tool_attempts must be positive")
        if discovery_timeout <= 0 or action_timeout <= 0:
            raise ValueError("timeouts must be positive")
        self.server_url = server_url
        self.env_id = env_id
        self.agent_id = agent_id
        self.config_path = config_path.expanduser().resolve()
        self.model_id = model_id
        self.discovery_timeout = discovery_timeout
        self.action_timeout = action_timeout
        self.max_rounds = max_rounds
        self.max_actions = max_actions
        self.max_tool_attempts = max_tool_attempts

    # 核心运行方法
    async def run(self, user_request: str) -> CalibrationRunResult:
        if not user_request.strip():
            raise ValueError("user_request must not be empty")

        message = CalibrationMessage.create(user_request.strip())
        message.status = "connecting"
        self._log("session_started", calibration_id=message.calibration_id)

        client, discovery_event, discovered_tools = self._create_star_client()
        heartbeat_task: asyncio.Task[Any] | None = None
        try:
            await client.connect() # 连接Hub
            heartbeat_task = asyncio.create_task(self._send_heartbeats(client))
            try:
                await asyncio.wait_for(
                    discovery_event.wait(), timeout=self.discovery_timeout
                )
            except asyncio.TimeoutError as exc:
                message.status = "failed"
                message.end_reason = "tool_discovery_timeout"
                raise RuntimeError(
                    f"在 {self.discovery_timeout:g} 秒内没有收到 Env 工具清单。"
                    f"请确认 Env {self.env_id!r} 已连接到 {self.server_url!r}，"
                    "并且 Agent 的 --env-id 与 Env ID 完全一致。"
                ) from exc
            # 把创建AgentClient时得到的tool list校验处理后加入message
            message.discovered_tools = validate_discovered_tools(discovered_tools)
            message.status = "running"
            self._log(
                "tools_discovered",
                tools=[tool["name"] for tool in message.discovered_tools],
            )

            configure_menglong(self.config_path)
            model, context, decorated_tools = self._build_model_inputs(message)
            runtime = StarEnvToolRuntime(decorated_tools)
            external_names = [tool["name"] for tool in message.discovered_tools]
            external_names.append(FINISH_TOOL_NAME)
            generator = Generator(
                model=model,
                context=context,
                model_id=self.model_id or read_default_model_id(self.config_path),
                max_rounds=self.max_rounds,
                tool_runtime=runtime,
                external_tools=external_names,
                on_event=self._generator_event_logger(),
            )
            return await self._drive_generator(
                generator=generator,
                client=client,
                message=message,
            )
        except Exception as exc:
            if message.status != "completed":
                message.status = "failed"
                message.end_reason = message.end_reason or type(exc).__name__
            raise
        finally:
            if heartbeat_task is not None:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except Exception:
                    pass
            await close_star_client(client)
            self._log("session_closed", **message.snapshot())

    @staticmethod
    async def _send_heartbeats(client: Any) -> None:
        """定期向 Hub 发送心跳，避免等待长实验时被 Hub 判定超时断开。

        Hub 每 60 秒检查一次、120 秒无心跳即断开；本任务每 30 秒发送一次
        （与 qcal_env StarTransport 的心跳实现保持一致）。
        """
        from star_protocol.protocol import Envelope, EnvelopeType, HeartbeatInfo

        while True:
            await asyncio.sleep(30)
            if not getattr(client, "connected", False):
                return
            try:
                envelope = Envelope(
                    envelope_type=EnvelopeType.HEARTBEAT,
                    sender=client.client_id,
                    recipient="hub",
                    message=HeartbeatInfo(status="alive"),
                )
                await client.send_envelope(envelope)
            except Exception:
                pass

    # 创建Star Protocol Agent
    def _create_star_client(self) -> tuple[Any, asyncio.Event, list[dict[str, Any]]]:
        try:
            from star_protocol.client import AgentClient
        except ImportError as exc:
            raise RuntimeError(
                "缺少 star-protocol；请先安装项目 README 固定的依赖"
            ) from exc

        client = AgentClient(
            agent_id=self.agent_id,
            env_id=self.env_id,
            hub_url=self.server_url,
            metadata={"name": "LLM Calibration Agent"},
        )
        discovery_event = asyncio.Event()
        discovered_tools: list[dict[str, Any]] = []

        @client.event("tools_discovered")
        async def on_tools_discovered(event_message: Any) -> None:
            raw_tools = (event_message.data or {}).get("tools", [])
            if isinstance(raw_tools, list):
                discovered_tools.clear()
                discovered_tools.extend(raw_tools)
            discovery_event.set()

        return client, discovery_event, discovered_tools

    def _build_model_inputs(
        self,
        message: CalibrationMessage,
    ) -> tuple[Any, Any, list[Callable[..., Any]]]:
        try:
            from menglong import Context, Model
        except ImportError as exc:
            raise RuntimeError(
                "缺少 MengLong SDK；本 Agent 需要 `menglong` 包才能调用模型"
            ) from exc

        decorated_tools = [
            build_menglong_tool(tool_definition)
            for tool_definition in message.discovered_tools
        ]
        decorated_tools.append(build_menglong_tool(finish_tool_definition()))

        context = Context()
        context.system(
            build_system_prompt(
                message.calibration_id,
                max_tool_attempts=self.max_tool_attempts,
            )
        )
        context.user(message.user_request)
        return Model(config_path=str(self.config_path)), context, decorated_tools

    async def _drive_generator(
        self,
        *,
        generator: Any,
        client: Any,
        message: CalibrationMessage,
    ) -> CalibrationRunResult:
        discovered_names = {tool["name"] for tool in message.discovered_tools}

        while True:
            response = await asyncio.to_thread(generator.run)
            if generator.state.phase == LoopPhase.COMPLETED:
                message.status = "failed"
                message.end_reason = "finish_tool_required"
                answer = (response.text if response else None) or "<empty response>"
                raise RuntimeError(
                    "模型未调用 Finish 就停止了校准流程；最后回复：" + answer
                )

            if generator.state.phase != LoopPhase.WAITING_RESULT:
                raise RuntimeError(
                    f"Generator 在非预期状态停止：{generator.state.phase.value}"
                )

            call = find_waiting_call(generator)
            arguments = normalize_arguments(call.arguments)

            if call.name == FINISH_TOOL_NAME:
                answer = arguments.get("answer")
                if not isinstance(answer, str) or not answer.strip():
                    generator.submit_tool_result(
                        {"accepted": False, "error": "Finish.answer 必须是非空字符串"},
                        tool_call_id=call.id,
                    )
                    continue
                message.status = "completed"
                message.final_answer = answer.strip()
                message.end_reason = "finish_tool"
                self._log("calibration_finished", answer=message.final_answer)
                return self._result(message)

            if call.name not in discovered_names:
                raise RuntimeError(f"模型调用了 Env 未发现的工具：{call.name}")
            if message.action_count >= self.max_actions:
                message.status = "failed"
                message.end_reason = "max_actions_exceeded"
                raise RuntimeError(f"已达到最大 Env action 次数：{self.max_actions}")

            # 同一工具连续调用计数；换工具即归 1（confirm 成功进入下一实验同理）
            if message.last_tool == call.name:
                message.tool_streak += 1
            else:
                message.last_tool = call.name
                message.tool_streak = 1
            tool_attempt = {
                "tool": call.name,
                "consecutive_calls": message.tool_streak,
                "finish_threshold": self.max_tool_attempts,
            }

            definition = next(
                tool for tool in message.discovered_tools if tool["name"] == call.name
            )
            session_field = definition.get("sessionField")
            if session_field:
                arguments[session_field] = message.calibration_id
            try:
                arguments, conversions = coerce_arguments(
                    arguments, definition["inputSchema"]
                )
                validate_arguments(arguments, definition["inputSchema"])
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                observation = {
                    "tool": call.name,
                    "calibration_id": message.calibration_id,
                    "validation_error": f"{type(exc).__name__}: {exc}",
                    "instruction": (
                        "工具尚未发送给 Env。请保持当前步骤，修正参数类型或缺失字段，"
                        "并使用完整参数重新调用同一个工具。"
                    ),
                    "tool_attempt": tool_attempt,
                }
                self._log("model_action_rejected", **observation)
                generator.submit_tool_result(observation, tool_call_id=call.id)
                continue
            if conversions:
                self._log(
                    "model_arguments_normalized",
                    tool=call.name,
                    conversions=conversions,
                )

            message.action_count += 1
            message.attempts[call.name] += 1
            attempt = message.attempts[call.name]
            self._log(
                "env_action_sending",
                tool_call_id=str(call.id),
                tool=call.name,
                attempt=attempt,
                arguments=arguments,
            )
            action_id = await client.send_action(
                call.name,
                arguments,
                recipient=self.env_id,
                timeout=self.action_timeout,
            )
            try:
                outcome = await asyncio.wait_for(
                    client.get_outcome(action_id), timeout=self.action_timeout
                )
            except asyncio.TimeoutError as exc:
                message.status = "failed"
                message.end_reason = "action_outcome_timeout"
                raise RuntimeError(
                    f"Env 工具 {call.name!r} 的 Action {action_id!r} 在 "
                    f"{self.action_timeout:g} 秒内没有返回结果。"
                    "请检查 Env 是否仍连接、实验是否仍在执行；必要时增大 "
                    "--action-timeout。"
                ) from exc
            if not isinstance(outcome, dict):
                outcome = {"isError": True, "content": repr(outcome)}

            observation = {
                "action_id": str(action_id),
                "calibration_id": message.calibration_id,
                "tool": call.name,
                "attempt": attempt,
                "env_is_error": bool(outcome.get("isError")),
                "content": outcome.get("content"),
                "tool_attempt": tool_attempt,
            }
            message.action_log.append(observation)
            self._log("env_outcome_received", **observation)

            # Env business errors are observations. The next model round chooses
            # whether and how to retry; only transport/protocol failures stop Python.
            generator.submit_tool_result(observation, tool_call_id=call.id)

    def _generator_event_logger(self) -> Callable[[Any], None]:
        def log_event(event: Any) -> None:
            if event.kind == EventKind.MODEL_CALL_STARTED:
                self._log("model_round_started", round=event.round_number)
            elif event.kind == EventKind.EXTERNAL_RESULT_REQUIRED:
                call = event.tool_call
                self._log(
                    "model_action_requested",
                    round=event.round_number,
                    tool_call_id=str(call.id),
                    tool=call.name,
                )
            elif event.kind == EventKind.ERROR:
                self._log("generator_error", error=event.text)

        return log_event

    @staticmethod
    def _result(message: CalibrationMessage) -> CalibrationRunResult:
        return CalibrationRunResult(
            calibration_id=message.calibration_id,
            status=message.status,
            final_answer=message.final_answer or "",
            action_count=message.action_count,
            attempts=dict(message.attempts),
        )

    @staticmethod
    def _log(event: str, **data: Any) -> None:
        print(
            json.dumps(
                {"event": event, "timestamp": datetime.now(UTC).isoformat(), **data},
                ensure_ascii=False,
            ),
            flush=True,
        )


def configure_menglong(config_path: Path) -> None:
    """Expose the selected SDK config without overwriting caller environment."""
    if not config_path.is_file():
        raise FileNotFoundError(f"找不到模型配置文件：{config_path}")
    os.environ.setdefault("MENGLONG_CONFIG", str(config_path))
    os.environ.setdefault("MENGLONG_CONFIG_FILE", str(config_path))


def read_default_model_id(config_path: Path) -> str | None:
    if not config_path.is_file():
        return None
    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)
    value = config.get("default", {}).get("model_id")
    return value if isinstance(value, str) and value else None


def validate_discovered_tools(tools: Sequence[Any]) -> list[dict[str, Any]]:
    if not tools:
        raise RuntimeError("Env 没有返回任何工具")
    validated: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, raw_tool in enumerate(tools):
        if not isinstance(raw_tool, dict):
            raise TypeError(f"Env 工具 #{index} 不是 JSON object")
        name = raw_tool.get("name")
        schema = raw_tool.get("inputSchema")
        if not isinstance(name, str) or not TOOL_NAME_PATTERN.fullmatch(name):
            raise ValueError(f"Env 工具 #{index} 的 name 无效：{name!r}")
        if name == FINISH_TOOL_NAME:
            raise ValueError(f"Env 工具名 {FINISH_TOOL_NAME!r} 与 Agent 内置工具冲突")
        if name in names:
            raise ValueError(f"Env 返回了重复工具：{name}")
        if not isinstance(schema, dict) or schema.get("type") != "object":
            raise ValueError(f"Env 工具 {name} 缺少 object 类型 inputSchema")
        schema = copy.deepcopy(schema)
        properties = schema.setdefault("properties", {})
        if not isinstance(properties, dict):
            raise ValueError(f"Env 工具 {name} 的 properties 必须是 JSON object")
        required = schema.setdefault("required", [])
        if not isinstance(required, list):
            raise ValueError(f"Env 工具 {name} 的 required 必须是 JSON array")
        session_field = detect_session_field(name, properties, required)
        names.add(name)
        validated.append(
            {
                "name": name,
                "description": str(raw_tool.get("description") or ""),
                "inputSchema": schema,
                "sessionField": session_field,
            }
        )
    return validated


def detect_session_field(
    name: str,
    properties: dict[str, Any],
    required: list[str],
) -> str | None:
    """识别工具 Schema 中的会话标识字段（Python 负责强制覆盖其值）。

    规则：required 内、名称以 _id 结尾、类型为 string 的属性视为会话字段；
    多个候选时优先描述包含 session/calibration/experiment 的那个。
    找不到时返回 None，调用侧跳过覆盖。
    """
    candidates: list[str] = []
    for field_name in required:
        field_schema = properties.get(field_name)
        if not isinstance(field_schema, dict):
            continue
        field_type = field_schema.get("type")
        is_string = field_type == "string" or (
            isinstance(field_type, list) and "string" in field_type
        )
        if field_name.endswith("_id") and is_string:
            candidates.append(field_name)
    if not candidates:
        print(
            json.dumps(
                {"event": "session_field_not_found", "tool": name},
                ensure_ascii=False,
            ),
            flush=True,
        )
        return None
    if len(candidates) == 1:
        return candidates[0]
    for field_name in candidates:
        description = str(properties[field_name].get("description") or "").lower()
        if any(word in description for word in ("session", "calibration", "experiment")):
            return field_name
    return candidates[0]


def build_menglong_tool(definition: dict[str, Any]) -> ToolInfo:
    """把 Env 发现的工具定义转成 MengLong 标准 ToolInfo。

    MengLong Model._ensure_tools 对 ToolInfo 原样透传，因此 Env 发布的
    inputSchema（类型、描述、约束、required）会完整到达模型 Provider。
    """
    return ToolInfo(
        function=FunctionInfo(
            name=definition["name"],
            description=definition["description"],
            parameters=definition["inputSchema"],
        )
    )


def finish_tool_definition() -> dict[str, Any]:
    return {
        "name": FINISH_TOOL_NAME,
        "description": (
            "全部校准步骤完成并确认后结束本次校准流程；"
            "或确认无法继续时汇报失败并结束。"
        ),
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["answer"],
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "完整校准总结，包括各步骤结论。",
                }
            },
        },
    }


def normalize_arguments(arguments: Any) -> dict[str, Any]:
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return dict(arguments)
    if isinstance(arguments, str):
        parsed = json.loads(arguments)
        if isinstance(parsed, dict):
            return parsed
    raise TypeError("模型工具 arguments 必须是 JSON object")


def validate_arguments(arguments: dict[str, Any], schema: dict[str, Any]) -> None:
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    missing = [name for name in required if name not in arguments]
    if missing:
        raise ValueError(f"工具参数缺少必填字段：{', '.join(missing)}")
    if schema.get("additionalProperties") is False:
        extras = sorted(set(arguments).difference(properties))
        if extras:
            raise ValueError(f"工具参数包含未定义字段：{', '.join(extras)}")
    for name, value in arguments.items():
        property_schema = properties.get(name)
        if isinstance(property_schema, dict):
            validate_json_value(name, value, property_schema)


def coerce_arguments(
    arguments: dict[str, Any], schema: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Safely normalize common LLM JSON type mistakes using the Env schema."""
    normalized = dict(arguments)
    conversions: list[dict[str, Any]] = []
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return normalized, conversions
    for name, property_schema in properties.items():
        if name not in normalized or not isinstance(property_schema, dict):
            continue
        original = normalized[name]
        converted = coerce_json_value(name, original, property_schema)
        normalized[name] = converted
        if converted != original or type(converted) is not type(original):
            conversions.append(
                {
                    "parameter": name,
                    "from": original,
                    "to": converted,
                }
            )
    return normalized, conversions


def coerce_json_value(name: str, value: Any, schema: dict[str, Any]) -> Any:
    expected = schema.get("type")
    allowed = expected if isinstance(expected, list) else [expected]
    non_null = [kind for kind in allowed if kind != "null"]
    if value is None or not non_null:
        return value
    target = non_null[0]

    if target == "number" and isinstance(value, str):
        converted = float(_normalized_numeric_text(name, value))
        if not math.isfinite(converted):
            raise ValueError(f"工具参数 {name} 必须是有限数值")
        return converted
    if target == "integer" and isinstance(value, str):
        converted = float(_normalized_numeric_text(name, value))
        if not math.isfinite(converted) or not converted.is_integer():
            raise ValueError(f"工具参数 {name} 必须是整数")
        return int(converted)
    if target == "boolean" and isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "false"}:
            return normalized == "true"
    if target == "array" and isinstance(value, str):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise TypeError(f"工具参数 {name} 必须是 JSON array")
        value = parsed
    if target == "array" and isinstance(value, list):
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            return [
                coerce_json_value(f"{name}[{index}]", item, item_schema)
                for index, item in enumerate(value)
            ]
    return value


def _normalized_numeric_text(name: str, value: str) -> str:
    normalized = value.strip().replace(",", "").replace("_", "")
    if not normalized:
        raise ValueError(f"工具参数 {name} 不能是空字符串")
    return normalized


def validate_json_value(name: str, value: Any, schema: dict[str, Any]) -> None:
    expected = schema.get("type")
    allowed = expected if isinstance(expected, list) else [expected]
    valid = any(
        (
            kind == "null" and value is None
            or kind == "string" and isinstance(value, str)
            or kind == "integer" and isinstance(value, int) and not isinstance(value, bool)
            or kind == "number" and isinstance(value, (int, float)) and not isinstance(value, bool)
            or kind == "boolean" and isinstance(value, bool)
            or kind == "array" and isinstance(value, list)
            or kind == "object" and isinstance(value, dict)
        )
        for kind in allowed
    )
    if expected is not None and not valid:
        raise TypeError(f"工具参数 {name} 的类型不符合 schema：期望 {expected!r}")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        raise ValueError(f"工具参数 {name} 太短")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"工具参数 {name} 小于最小值 {schema['minimum']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(f"工具参数 {name} 的元素数量不足")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate_json_value(f"{name}[{index}]", item, item_schema)


def find_waiting_call(generator: Any) -> Any:
    # 模型一轮可能产生多个工具调用：按顺序逐个处理（submit 后队列前移）。
    waiting = generator.state.active_calls
    if not waiting:
        raise RuntimeError("Generator 没有等待外部结果的工具调用")
    return waiting[0]


def build_system_prompt(
    calibration_id: str,
    *,
    max_tool_attempts: int,
) -> str:
    return f"""你是量子比特自动校准 Agent，负责通过 Env 提供的工具自主完成一轮量子比特校准。一次用户请求对应一轮完整校准。工具名、参数与描述以工具定义为准，本提示词不重复工具清单。

## 背景

量子比特校准是一系列按依赖顺序排列的实验（读取腔频率 → 比特频率 → π 脉冲 → e 态读取腔 → T1 → T2*/T2 echo → 单次测量判态）。实验顺序与依赖继承关系以工具定义的发现顺序和各工具描述为准。校准单向推进：后续步骤暴露前序标定问题时，可借助 Env 提供的能力回到前序实验重新标定。

## 知识

- Env 可能提供知识库/手册（含各实验的判据、典型参数范围、调参经验与样品预设值）、实验报告与状态查询等工具；按需查阅，首次实验前优先查阅相关章节。
- 各实验的合格判据以知识库/报告为准；若知识库未给出阈值，尽量采用高置信度的结果作为依据。
- 判定时必须逐条对照输出检查清单（实测值 vs 判据），最后显式给出"合格/不合格"结论；报告缺少判定所需字段时，不得自行假设合格。

## 会话约束

- 本轮全程使用固定 calibration_id：{calibration_id}；工具调用中的会话标识字段名以工具 Schema 为准（如 calibration_id），Python 会强制覆盖该字段的值，你仍需提供该字段。
- 用户请求中提到的工具名、字段名可能与 Env 实际 Schema 不一致，一律以 Env 工具定义的实际名称与 Schema 为准。
- 每次调用都必须提供完整参数，不得只给与上次不同的参数。
- 所有参数的单位、合法范围、默认值与含义以工具 Schema 为准；禁止凭记忆使用任何具体频率、幅度、时间等物理数值。
- Env 返回的业务错误不是终止信号：结合错误信息修正参数后重试当前实验。

## 每个实验的固定闭环

1. 调用实验工具，从 Outcome 中取得该次实验的报告/产物路径。
2. 若 Env 提供了报告读取类工具（按描述判断：读取 Env 保存的产物/Markdown 报告），调用它阅读报告并据此研判；没有该工具时只能依据 Outcome 内容研判。
3. 按知识库/报告给出的判据检查全部指标。
4. 判定合格后，若 Env 提供了候选确认类工具（按描述判断：把拟合候选正式生效），调用它确认报告中列出的全部候选；确认成功才算完成当前实验，才能进入下一步。
5. 若缺少推进流程所必需的工具（无法阅读报告或无法确认候选），调用 Finish 并在 answer 中说明缺少哪些必要工具及原因；不得无限重试。

## 失败与结束

- 失败结束：Python 会在每次工具结果中注入 tool_attempt 字段（consecutive_calls 为该工具的调用计数，finish_threshold={max_tool_attempts}）。当计数达到 finish_threshold 且本次结果仍不合格时，调用 Finish 汇报失败：answer 写清已确认的标定、卡住的实验、该实验的完整参数尝试序列与失败原因；调用 Finish 后不得再调用任何工具。
- 全部实验确认完成后才能调用 Finish；若 Env 提供了状态查询类工具（按描述判断），Finish 前先查询核对全部实验均已确认。
- Finish.answer 按实验顺序总结每个实验的最终参数、标定值与重试情况；需要继续时必须调用工具，不得用普通文本提前结束。
"""


async def close_star_client(client: Any) -> None:
    websocket = getattr(client, "websocket", None)
    if websocket is not None:
        await websocket.close()
    client.connected = False
    client.websocket = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", help="一次完整校准请求")
    parser.add_argument("--server-url", default="ws://127.0.0.1:8765")
    parser.add_argument("--env-id", default="qcal-env")
    parser.add_argument("--agent-id", default=f"calibration-agent-{os.getpid()}")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--model")
    parser.add_argument("--discovery-timeout", type=float, default=15.0)
    parser.add_argument("--action-timeout", type=float, default=600.0)
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=120,
        help="模型最大轮数；完整校准下限约 80 轮（每次 Env action 至少 1 轮）",
    )
    parser.add_argument(
        "--max-actions",
        type=int,
        default=120,
        help="Env action 最大次数；完整校准下限约 40 次（8 实验 × 约 5 次）",
    )
    parser.add_argument(
        "--max-tool-attempts",
        type=int,
        default=5,
        help="同一工具调用计数达到该值且仍不合格时，模型应调用 Finish 汇报失败",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.request:
        raise SystemExit("请提供一次完整校准请求")
    agent = CalibrationAgent(
        server_url=args.server_url,
        env_id=args.env_id,
        agent_id=args.agent_id,
        config_path=args.config,
        model_id=args.model,
        discovery_timeout=args.discovery_timeout,
        action_timeout=args.action_timeout,
        max_rounds=args.max_rounds,
        max_actions=args.max_actions,
        max_tool_attempts=args.max_tool_attempts,
    )
    result = asyncio.run(agent.run(args.request))
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
