"""M1 段 3 测试（二）：失效传播与恢复（test_invalidation）。

覆盖需求文档 14.2 必测情形的失效部分：
- 会话中断/任务失败后恢复不重复提交
- 修改 FASTA/参数后下游缓存与旧审核正确失效
- 依赖工具/数据库/资源不足时明确报错而非无界重试
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.plan import dependency_unavailable, invalidate_downstream, route
from scripts.state_registry import RunRegistry


@pytest.fixture
def registry(tmp_path: Path) -> RunRegistry:
    return RunRegistry(tmp_path / "state")


def test_no_duplicate_submit_after_interrupt(registry: RunRegistry) -> None:
    """会话中断：run 仍活跃(RUNNING)，恢复后禁止重复提交。"""
    registry.register("proj-a", "run-1")
    registry.transition("proj-a", "READY")
    registry.transition("proj-a", "RUNNING")
    # 恢复扫描读到活跃 run
    rec = registry.recover("proj-a")
    assert rec["run"]["status"] == "RUNNING"
    # 再次提交同一项目 -> 被拒
    with pytest.raises(ValueError, match="禁止重复提交"):
        registry.register("proj-a", "run-2")


def test_failed_then_manual_reset_then_resubmit(registry: RunRegistry) -> None:
    """任务失败后不自动重试；须显式经 READY 才可重新调度。"""
    registry.register("proj-a", "run-1")
    registry.transition("proj-a", "READY")
    registry.transition("proj-a", "RUNNING")
    registry.transition("proj-a", "FAILED")
    # 不允许失败后自动跳回 RUNNING（无界重试）
    with pytest.raises(ValueError, match="非法迁移"):
        registry.transition("proj-a", "RUNNING")
    # 显式复位到 READY 后才可重调度
    registry.transition("proj-a", "READY")
    registry.transition("proj-a", "RUNNING")
    assert registry.get_run("proj-a")["status"] == "RUNNING"


def test_status_change_invalidates_downstream(registry: RunRegistry) -> None:
    """修改上游 FASTA 后，下游已完成的节点标 STALE，历史版本保留。"""
    registry.register("proj-b", "run-1")
    registry.transition("proj-b", "READY")
    registry.transition("proj-b", "RUNNING")
    registry.transition("proj-b", "SUCCEEDED")
    affected = invalidate_downstream(registry, "proj-b", "FASTA sha256 已变更")
    assert len(affected) == 1
    assert affected[0]["to"] == "STALE"
    assert registry.get_run("proj-b")["status"] == "STALE"


def test_parameter_change_marks_stale(registry: RunRegistry) -> None:
    registry.register("proj-c", "run-1")
    registry.transition("proj-c", "READY")
    registry.transition("proj-c", "RUNNING")
    registry.transition("proj-c", "SUCCEEDED")
    affected = invalidate_downstream(registry, "proj-c", "窗口/参数已变更")
    assert affected and registry.get_run("proj-c")["status"] == "STALE"


def test_invalidation_preserves_history(registry: RunRegistry) -> None:
    """失效不删旧记录——run 文件仍保留历史状态字段。"""
    registry.register("proj-d", "run-1")
    registry.transition("proj-d", "READY")
    registry.transition("proj-d", "RUNNING")
    registry.transition("proj-d", "SUCCEEDED")
    invalidate_downstream(registry, "proj-d", "原因")
    rec = registry.get_run("proj-d")
    assert rec["status"] == "STALE"
    assert rec["run_id"] == "run-1"  # 历史身份保留，不再能用旧状态跑下游


def test_dependency_missing_reports_clear_error() -> None:
    p = {"inputs": {"libraries": [_lib_hifi()]}}
    assert dependency_unavailable(p, None)  # 无 manifest -> 明确报错


def test_dependency_missing_tools_report() -> None:
    p = {"inputs": {"libraries": [_lib_hifi()]}}
    manifest = {"software_versions": {"fastqc": "0.12.1"}}  # fastp/hifiasm/nextflow 缺
    problems = dependency_unavailable(p, manifest)
    assert len(problems) >= 1
    assert any("必需工具" in b for b in problems)


def _lib_hifi() -> dict:
    return {"library_id": "l", "technology": "hifi", "library_type": "wgs", "sample_role": "proband"}