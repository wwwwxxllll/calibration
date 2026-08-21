"""Small file store for runs, candidates and Agent-confirmed calibrations."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path


class FileStore:
    def __init__(self, root: str | Path, *, device_id: str, qubit_id: str) -> None:
        self.root = Path(root).resolve()
        self.actions_root = self.root / "actions"
        self.calibrations_path = self.root / "calibrations.json"
        self.knowledge_dir = self.root / "knowledge"
        self.presets_dir = self.root / "presets"
        self.device_id = device_id
        self.qubit_id = qubit_id
        self.actions_root.mkdir(parents=True, exist_ok=True)
        if not self.calibrations_path.exists() or self.calibrations_path.stat().st_size == 0:
            self._write_json(self.calibrations_path, {"candidates": [], "active": {}})

    def read_knowledge_document(self, topic: str) -> str:
        """读取知识手册主题文档；当前仅支持 common。文件由人类专家维护。"""
        if topic != "common":
            raise ValueError(f"未知知识主题：{topic}（当前仅支持 common）。")
        path = self.knowledge_dir / "handbook.md"
        if not path.is_file():
            return (
                f"知识手册尚未填写（{path}）。"
                "请人类专家按 README 中的模板创建该文件；创建后本工具将返回其完整内容。"
            )
        return path.read_text(encoding="utf-8")

    def read_preset_document(self) -> str:
        """读取本样品预设值文档（人工填写，可为空）。"""
        path = self.presets_dir / f"{self.device_id}.md"
        if not path.is_file():
            return (
                f"预设文档尚未填写（{path}）。"
                "请人类专家按 README 中的模板创建该文件；创建后本工具将返回其完整内容。"
            )
        return path.read_text(encoding="utf-8")

    def action_dir(self, action_id: str) -> Path:
        self._validate_action_id(action_id)
        path = (self.actions_root / action_id).resolve()
        if self.actions_root not in path.parents:
            raise ValueError("action_id 超出 Action 目录。")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def read_markdown_artifact(self, logical_path: str, *, calibration_id: str) -> str:
        """Read one report through its Env-owned logical resource path."""
        parts = logical_path.split("/")
        if len(parts) != 4 or parts[0] or parts[1] != "files" or parts[3] != "report.md":
            raise ValueError("当前只支持 /files/{action_id}/report.md 格式的 Markdown 报告路径。")

        source_action_id = parts[2]
        self._validate_action_id(source_action_id)
        source_dir = (self.actions_root / source_action_id).resolve()
        if self.actions_root not in source_dir.parents:
            raise ValueError("报告路径超出 Env Action 目录。")

        record_path = source_dir / "result.json"
        if not record_path.is_file():
            raise ValueError(f"报告所属 Action 不存在：{source_action_id}。")
        record = self._read_json(record_path)
        if record.get("calibration_id") != calibration_id:
            raise ValueError("报告不属于当前 calibration_id。")

        report_path = (source_dir / "report.md").resolve()
        if self.actions_root not in report_path.parents or not report_path.is_file():
            raise ValueError("Markdown 报告不存在。")
        return report_path.read_text(encoding="utf-8")

    def save_action(self, action_id: str, value: dict[str, object]) -> None:
        self._write_json(self.action_dir(action_id) / "result.json", value)

    def get_action(self, action_id: str) -> dict[str, object]:
        path = self.action_dir(action_id) / "result.json"
        if not path.exists():
            raise KeyError(f"Action 不存在: {action_id}")
        return self._read_json(path)

    def find_action(self, action_id: str) -> dict[str, object] | None:
        path = self.action_dir(action_id) / "result.json"
        return self._read_json(path) if path.exists() else None

    def list_actions(self) -> list[dict[str, object]]:
        values = []
        for path in sorted(self.actions_root.glob("*/result.json"), reverse=True):
            values.append(self._read_json(path))
        return values

    def append_action_event(
        self,
        action_id: str,
        stage: str,
        message: str,
        data: dict[str, object] | None = None,
    ) -> None:
        path = self.action_dir(action_id) / "events.json"
        events = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        event: dict[str, object] = {
            "timestamp": _now(),
            "stage": stage,
            "message": message,
        }
        if data is not None:
            event["data"] = data
        events.append(event)
        self._write_json(path, events)

    def get_action_events(self, action_id: str) -> list[dict[str, object]]:
        path = self.action_dir(action_id) / "events.json"
        if not path.exists():
            raise KeyError(f"Action 事件不存在: {action_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def add_candidate(
        self,
        *,
        action_id: str,
        calibration_id: str,
        key: str,
        value: float,
        unit: str,
    ) -> dict[str, object]:
        store = self._calibration_data()
        candidate = {
            "candidate_id": str(uuid.uuid4()),
            "action_id": action_id,
            "calibration_id": calibration_id,
            "device_id": self.device_id,
            "qubit_id": self.qubit_id,
            "key": key,
            "value": float(value),
            "unit": unit,
            "status": "pending_agent_review",
            "created_at": _now(),
        }
        store["candidates"].append(candidate)
        self._write_json(self.calibrations_path, store)
        return candidate

    def confirm(
        self,
        *,
        calibration_id: str,
        candidate_ids: list[str],
        confirmed_by: str,
        note: str | None = None,
    ) -> list[dict[str, object]]:
        store = self._calibration_data()
        selected = [
            item
            for item in store["candidates"]
            if item["candidate_id"] in candidate_ids and item["calibration_id"] == calibration_id
        ]
        if len(selected) != len(set(candidate_ids)):
            raise ValueError("Candidate 不存在或不属于当前 calibration_id。")
        if any(self.get_action(str(item["action_id"])).get("status") != "succeeded" for item in selected):
            raise ValueError("只有成功完成的实验 Candidate 才能确认。")
        confirmed = []
        for candidate in selected:
            if candidate["status"] != "pending_agent_review":
                raise ValueError(f"Candidate 已处理: {candidate['candidate_id']}")
            candidate["status"] = "confirmed"
            calibration = {
                **candidate,
                "calibration_id": str(uuid.uuid4()),
                "status": "active",
                "confirmed_by": confirmed_by,
                "confirmed_at": _now(),
                "note": note,
            }
            store["active"][_active_key(str(candidate["key"]), calibration_id)] = calibration
            confirmed.append(calibration)
        for candidate in confirmed:
            for item in store["candidates"]:
                if (
                    item.get("calibration_id") == calibration_id
                    and item.get("key") == candidate["key"]
                    and item.get("status") == "pending_agent_review"
                ):
                    item["status"] = "rejected"
        self._write_json(self.calibrations_path, store)
        return confirmed

    def active(self, key: str, calibration_id: str) -> dict[str, object] | None:
        return self._calibration_data()["active"].get(_active_key(key, calibration_id))

    def calibrations(self) -> dict[str, object]:
        return self._calibration_data()

    def _calibration_data(self) -> dict[str, object]:
        return self._read_json(self.calibrations_path)

    @staticmethod
    def _validate_action_id(action_id: str) -> None:
        allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        if not action_id or any(char not in allowed for char in action_id):
            raise ValueError("action_id 含有非法字符。")

    @staticmethod
    def _read_json(path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _active_key(key: str, calibration_id: str) -> str:
    return f"{calibration_id}::{key}"


__all__ = ["FileStore"]