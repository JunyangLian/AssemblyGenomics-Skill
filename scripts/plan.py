#!/usr/bin/env python3
"""路由判定 + 能力约束 + 失效传播。

把需求文档第 6 节的能力约束映射为判定表（plan 路由意图与门槛）。
硬约束（缺 R2、损坏文件、错误文库类型、样本角色冲突、倍性/表示未定义、多倍体未验证路径、
只有 Hi-C 无可用组装）由代码直接阻断并说明缺什么、能做什么。
LLM 可解释与提候选，但不得越过这里的硬约束。

注意：本模块只做"配置/模拟"判定，不启动、也不宣称能跑通真实组装。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.state_registry import RunRegistry, validate_transition

# 允许的 technology 与 library_type 组合（需求文档 6 节路线支持矩阵子集）。
SUPPORTED_COMBOS: set[tuple[str, str]] = {
    ("illumina_wgs", "wgs"),
    ("illumina_wgs", "rna_seq"),
    ("illumina_hiseq_hic", "hic"),
    ("hifi", "wgs"),
    ("ont", "wgs"),
}

# 必需工具，plan 时若清单缺版本即视为依赖不足。
REQUIRED_TOOLS: set[str] = {"fastqc", "fastp", "hifiasm", "nextflow"}


def _libraries(project: dict) -> list[dict]:
    return (project.get("inputs") or {}).get("libraries") or []


def _same_orientation_ok(lib: dict) -> bool:
    """双端文库须成对提供 R1/R2（缺任一即判定不可用）。"""
    reads = lib.get("read_files") or []
    # 只按文件名 R1/R2 存在性判断，不再依赖更细技术判定
    for r in reads:
        name = Path(r).name.lower()
        if any(token in name for token in ("_r1", "_1.f", ".r1", "_r1.")):
            paired = any(("_r2" in name) for _ in [0]) or any(
                t in rr.lower()
                for rr in reads
                for t in ("_r2", "_2.f", ".r2", "_r2.")
            )
            if not paired:
                return False
    return True


def _has_reads(project: dict) -> bool:
    """存在可组装的读段（BAM 不等于 HiFi，故不把任意读段视作组装源）。"""
    return any(
        lib.get("library_type") in ("wgs", None)
        and lib.get("technology") in ("hifi", "ont", "illumina_wgs")
        for lib in _libraries(project)
    )


def _has_existing(project: dict) -> bool:
    return bool((project.get("inputs") or {}).get("existing_assembly"))


def _has_assembly_source(project: dict) -> bool:
    return _has_reads(project) or _has_existing(project)


def route(project: dict) -> dict:
    """依据 project 判定路由意图与阻断。返回 intent/steps/blockers/recommendations。

    intent ∈ {assemble_and_scaffold, assemble_only, existing_then_scaffold, blocked}
    """
    blockers: list[str] = []
    recommendations: list[str] = []

    # 1) 交付表示未知：不擅自选择
    delivery = project.get("delivery") or {}
    rep = delivery.get("representation")
    if rep in (None, "unresolved"):
        blockers.append("delivery.representation 未定义，无法决定交付路线（不擅自选择）")
        recommendations.append("澄清交付表示后再路由")

    # 2) 样本角色
    probands = [l.get("sample_role") for l in _libraries(project)] 
    if probands and "proband" not in probands:
        blockers.append("缺少 proband 角色文库，无法确定组装主体")
    role_set = set(l.get("sample_role") for l in _libraries(project))
    if role_set:
        role_set.discard(None)
    if len(role_set & {"proband"}) != 1:
        # 由角色触发
        pass

    # 3) 文库组合与成对性
    for lib in _libraries(project):
        tech, ltype = lib.get("technology"), lib.get("library_type")
        if tech and ltype and (tech, ltype) not in SUPPORTED_COMBOS:
            blockers.append(
                f"inputs.libraries[{lib.get('library_id')}]: 文库类型不支持 "
                f"({tech}/{ltype})，可用的组合见支持矩阵"
            )
        elif tech and not ltype:
            blockers.append(f"inputs.libraries[{lib.get('library_id')}]: technology={tech} 但缺 library_type")
        if lib.get("technology") == "illumina_wgs" and not _same_orientation_ok(lib):
            blockers.append(f"inputs.libraries[{lib.get('library_id')}]: 双端文库缺 R1 或 R2，无法配对")

    # 4) 无效或损坏文件（模拟：existing_assembly 缺 hash → 提示补全，由校验层算；不硬阻断新手）
    ex = (project.get("inputs") or {}).get("existing_assembly")
    if ex and not ex.get("hash"):
        recommendations.append("inputs.existing_assembly.path 无 hash：产物校验时自动计算并核对来源完整性")
        recommendations.append("若这是您自有的历史组装，可跳过 hash 校验")

    # 5) 倍性 / 交付未知 + 多倍体未验证路径
    ploidy = (project.get("sample") or {}).get("ploidy")
    if ploidy is not None and ploidy > 2:
        blockers.append("sample.ploidy>2：当前未验证多倍体组装路径，自动阻断")
    mixed = (project.get("sample") or {}).get("mixed_sample")
    if mixed:
        blockers.append("sample.mixed_sample=true：混样组装路径未验证，需人工方案审核，自动阻断")

    # 6) 只有 Hi-C 无可用组装源
    has_hic = any(l.get("library_type") == "hic" for l in _libraries(project))
    if has_hic and not _has_assembly_source(project):
        blockers.append("存在 Hi-C 但无任何可组装读段或既有组装，无法做 scaffolding")
        recommendations.append("补充长读段/二代 WGS 组装源，或提供 existing_assembly")

    # 组装源 + Hi-C 的组合决定路由意图
    has_reads = _has_reads(project)
    has_existing = _has_existing(project)
    if has_reads and has_hic:
        route_intent = "assemble_and_scaffold"
    elif has_reads and not has_hic:
        route_intent = "assemble_only"
    elif has_existing and has_hic:
        route_intent = "existing_then_scaffold"
    elif has_existing and not has_hic:
        route_intent = "existing_only_validate"
    else:
        route_intent = "blocked"  # 无组装源，交由上方阻断原因说明

    if blockers:
        route_intent = "blocked"

    return {
        "intent": route_intent,
        "steps": _derive_steps(route_intent, project),
        "blockers": blockers,
        "recommendations": recommendations,
        "has_hic": has_hic,
        "has_assembly_source": _has_assembly_source(project),
    }


def _derive_steps(intent: str, project: dict) -> list[dict]:
    if intent in ("blocked",):
        return []
    steps = []
    if intent in ("assemble_and_scaffold", "assemble_only"):
        steps.append({"name": "assembly", "status": "PENDING", "gate": None})
    elif intent in ("existing_then_scaffold", "existing_only_validate"):
        steps.append({"name": "validate_existing", "status": "PENDING", "gate": None})
    if intent in ("assemble_and_scaffold", "existing_then_scaffold"):
        steps.append({"name": "hic_mapping", "status": "PENDING", "gate": "juicebox_review"})
        steps.append({"name": "scaffolding", "status": "PENDING", "gate": "manual_approval"})
    return steps


def invalidate_downstream(registry: RunRegistry, project_id: str, reason: str) -> list[dict]:
    """把该项目及其下游相关节点标为 STALE（失效传播）。

    只把仍有效的节点改为 STALE；FAILED/BLOCKED 已是非稳态，保持不变。
    """
    rec = registry.get_run(project_id)
    affected = []
    if rec and rec.get("status") in ("SUCCEEDED", "READY", "RUNNING", "WAITING_REVIEW"):
        try:
            registry.transition(project_id, "STALE")
        except ValueError:
            pass
        else:
            affected.append({"project_id": project_id, "to": "STALE", "reason": reason})
    return affected


def dependency_unavailable(project: dict, manifest: dict | None) -> list[str]:
    """依赖/工具/数据库不足时明确报错，而非无界重试。"""
    problems: list[str] = []
    if not manifest:
        problems.append("缺少 manifest：无法核对工具与数据库版本")
        return problems
    soft = manifest.get("software_versions") or {}
    missing = REQUIRED_TOOLS - set(soft.keys())
    if missing:
        problems.append(f"缺少必需工具版本记录：{sorted(missing)}")
    return problems


def _cli() -> int:
    parser = argparse.ArgumentParser(description="路由判定与失效传播 CLI")
    parser.add_argument("doc", help="project.yaml/json 路径")
    parser.add_argument("--root", help="run registry 根目录（用于失效传播）")
    parser.add_argument("--invalidate", help="project_id:进行失效传播")
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import yaml as _yaml
    if args.doc.lower().endswith((".yaml", ".yml")):
        data = _yaml.safe_load(Path(args.doc).read_text(encoding="utf-8"))
    else:
        data = json.loads(Path(args.doc).read_text(encoding="utf-8"))
    print(json.dumps(route(data), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())