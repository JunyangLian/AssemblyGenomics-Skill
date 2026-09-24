#!/usr/bin/env python3
"""skill_coach.py —— 新手向导主入口（雏形）。

把现有零件（数据识别 / 路由 / 陷阱库 / preflight）串成对新手可执行的分步 SOP：
```
新手把全部原始数据放进来 → skill 判断有哪些数据 → 判定路由 → 输出分步 SOP，每步附带"有哪些坑"
```
对齐项目定位：skill 要"指定怎么做"，并在每步预警"能跑通但不完整"的静默缺口。

本模块不做真实计算；只做识别 + 路由 + 坑位编排（配置/模拟层）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import plan as plan_mod  # noqa: E402
from scripts.run_pitfall_checks import PITFALLS_DIR, _load_entries  # noqa: E402

# --- 数据识别（从文件名判断"有哪些数据"）------------------------------------
#
# 识别语义（D-025）：
# - BAM 不视作组装源（references/scope-and-routing.md），归 bam 类并提示人工明确用途
# - 无法识别文库类型的 FASTQ 归 unknown_reads：不得默认当作 WGS，须用户显式确认（--assume-wgs）
# - hiseq 是测序平台名，不作为 Hi-C 关键词；关键词一律按分隔符边界匹配，防子串误报
# - 文件名推断（如 hap1/hap2 → 单倍型交付）只产生 hint，不代替显式声明

FASTA_EXT = (".fa", ".fas", ".fasta", ".fna", ".fa.gz", ".fasta.gz")
READ_EXT = (".fq", ".fastq", ".fq.gz", ".fastq.gz")

_HIC_RE = re.compile(r"(?:^|[_.\-])hi[-_]?c(?:[_.\-]|$)")
_RNA_RE = re.compile(r"(?:^|[_.\-])rna(?:[_.\-]|$)|transcri")
_WGS_RE = re.compile(r"(?:^|[_.\-])(?:wgs|whole[-_]?genome)(?:[_.\-]|$)")
_HAP_RE = re.compile(
    r"(?:^|[_.\-])(?:hap[_.\-]?[12]|phased|phase[_.\-]?separated|subgenome|diploid|triploid)(?:[_.\-]|$)"
)

# kind → discovered 键（technology 缩写）
_KIND_TEC = (("hic_reads", "hic"), ("rna_reads", "rna_seq"), ("wgs_reads", "wgs"))
_TEC_LABEL = {"wgs": "WGS", "hic": "Hi-C", "rna_seq": "RNA"}


def classify_filename(name: str) -> dict:
    """把单个文件名归类为 {kind, read}。

    kind ∈ {wgs_reads, hic_reads, rna_reads, unknown_reads, assembly, bam, other}
    - unknown_reads：FASTQ 但文件名无 WGS/Hi-C/RNA 证据（如 sample_R1.fastq.gz、ATAC/ChIP 数据）——
      不得默认当 WGS，须显式确认后才能作为组装源
    - bam：BAM 是比对产物不是组装源，只提示人工明确用途
    """
    n = (name or "").lower()
    if n.endswith(READ_EXT):
        if _HIC_RE.search(n):
            kind = "hic_reads"
        elif _RNA_RE.search(n):
            kind = "rna_reads"
        elif _WGS_RE.search(n):
            kind = "wgs_reads"
        else:
            kind = "unknown_reads"
        return {"kind": kind, "read": plan_mod.read_tag(name)}
    if n.endswith(FASTA_EXT):
        return {"kind": "assembly", "read": None}
    if n.endswith(".bam"):
        return {"kind": "bam", "read": None}
    return {"kind": "other", "read": None}


def identify_data(filenames: list[str]) -> dict:
    """汇总整个文件清单：发现了哪些数据类别、按样本前缀的 R1/R2 配对缺口、无法识别项。"""
    by_kind: dict[str, list[str]] = {}
    for fn in filenames:
        by_kind.setdefault(classify_filename(fn)["kind"], []).append(fn)

    discovered: dict[str, int] = {}
    for kind, tec in _KIND_TEC:
        files = by_kind.get(kind) or []
        if files:
            discovered[tec] = len(files)

    warnings: list[str] = []
    # R1/R2 按样本前缀配对：A_R1 + B_R2 不算成对（旧逻辑只看"有没有出现 R1/R2"，多样本会漏判）
    for kind, tec in _KIND_TEC:
        files = by_kind.get(kind) or []
        by_prefix: dict[str, set[str]] = {}
        for f in files:
            tag = plan_mod.read_tag(f)
            if tag:
                by_prefix.setdefault(plan_mod.sample_prefix(f), set()).add(tag)
        label = _TEC_LABEL[tec]
        for prefix in sorted(by_prefix):
            tags = by_prefix[prefix]
            if "r1" in tags and "r2" not in tags:
                warnings.append(f"检测到{label}读段 [{prefix}] 只有 R1 缺 R2——双端文库不完整，无法配对")
            elif "r2" in tags and "r1" not in tags:
                warnings.append(f"检测到{label}读段 [{prefix}] 只有 R2 缺 R1——双端文库不完整，无法配对")

    bam_files = by_kind.get("bam") or []
    if bam_files:
        warnings.append(
            f"BAM 不视作组装源（{len(bam_files)} 个 .bam）：如需使用其中的比对结果，请人工明确其用途"
        )

    # 单倍型交付 hint：只作为候选提示，不代替显式声明（D-025）
    delivery_hint: str | None = None
    for asm_fn in by_kind.get("assembly") or []:
        if _HAP_RE.search(asm_fn or ""):
            delivery_hint = "phase_separated"
            break

    return {
        "discovered": discovered,
        "has_hic": "hic" in discovered,
        "has_assembly": bool(by_kind.get("assembly")),
        "by_kind": by_kind,
        "delivery_hint": delivery_hint,
        "warnings": warnings,
        "unknown_reads": by_kind.get("unknown_reads") or [],
        "unclassifiable": by_kind.get("other") or [],
    }


# --- 由识别结果建 project dict（喂给 plan.route）-----------------------------

def build_project(identified: dict, delivery_repr: str | None = None,
                  sample_ploidy: int | None = None, assume_wgs: bool = False) -> dict:
    """由识别结果建 project dict（喂给 plan.route）。

    - delivery_repr 默认 None（=未声明）：交付表示必须显式给出，不默认 primary_reference（D-025）
    - read_files 全量带入 library：路由层的 R1/R2 硬阻断依赖它（此前只在前层出 warning、
      后层看不到原始文件，属于层间信息丢失）
    - assume_wgs=True：用户显式确认把 unknown_reads 当 WGS（technology_source 记 user_confirmed）
    """
    by_kind = identified.get("by_kind") or {}
    libs: list[dict] = []

    wgs_files = list(by_kind.get("wgs_reads") or [])
    unknown = list(identified.get("unknown_reads") or [])
    if assume_wgs and unknown:
        wgs_files += unknown
    if wgs_files:
        source = "user_confirmed" if (assume_wgs and unknown) else "filename_inferred"
        libs.append({
            "library_id": "lib_wgs",
            "technology": "illumina_wgs",
            "technology_source": source,
            "library_type": "wgs",
            "read_files": sorted(wgs_files),
            "sample_role": "proband",
        })

    hic_files = by_kind.get("hic_reads") or []
    if hic_files:
        libs.append({
            "library_id": "lib_hic",
            "technology": "illumina_hiseq_hic",
            "technology_source": "filename_inferred",
            "library_type": "hic",
            "read_files": sorted(hic_files),
            "sample_role": "proband",
        })

    rna_files = by_kind.get("rna_reads") or []
    if rna_files:
        libs.append({
            "library_id": "lib_rna",
            "technology": "illumina_wgs",
            "technology_source": "filename_inferred",
            "library_type": "rna_seq",
            "read_files": sorted(rna_files),
            "sample_role": "proband",
        })

    existing = None
    asm_files = by_kind.get("assembly") or []
    if asm_files:
        existing = {"path": asm_files[0], "format": "fasta",
                    "hash": None}  # hash 留空交由 plan 判定"来源完整性不可校验"
    sample: dict[str, Any] = {"id": "SAMPLE"}
    if sample_ploidy is not None:
        sample["ploidy"] = sample_ploidy
    return {
        "sample": sample,
        "input_type": "existing_assembly" if existing else "raw_reads",
        "inputs": {
            "libraries": libs,
            "existing_assembly": existing,
        },
        "delivery": {"representation": delivery_repr},
    }


# --- 每步坑位铺排（把陷阱库按 phase/step 挂到 SOP 步骤）-----------------------

def _pits_for(step: dict, entries: list[dict]) -> list[dict]:
    """把陷阱库条目里 phase/step 与该 SOP 步匹配的挑出来。无匹配则提示无已知坑。"""
    name = step["name"]
    phase_hint = {
        "assembly": "assembly",
        "validate_existing": "assembly",
        "hic_mapping": "hic",
        "scaffolding": "hic",
        "annotation": "annotation",
    }.get(name, name)
    matched = [e for e in entries if e.get("phase") == phase_hint or e.get("step") == step.get("step")]
    return matched


# --- 主入口：把识别 + 路由 + 坑位编排成新手 SOP ------------------------------

SOP_STEP_TITLE = {
    "assembly": "组装 contig（把测序读段拼成 contig）",
    "validate_existing": "校验既有组装（先核对你已有的 .fa/.fasta）",
    "hic_mapping": "Hi-C 比对（把 Hi-C 读段比对回 contig）",
    "scaffolding": "3D-DNA 挂载 + Juicebox 人工调图（硬性人工闸口）",
    "annotation": "结构注释 + 功能注释",
}


def run_coach(filenames: list[str], delivery_repr: str | None = None,
              ploidy: int | None = None, assume_wgs: bool = False) -> dict:
    identified = identify_data(filenames)
    project = build_project(identified, delivery_repr=delivery_repr,
                            sample_ploidy=ploidy, assume_wgs=assume_wgs)
    routed = plan_mod.route(project)
    entries = _load_entries(PITFALLS_DIR)

    # --- intake 层阻断：plan 看不到的原始信息在这里拦，不静默降级 ---
    intake_blockers: list[str] = []
    unknown = identified.get("unknown_reads") or []
    if unknown and not assume_wgs:
        shown = ", ".join(unknown[:3]) + ("…" if len(unknown) > 3 else "")
        intake_blockers.append(
            f"检测到 {len(unknown)} 个无法识别文库类型的 FASTQ（{shown}）："
            "不得默认当作 WGS——请显式确认（--assume-wgs）或按规范命名（如 sample_WGS_R1.fq.gz）后重跑"
        )

    recommendations = list(routed["recommendations"])
    data_warnings = list(identified["warnings"])
    # 单倍型 hint 只提示，不代替显式声明；与显式选择冲突时警告人工核实
    hint = identified.get("delivery_hint")
    if hint:
        if delivery_repr is None:
            recommendations.append(
                f"文件名暗示单倍型交付（{hint}）：请显式 --repr {hint} 确认后再路由，不自动采纳"
            )
        elif delivery_repr != hint:
            data_warnings.append(
                f"文件名暗示单倍型交付（{hint}），与显式指定的 {delivery_repr} 不一致——请人工核实"
            )

    blockers = list(routed["blockers"]) + intake_blockers
    route_intent = "blocked" if intake_blockers else routed["intent"]

    steps: list[dict] = list(routed["steps"])
    # 注释阶段是 skill 当前接管目标：流程未含注释步时，若陷阱库有 annotation 条目，
    # 追加一个"后续结构+功能注释"建议步，让 Dfam 这类坑有挂靠点，提醒新手别漏。
    annotation_entries = [e for e in entries if e.get("phase") == "annotation"]
    step_names = {s["name"] for s in steps}
    if annotation_entries and "annotation" not in step_names:
        steps.append({"name": "annotation", "status": "SUGGESTED", "gate": None})

    steps_out: list[dict] = []
    for i, s in enumerate(steps, 1):
        step = dict(s)
        step["title"] = SOP_STEP_TITLE.get(s["name"], s["name"])
        step["gate_note"] = ("⛔ 必须人工（Juicebox/审核）" if s.get("gate") else "自动（但每步留意下面的坑）")
        pits = _pits_for(s, entries)
        step["pitfalls"] = [
            {
                "id": p["id"],
                "title": p["title"],
                "severity": p["severity"],
                "symptom": (p.get("symptom") or "").strip(),
                "has_auto_check": bool(p.get("check")),
            }
            for p in pits
        ]
        step["step_no"] = i
        steps_out.append(step)

    return {
        "route_intent": route_intent,
        "delivery_repr_resolved": delivery_repr,
        "blockers": blockers,
        "recommendations": recommendations,
        "has_hic": identified["has_hic"],
        "data_warnings": data_warnings,
        "unclassifiable": identified["unclassifiable"],
        "unknown_reads": identified["unknown_reads"],
        "observed_data": identified["discovered"],
        "steps": steps_out,
        "annotation_pitfall_hint": bool(annotation_entries),
    }


def _cli() -> int:
    p = argparse.ArgumentParser(description="新手向导：从原始文件清单生成分步 SOP + 每步坑位预警（雏形）")
    p.add_argument("files", nargs="+", help="原始文件名清单（新手把全部数据放进来）")
    p.add_argument("--repr", default=None,
                   help="交付表示（primary_reference / phase_separated）：必须显式指定；缺省即阻断，不默认")
    p.add_argument("--assume-wgs", action="store_true",
                   help="显式确认：把无法识别类型的 FASTQ 当作 WGS（识别不了≠默认是，用户承担确认责任）")
    p.add_argument("--ploidy", type=int, default=None, help="倍性（默认不设，若 >2 会被 plan 阻断）")
    args = p.parse_args()

    res = run_coach(args.files, delivery_repr=args.repr, ploidy=args.ploidy,
                   assume_wgs=args.assume_wgs)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())