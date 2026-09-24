#!/usr/bin/env python3
"""run 状态机 + 磁盘持久化 + 恢复逻辑。

状态以磁盘结构化记录为准，不以聊天历史为准。写入原子化，禁止同一项目重复提交。
状态词表与迁移（见 docs/plan-m0-m1.md）：

    PENDING -> READY -> RUNNING -> SUCCEEDED
    RUNNING -> FAILED / WAITING_REVIEW / BLOCKED
    WAITING_REVIEW -> READY / REJECTED
    常驻：SKIPPED_NOT_APPLICABLE、STALE
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_STATUS = {
    "PENDING", "READY", "RUNNING", "SUCCEEDED",
    "FAILED", "WAITING_REVIEW", "BLOCKED", "REJECTED",
    "SKIPPED_NOT_APPLICABLE", "STALE",
}

# 合法迁移边；未列出的迁移一律拒绝。
TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"READY", "BLOCKED", "SKIPPED_NOT_APPLICABLE"},
    "READY": {"RUNNING", "STALE"},
    "RUNNING": {"SUCCEEDED", "FAILED", "WAITING_REVIEW", "BLOCKED"},
    "WAITING_REVIEW": {"READY", "REJECTED", "STALE"},
    "FAILED": {"READY", "BLOCKED"},
    "REJECTED": {"READY"},
    "STALE": {"READY", "SKIPPED_NOT_APPLICABLE"},
    "SUCCEEDED": {"STALE"},
    "BLOCKED": set(),
    "SKIPPED_NOT_APPLICABLE": set(),
}

ACTIVE_STATUSES = frozenset({"PENDING", "READY", "RUNNING"})


def validate_transition(status: str, target: str) -> None:
    """校验迁移合法性；抛出 ValueError 并给出可用目标，而非静默拒绝。"""
    if status not in VALID_STATUS:
        raise ValueError(f"未知状态 {status!r}")
    if target not in VALID_STATUS:
        raise ValueError(f"未知目标状态 {target!r}")
    allowed = TRANSITIONS.get(status, set())
    if target not in allowed:
        choices = "、".join(sorted(allowed)) or "（无，终态）"
        raise ValueError(f"非法迁移 {status} -> {target}；该状态允许到：{choices}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_write_text(path: Path, text: str) -> None:
    """同目录写临时文件后 rename，保证要么全写要么不写。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


class RunRegistry:
    """run 状态与清单的磁盘持久化。根目录结构：

        <root>/<project_id>.run.json       # 每次 run 的状态记录
        <root>/<project_id>.manifest.json  # 关联组装清单
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _run_path(self, project_id: str) -> Path:
        return self.root / f"{project_id}.run.json"

    def _manifest_path(self, project_id: str, run_id: str) -> Path:
        return self.root / f"{project_id}__{run_id}.manifest.json"

    def register(self, project_id: str, run_id: str, manifest: dict | None = None) -> dict:
        """注册一个 run。已有活跃 run 时拒绝重复提交。返回新 run 记录。"""
        if not project_id or not run_id:
            raise ValueError("project_id 与 run_id 均不得为空")
        existing = self.get_run(project_id)
        if existing is not None and existing.get("status") in ACTIVE_STATUSES:
            raise ValueError(
                f"禁止重复提交：project {project_id!r} 已有活跃 run "
                f"{existing.get('run_id')!r}，状态 {existing.get('status')}"
            )
        rec = {
            "project_id": project_id,
            "run_id": run_id,
            "status": "PENDING",
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        atomic_write_text(self._run_path(project_id), json.dumps(rec, indent=2, ensure_ascii=False))
        if manifest is not None:
            atomic_write_text(
                self._manifest_path(project_id, run_id),
                json.dumps(manifest, indent=2, ensure_ascii=False),
            )
        return rec

    def get_run(self, project_id: str) -> dict | None:
        p = self._run_path(project_id)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def get_manifest(self, project_id: str, run_id: str) -> dict | None:
        p = self._manifest_path(project_id, run_id)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))

    def transition(self, project_id: str, target: str) -> dict:
        """对唯一 run 做状态迁移；并发下用读改写 + 原子写。"""
        rec = self.get_run(project_id)
        if rec is None:
            raise KeyError(f"project {project_id!r} 无 run 记录，无法迁移")
        current = rec["status"]
        validate_transition(current, target)
        rec["status"] = target
        rec["updated_at"] = utc_now()
        atomic_write_text(self._run_path(project_id), json.dumps(rec, indent=2, ensure_ascii=False))
        return rec

    def active_runs(self) -> list[dict]:
        """列出所有活跃 run（用于会话中断后恢复扫描）。"""
        out = []
        if not self.root.exists():
            return out
        for p in sorted(self.root.glob("*.run.json")):
            try:
                rec = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if rec.get("status") in ACTIVE_STATUSES:
                out.append(rec)
        return out

    def recover(self, project_id: str) -> dict | None:
        """恢复扫描：返回该 project 现存活跃/终态 run 的摘要。None 表示无记录可恢复。

        幂等：查询磁盘状态，不修改任何东西，避免会话中断后重复提交。
        """
        rec = self.get_run(project_id)
        if rec is None:
            return None
        manifest = self.get_manifest(project_id, rec["run_id"])
        return {"run": rec, "has_manifest": manifest is not None, "manifest": manifest}


def _cli() -> int:
    parser = argparse.ArgumentParser(description="run 状态机与持久化 CLI（供测试/接入用）")
    sub = parser.add_subparsers(dest="cmd", required=True)
    reg = sub.add_parser("register")
    reg.add_argument("--root", required=True)
    reg.add_argument("--project", required=True)
    reg.add_argument("--run", required=True)
    t = sub.add_parser("transition")
    t.add_argument("--root", required=True)
    t.add_argument("--project", required=True)
    t.add_argument("--to", required=True)
    r = sub.add_parser("recover")
    r.add_argument("--root", required=True)
    r.add_argument("--project", required=True)
    args = parser.parse_args()

    reg = RunRegistry(args.root)
    try:
        if args.cmd == "register":
            rec = reg.register(args.project, args.run)
            _emit(rec)
        elif args.cmd == "transition":
            _emit(reg.transition(args.project, args.to))
        else:
            _emit(reg.recover(args.project))
    except (ValueError, KeyError) as e:
        print(f"[blocked] {e}", file=__import__("sys").stderr)
        return 1
    return 0


def _emit(data: Any) -> None:
    if data is None:
        print("[ok] 无记录可恢复")
        return
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(_cli())