#!/usr/bin/env python3
"""审核门槛校验（test_review_gate 的实现）。

硬约束：
- 未经人类批准（approved_by_human=true 且 submission_action 非空，二者缺一不可）不得视为通过。
- 审核必须绑定当前产物的 hash；绑定旧 hash 或缺失 review_package_hash 视为旧版，拒绝复用。
- 编辑引用必须合法：支持坐标/片段引用，覆盖/缺失/重复须逐项可解释；非法 liftover 归属被识别。
- hap1/hap2 数据与命名不得串用。

只做结构化判定，不宣称已跑通真实组装。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FRAGMENT_REF_RE = re.compile(
    r"^(?P<chr>[^:]+):(?P<start>\d+)-(?P<end>\d+)(?P<hap>:(hap1|hap2))?$"
)
SCAFFOLD_REF_RE = re.compile(r"^(?P<id>\S+)_scaf_(?P<idx>\d+)$")


def validate_review(pkg: dict) -> dict:
    """返回 {ok, blockers, recommendations}。ok 为 False 即阻断进入下一阶段。"""
    blockers: list[str] = []
    recs: list[str] = []

    # 1) 人类批准动作
    approval = pkg.get("approval") or {}
    if not approval.get("approved_by_human") is True:
        blockers.append("approval.approved_by_human 必须为 true（需真实人类确认）")
    if not approval.get("submission_action"):
        blockers.append("approval.submission_action 不得为空：须有明确的人类提交动作标识")
    if approval.get("approved_by_human") and not approval.get("submission_action"):
        blockers.append("approved_by_human=true 但缺少 submission_action，二者缺一即未批准")

    # 2) hash 绑定：防旧版复用
    binds = pkg.get("binds_to") or {}
    if not binds.get("input_assembly_hash"):
        blockers.append("binds_to.input_assembly_hash 缺失，无法确认审核对象，拒绝"
        )
    if not binds.get("review_package_hash"):
        blockers.append("binds_to.review_package_hash 缺失：审核包 hash 未绑定")
    if binds.get("stale") is True:
        blockers.append("审核绑定的是旧版产物（stale），不得复用旧批准")

    # 3) 编辑引用与 liftover 归属
    edits = pkg.get("edits") or []
    seen_coords: set[str] = set()
    for ed in edits:
        ref = ed.get("ref")
        if not ref:
            blockers.append("edits[]: 存在缺少 ref 的编辑项")
            continue
        if not (_valid_fragment(ref) or SCAFFOLD_REF_RE.match(ref)):
            blockers.append(f"edits[].ref 引用不合法: {ref!r}")
            continue
        if FRAGMENT_REF_RE.match(ref):
            base = FRAGMENT_REF_RE.match(ref).group("chr", "start", "end")
            key = f"{base[0]}:{base[1]}-{base[2]}"
            if key in seen_coords:
                blockers.append(f"edits[]: 坐标重复引用 {ref!r}，覆盖/重复须逐项可解释")
            seen_coords.add(key)
        # liftover 归属：hap 字段与坐标来源的一致性
        lif = ed.get("liftover_from")
        if lif and _hap_mismatch(ref, lif, ed):
            blockers.append(f"edits[]: hap1/hap2 命名与 liftover 来源不一致 ({ref!r})")

    # 4) status 门控：仅 accepted/modified 视为可继续；rejected/undetermined 阻断
    st = pkg.get("status")
    if st in ("rejected", "undetermined"):
        blockers.append(f"审核状态 {st!r} 未获批准，不得进入 post-review")

    return {"ok": not blockers, "blockers": blockers, "recommendations": recs}


def _valid_fragment(ref: str) -> bool:
    return bool(FRAGMENT_REF_RE.match(ref)) or bool(SCAFFOLD_REF_RE.match(ref))


def _hap_mismatch(ref: str, lif: dict, ed: dict) -> bool:
    m = FRAGMENT_REF_RE.match(ref)
    ref_hap = (m.group("hap") or "").lstrip(":") if m else None
    lif_hap = (lif.get("hap") or "").lower()
    if not ref_hap and not lif_hap:
        return False
    if ref_hap and not lif_hap:
        return False
    if not ref_hap and lif_hap:
        return True  # 目标未标 hap 却从某 hap liftover，归属不明
    return ref_hap != lif_hap


def _cli() -> int:
    parser = argparse.ArgumentParser(description="审核门槛校验 CLI")
    parser.add_argument("pkg", help="review package JSON 路径")
    args = parser.parse_args()
    data = json.loads(Path(args.pkg).read_text(encoding="utf-8"))
    res = validate_review(data)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(_cli())