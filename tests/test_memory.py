import json
import os
from datetime import datetime

import pytest

import memory_store
import paths
from memory_store import load_memory, render_current_memory, update_memory
from tools.memory import make_memory_tool


@pytest.fixture
def memory_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "MEMORY_DIR", tmp_path / "memory")
    return tmp_path / "memory"


def _file(memory_dir):
    return memory_dir / "project_memory.json"


def test_load_memory_when_file_missing(memory_dir):
    doc = load_memory()
    assert doc["current"] == {}
    assert doc["history"] == []
    assert not _file(memory_dir).exists()


def test_update_memory_creates_file_with_current_and_history(memory_dir):
    result = update_memory("language", "TypeScript", "s1")
    assert result["ok"] is True and result["status"] == "created"
    data = json.loads(_file(memory_dir).read_text(encoding="utf-8"))
    assert data["current"]["language"]["value"] == "TypeScript"
    assert len(data["history"]) == 1
    assert data["history"][0]["action"] == "create"
    assert data["history"][0]["old_value"] is None


def test_load_memory_returns_saved_values(memory_dir):
    update_memory("database", "PostgreSQL", "s1")
    assert load_memory()["current"]["database"]["value"] == "PostgreSQL"


def test_update_keeps_other_conventions(memory_dir):
    update_memory("language", "TypeScript", "s1")
    update_memory("database", "PostgreSQL", "s1")
    update_memory("auth", "JWT", "s1")
    update_memory("auth", "session cookie", "s2")
    current = load_memory()["current"]
    assert current["language"]["value"] == "TypeScript"
    assert current["database"]["value"] == "PostgreSQL"


def test_update_replaces_value_and_records_history(memory_dir):
    update_memory("auth", "JWT", "s1")
    result = update_memory("auth", "session cookie", "s2")
    assert result["status"] == "updated"
    doc = load_memory()
    assert doc["current"]["auth"]["value"] == "session cookie"
    entry = doc["history"][-1]
    assert entry["action"] == "update"
    assert entry["old_value"] == "JWT"
    assert entry["new_value"] == "session cookie"
    assert entry["source_session"] == "s2"
    datetime.fromisoformat(entry["timestamp"])
    assert any(h["new_value"] == "JWT" for h in doc["history"])


def test_render_current_memory_excludes_old_value(memory_dir):
    update_memory("auth", "JWT", "s1")
    update_memory("auth", "session cookie", "s2")
    doc = load_memory()
    text = render_current_memory()
    assert "session cookie" in text
    assert "JWT" not in text
    for entry in doc["history"]:
        assert entry["timestamp"] not in text


def test_render_current_memory_empty_without_memory(memory_dir):
    assert render_current_memory() == ""


def test_render_current_memory_sorted_by_key(memory_dir):
    update_memory("language", "TypeScript", "s1")
    update_memory("auth", "JWT", "s1")
    assert render_current_memory().splitlines() == ["- auth: JWT", "- language: TypeScript"]


def test_update_same_value_is_unchanged(memory_dir):
    update_memory("auth", "JWT", "s1")
    before = load_memory()
    result = update_memory("auth", "JWT", "s2")
    after = load_memory()
    assert result["status"] == "unchanged"
    assert len(after["history"]) == len(before["history"]) == 1
    assert after["current"]["auth"]["updated_at"] == before["current"]["auth"]["updated_at"]


def test_update_validates_input(memory_dir):
    for bad_key in ["", "  ", "Bad Key", "-x", "a/b"]:
        with pytest.raises(ValueError):
            update_memory(bad_key, "x", "s1")
    with pytest.raises(ValueError):
        update_memory("auth", "  ", "s1")
    with pytest.raises(ValueError):
        update_memory("auth", "x" * 501, "s1")
    with pytest.raises(ValueError):
        update_memory("auth", "JWT", "")
    assert not _file(memory_dir).exists()


def test_key_is_normalized_to_lowercase(memory_dir):
    update_memory("  Auth ", "JWT", "s1")
    assert "auth" in load_memory()["current"]


def test_tool_updates_memory_with_session_id(memory_dir):
    tool = make_memory_tool("sess-A")
    assert tool.name == "update_project_memory"
    out = json.loads(tool.invoke({"key": "database", "value": "PostgreSQL"}))
    assert out["ok"] is True
    doc = load_memory()
    assert doc["current"]["database"]["value"] == "PostgreSQL"
    assert doc["history"][0]["source_session"] == "sess-A"


def test_tool_rejects_invalid_key_and_value(memory_dir):
    tool = make_memory_tool("sess-A")
    bad_key = json.loads(tool.invoke({"key": "Bad Key", "value": "x"}))
    bad_value = json.loads(tool.invoke({"key": "auth", "value": "   "}))
    assert bad_key["ok"] is False and bad_key["error"]["code"] == "MEMORY_KEY_INVALID"
    assert bad_value["ok"] is False and bad_value["error"]["code"] == "MEMORY_VALUE_INVALID"
    assert not _file(memory_dir).exists()


def test_tool_error_is_structured_json(memory_dir):
    tool = make_memory_tool("sess-A")
    for args in ({"key": "", "value": "x"}, {"key": "auth", "value": "JWT"}):
        raw = tool.invoke(args)
        assert isinstance(raw, str)
        parsed = json.loads(raw)
        assert "ok" in parsed


def test_tool_reports_write_failure(memory_dir, monkeypatch):
    def boom(*args, **kwargs):
        raise PermissionError("read-only")

    monkeypatch.setattr(os, "replace", boom)
    out = json.loads(make_memory_tool("s").invoke({"key": "auth", "value": "JWT"}))
    assert out["ok"] is False and out["error"]["code"] == "MEMORY_WRITE_FAILED"


def test_two_sessions_record_their_own_session_id(memory_dir):
    make_memory_tool("sess-A").invoke({"key": "auth", "value": "JWT"})
    make_memory_tool("sess-B").invoke({"key": "auth", "value": "session cookie"})
    history = load_memory()["history"]
    assert [h["source_session"] for h in history] == ["sess-A", "sess-B"]


def test_corrupted_memory_file_does_not_break_load(memory_dir, capsys):
    memory_dir.mkdir(parents=True)
    _file(memory_dir).write_text("{rác không phải json", encoding="utf-8")
    doc = load_memory()
    assert doc["current"] == {} and doc["history"] == []
    assert "memory" in capsys.readouterr().err
    update_memory("auth", "JWT", "s1")
    assert json.loads(_file(memory_dir).read_text(encoding="utf-8"))["current"]["auth"]["value"] == "JWT"