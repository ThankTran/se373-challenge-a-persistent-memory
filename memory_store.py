"""Lưu trữ memory dự án (quy ước hiện hành + lịch sử thay đổi) ra file JSON.

Đường dẫn được đọc từ ``paths.MEMORY_DIR`` ở thời điểm gọi hàm để test có thể
monkeypatch.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any

import paths

SCHEMA_VERSION = 1
MEMORY_FILENAME = "project_memory.json"
KEY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,63}$")
MAX_VALUE_LENGTH = 500


class InvalidKeyError(ValueError):
    """Key rỗng hoặc sai định dạng slug."""


class InvalidValueError(ValueError):
    """Value rỗng hoặc quá dài."""


def _memory_file():
    return paths.MEMORY_DIR / MEMORY_FILENAME


def _empty_document() -> dict[str, Any]:
    return {"version": SCHEMA_VERSION, "updated_at": None, "current": {}, "history": []}


def _is_valid_document(doc: Any) -> bool:
    if not isinstance(doc, dict):
        return False
    current = doc.get("current", {})
    history = doc.get("history", [])
    if not isinstance(current, dict) or not isinstance(history, list):
        return False
    for record in current.values():
        if not isinstance(record, dict) or not isinstance(record.get("value"), str):
            return False
    return all(isinstance(entry, dict) for entry in history)


def _now_iso() -> str:
    # Cùng convention với observer.now_iso()
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _write_atomic(doc: dict[str, Any]) -> None:
    target = _memory_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)


def load_memory() -> dict[str, Any]:
    """Đọc memory từ đĩa. Không bao giờ ném lỗi."""
    target = _memory_file()
    if not target.exists():
        return _empty_document()
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
        if not _is_valid_document(doc):
            raise ValueError("sai cấu trúc document")
    except (OSError, ValueError) as exc:  # JSONDecodeError là con của ValueError
        print(f"[memory] Bỏ qua file memory hỏng ({target}): {exc}", file=sys.stderr)
        return _empty_document()
    doc.setdefault("version", SCHEMA_VERSION)
    doc.setdefault("updated_at", None)
    doc.setdefault("current", {})
    doc.setdefault("history", [])
    return doc


def update_memory(key: str, value: str, source_session: str) -> dict[str, Any]:
    """Tạo/đổi một quy ước và ghi lịch sử. Ném ValueError / OSError khi lỗi."""
    if not isinstance(key, str) or not key.strip():
        raise InvalidKeyError("key không được rỗng.")
    key = key.strip().lower()
    if not KEY_PATTERN.match(key):
        raise InvalidKeyError(
            "key phải là slug tiếng Anh chữ thường khớp ^[a-z0-9][a-z0-9_.-]{0,63}$ "
            "(ví dụ: language, database, auth, api_style)."
        )
    if not isinstance(value, str) or not value.strip():
        raise InvalidValueError("value không được rỗng.")
    value = value.strip()
    if len(value) > MAX_VALUE_LENGTH:
        raise InvalidValueError(f"value tối đa {MAX_VALUE_LENGTH} ký tự.")
    if not isinstance(source_session, str) or not source_session.strip():
        raise ValueError("source_session không được rỗng.")

    doc = load_memory()
    existing = doc["current"].get(key)
    old = existing.get("value") if existing else None

    if existing is not None and old == value:
        return {
            "ok": True,
            "key": key,
            "value": value,
            "status": "unchanged",
            "updated_at": existing.get("updated_at"),
        }

    action = "update" if existing is not None else "create"
    timestamp = _now_iso()
    doc["current"][key] = {
        "value": value,
        "updated_at": timestamp,
        "source_session": source_session,
    }
    doc["history"].append(
        {
            "timestamp": timestamp,
            "source_session": source_session,
            "key": key,
            "action": action,
            "old_value": old,
            "new_value": value,
        }
    )
    doc["updated_at"] = timestamp
    doc["version"] = SCHEMA_VERSION
    _write_atomic(doc)
    return {
        "ok": True,
        "key": key,
        "value": value,
        "status": "created" if action == "create" else "updated",
        "updated_at": timestamp,
    }


def render_current_memory() -> str:
    """Văn bản `- key: value` (sắp xếp theo key). Chỉ đọc `current`, không đọc `history`."""
    current = load_memory()["current"]
    lines = [f"- {key}: {current[key]['value']}" for key in sorted(current)]
    return "\n".join(lines)