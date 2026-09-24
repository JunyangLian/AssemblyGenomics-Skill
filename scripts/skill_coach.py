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
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import plan as plan_mod  # noqa: E402
from scripts.run_pitfall_checks import PITFALLS_DIR, _load_entries  # noqa: E402

# --- 数据识别（从文件名判断"有哪些数据"）------------------------------------

# (分类, 触发关键字、扩展名判定)
FASTA_EXT = (".fa", ".fas", ".fasta", ".fna", ".fa.gz", ".fasta.gz")
READ_EXT = (".fq", ".fastq", ".fq.gz", ".fastq.gz")


class _Ctx:
    def __init__(self, name: str):
        self.n = (name or "").lower()
        self.ext = ""
        for e in FASTA_EXT + READ_EXT:
            if self.n.endswith(e):
                self.ext = e
                self.base = self.n[: -len(e)]
                break
        else:
            self.base = self.n
        self._hic = self._kw(("hic", "hiseq"))
        self._rna = self._kw(("rna", "transcri"))
        self._wgs = self._kw(("wgs", "wholegenome", "pair"))
        self._hap = self._kw(("hap1", "hap2", "hap_1", "hap_2"))
        self._phased = self._kw(("phased", "phase", "subgenome", "dip", "tri"))

    def _kw(self, toks: tuple[str, ...]) -> bool:
        return any(t in self.n for t in toks)

    @property
    def read1(self) -> bool:
        return any(t in self.base for t in ("_r1", ".r1", "_1")) or self.base.endswith("1")

    @property
    def read2(self) -> bool:
        return any(t in self.base for t in ("_r2", ".r2", "_2")) or self.base.endswith("2")


def classify_filename(name: str) -> dict:
    """把单个文件名归类为 {kind, r1/r2, paired_possible}。kind∈{wgs_reads,hic_reads,rna_reads,assembly,other}"""
    c = _Ctx(name)
    is_read = c.n.endswith(READ_EXT)
    is_fa = c.n.endswith(FASTA_EXT)
    is_bam = c.n.endswith(".bam")
    if is_read and c._hic:
        return {"kind": "hic_reads", "read": "r1" if c.read1 else ("r2" if c.read2 else None)}
    if is_read and c._rna:
        return {"kind": "rna_reads", "read": "r1" if c.read1 else ("r2" if c.read2 else None)}
    if is_read:
        return {"kind": "wgs_reads", "read": "r1" if c.read1 else ("r2" if c.read2 else None)}
    if is_fa or is_bam:
        return {"kind": "assembly"}
    return {"kind": "other"}


def identify_data(filenames: list[str]) -> dict:
    """汇总整个文件清单：发现了哪些数据类别、是否有成对读段、缺口提示。"""
    seen: dict[str, int] = {}
    by_kind: dict[str, list[str]] = {}
    for fn in filenames:
        info = classify_filename(fn)
        by_kind.setdefault(info["kind"], []).append(fn)
        if info["kind"] in ("hic_reads", "rna_reads", "wgs_reads"):
            tec = {"hic_reads": "hic", "rna_reads": "rna_seq", "wgs_reads": "wgs"}[info["kind"]]
            seen[tec] = seen.get(tec, 0) + 1

    warnings: list[str] = []
    # 关键判断：BAM/assembly 不等于有可组装的读段；同类型读段需成对
    has_hic = "hic" in seen
    has_wgs = "wgs" in seen
    # 单倍型交付推断：装配文件名含 hap1/hap2 或 phased → 提示可能要求单倍型交付
    delivery_hint: str | None = None
    for asm_fn in by_kind.get("assembly", []):
        c = _Ctx(asm_fn)
        if c._hap or c._phased:
            delivery_hint = "phase_separated"
            break
    for kind_key in ("wgs_reads", "hic_reads", "rna_reads"):
        files = by_kind.get(kind_key) or []
        completions = [(f, classify_filename(f)["read"]) for f in files]
        r1 = any(r == "r1" for _, r in completions)
        r2 = any(r == "r2" for _, r in completions)
        if not (r1 and r2):
            tec = {"wgs_reads": "WGS", "hic_reads": "Hi-C", "rna_reads": "RNA"}[kind_key]
        if r1 and not r2:
            warnings.append(f"检测到{tec}读段只有 R1，缺 R2——双端文库不完整，无法配对")
        elif r2 and not r1:
            warnings.append(f"检测到{tec}读段只有 R2，缺 R1——双端文库不完整，无法配对")

    return {
        "discovered": seen,
        "has_hic": has_hic,
        "has_assembly": bool(by_kind.get("assembly")),
        "by_kind": by_kind,
        "delivery_hint": delivery_hint,
        "warnings": warnings,
        "unclassifiable": by_kind.get("other", []),
    }


# --- 由识别结果建 project dict（喂给 plan.route）-----------------------------

def build_project(identified: dict, delivery_repr: str | None = "primary_reference",
                  sample_ploidy: int | None = None) -> dict:
    libs: list[dict] = []
    idx = 0
    for tec, n in identified["discovered"].items():
        if n and tec == "hic":
            libs.append({"library_id": f"lib_hic{idx}", "technology": "illumina_hiseq_hic",
                         "library_type": "hic", "sample_role": "proband"})
            idx += 1
        elif n and tec == "wgs":
            libs.append({"library_id": f"lib_wgs{idx}", "technology": "illumina_wgs",
                         "library_type": "wgs", "sample_role": "proband"})
            idx += 1
        elif n and tec == "rna_seq":
            libs.append({"library_id": f"lib_rna{idx}", "technology": "illumina_wgs",
                         "library_type": "rna_seq", "sample_role": "proband"})
            idx += 1
    existing = None
    asm_files = identified.get("by_kind", {}).get("assembly") or []
    if asm_files:
        existing = {"path": asm_files[0], "format": "fasta",
                    "hash": None}  # hash 留空交由 plan 判定"来源完整性不可校验"
    sample: dict[str, Any] = {"id": "SAMPLE"}
    if sample_ploidy is not None:
        sample["ploidy"] = sample_ploidy
    project: dict[str, Any] = {
        "sample": sample,
        "input_type": "existing_assembly" if existing else "raw_reads",
        "inputs": {
            "libraries": libs,
            "existing_assembly": existing,
        },
        "delivery": {"representation": delivery_repr},
    }
    return project


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


def run_coach(filenames: list[str], delivery_repr: str | None = "primary_reference",
              ploidy: int | None = None) -> dict:
    identified = identify_data(filenames)
    # 单倍型交付推断优先：若文件名含 hap 且用户未显式指定，则采纳 hap(phase_separated)
    if identified.get("delivery_hint") and delivery_repr == "primary_reference":
        delivery_repr = identified["delivery_hint"]
    project = build_project(identified, delivery_repr=delivery_repr, sample_ploidy=ploidy)
    routed = plan_mod.route(project)
    entries = _load_entries(PITFALLS_DIR)

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
        "route_intent": routed["intent"],
        "delivery_repr_resolved": delivery_repr,
        "blockers": routed["blockers"],
        "recommendations": routed["recommendations"],
        "has_hic": identified["has_hic"],
        "data_warnings": identified["warnings"],
        "unclassifiable": identified["unclassifiable"],
        "observed_data": identified["discovered"],
        "steps": steps_out,
        "annotation_pitfall_hint": bool(annotation_entries),
    }


def _cli() -> int:
    p = argparse.ArgumentParser(description="新手向导：从原始文件清单生成分步 SOP + 每步坑位预警（雏形）")
    p.add_argument("files", nargs="+", help="原始文件名清单（新手把全部数据放进来）")
    p.add_argument("--repr", default="primary_reference",
                   help="交付表示（默认 primary_reference）")
    p.add_argument("--ploidy", type=int, default=None, help="倍性（默认不设，若 >2 会被 plan 阻断）")
    args = p.parse_args()

    res = run_coach(args.files, delivery_repr=args.repr, ploidy=args.ploidy)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())