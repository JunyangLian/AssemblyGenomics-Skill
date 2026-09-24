"""M1 段 2 测试：状态迁移、磁盘持久化、原子写入、恢复与禁止重复提交。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.state_registry import (
    ACTIVE_STATUSES,
    VALID_STATUS,
    RunRegistry,
    validate_transition,
)


@pytest.fixture
def registry(tmp_path: Path) -> RunRegistry:
    return RunRegistry(tmp_path / "state")


def test_status_vocabulary_complete() -> None:
    expected = {
        "PENDING", "READY", "RUNNING", "SUCCEEDED", "FAILED",
        "WAITING_REVIEW", "BLOCKED", "REJECTED",
        "SKIPPED_NOT_APPLICABLE", "STALE",
    }
    assert VALID_STATUS == expected


@pytest.mark.parametrize(
    "frm, to, ok",
    [
        ("PENDING", "READY", True),
        ("READY", "RUNNING", True),
        ("RUNNING", "SUCCEEDED", True),
        ("RUNNING", "FAILED", True),
        ("RUNNING", "WAITING_REVIEW", True),
        ("RUNNING", "BLOCKED", True),
        ("WAITING_REVIEW", "READY", True),
        ("WAITING_REVIEW", "REJECTED", True),
        ("SUCCEEDED", "STALE", True),
        ("STALE", "READY", True),
        # 非法
        ("PENDING", "SUCCEEDED", False),
        ("RUNNING", "PENDING", False),
        ("SUCCEEDED", "RUNNING", False),
        ("BLOCKED", "READY", False),
        ("SKIPPED_NOT_APPLICABLE", "RUNNING", False),
        ("PENDING", "REJECTED", False),
    ],
)
def test_transition_rules(frm: str, to: str, ok: bool) -> None:
    if ok:
        validate_transition(frm, to)  # 不抛异常
    else:
        with pytest.raises(ValueError):
            validate_transition(frm, to)


def test_active_statuses_cover_resumable() -> None:
    assert ACTIVE_STATUSES == frozenset({"PENDING", "READY", "RUNNING"})


def test_register_and_persist(registry: RunRegistry) -> None:
    rec = registry.register("proj-a", "run-1")
    assert rec["status"] == "PENDING"
    # 磁盘记录为准：从磁盘重读
    assert registry.get_run("proj-a")["run_id"] == "run-1"
    assert registry._run_path("proj-a").exists()


def test_reject_duplicate_active_submission(registry: RunRegistry) -> None:
    registry.register("proj-a", "run-1")
    with pytest.raises(ValueError, match="禁止重复提交"):
        registry.register("proj-a", "run-2")


def test_register_again_after_terminal_state_ok(registry: RunRegistry) -> None:
    registry.register("proj-a", "run-1")
    registry.transition("proj-a", "READY")
    registry.transition("proj-a", "RUNNING")
    registry.transition("proj-a", "SUCCEEDED")
    registry.register("proj-a", "run-2")  # 终态后可开新一轮


def test_transition_persists_and_rejects_illegal(registry: RunRegistry) -> None:
    registry.register("proj-a", "run-1")
    registry.transition("proj-a", "READY")
    assert registry.get_run("proj-a")["status"] == "READY"
    with pytest.raises(ValueError, match="非法迁移"):
        registry.transition("proj-a", "SUCCEEDED")  # READY 不能直接 SUCCEEDED


def test_manifest_stored_and_recoverable(registry: RunRegistry) -> None:
    manifest = {
        "manifest_version": 1, "run_id": "run-1", "project_id": "proj-a",
        "sample": "s", "assembly_identity": "hap1/round_001",
        "upstream_route": "juicer-3ddna",
        "fasta": {"path": "/data/a.fa", "sha256": "a" * 64},
        "generated_at": "2026-01-01T00:00:00+00:00",
        "restore_inputs": [],
    }
    registry.register("proj-a", "run-1", manifest)
    got = registry.recover("proj-a")
    assert got is not None
    assert got["has_manifest"] is True
    assert got["manifest"]["fasta"]["sha256"] == "a" * 64


def test_recover_none_when_no_record(registry: RunRegistry) -> None:
    assert registry.recover("no-such-project") is None


def test_recover_after_interrupt_is_idempotent(registry: RunRegistry) -> None:
    """会话中断后恢复扫描不应改动磁盘状态（幂等）。"""
    registry.register("proj-a", "run-1")
    before = registry._run_path("proj-a").read_text(encoding="utf-8")
    registry.recover("proj-a")
    after = registry._run_path("proj-a").read_text(encoding="utf-8")
    assert before == after


def test_no_partial_write_on_invalid_transition(registry: RunRegistry) -> None:
    registry.register("proj-a", "run-1")
    with pytest.raises(ValueError):
        registry.transition("proj-a", "SUCCEEDED")
    rec = registry.get_run("proj-a")
    assert rec["status"] == "PENDING"  # 未被污染


def test_atomic_write_creates_single_file(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "x.json"
    from scripts.state_registry import atomic_write_text
    atomic_write_text(target, json.dumps({"k": 1}))
    assert target.exists()
    leftovers = [p for p in target.parent.glob("*.tmp")]
    assert leftovers == []