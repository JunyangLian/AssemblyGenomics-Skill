#!/usr/bin/env python3
"""文献基线对照器："这个数正常吗？"

与陷阱库正交：pitfalls 探测过程（问"这步做对了吗"），本脚本对照结果
（问"这个数像话吗"）。

双层结构（D-016）：
1. 项目级锚点（权威）：intake 确定数据来源时一并选定可比参考文献/数据集
   （最近已发表同类），写入 project.yaml 的 baselines 节；metric_overrides
   优先于全局带。enforce 档要求 references ≥1 条带 accession/doi——选锚是
   intake 时的人类决策，1 条明确锚点即可，与全局 published 档的 ≥2 条门槛
   （防个案冒充共识）语义不同。
2. 类群兜底带（advisory）：knowledge/baselines/*.yaml 全局注册表，
   项目未覆盖的指标退回这里，仅提示。

诚实约束（代码强制）：
- 全局 enforce=true 必须 published 且 ≥2 条 doi/url，否则注册表校验失败。
- 项目 override 的 enforce=true 必须有 based_on 且项目带 references。
- 没有对应基线的指标如实报 unknown，不猜。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

BASELINES_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "baselines"

REQUIRED_KEYS = ("id", "metric", "taxon_scope", "unit", "expected_range",
                 "source_type", "enforce", "references")


def load_registry(directory: Path | None = None) -> list[dict]:
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML 未安装，无法解析基线注册表")
    directory = directory or BASELINES_DIR
    entries: list[dict] = []
    for p in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if not data:
            continue
        items = data if isinstance(data, list) else [data]
        for e in items:
            e.setdefault("_source", str(p))
            entries.append(e)
    return entries


def validate_registry(entries: list[dict]) -> list[str]:
    errs: list[str] = []
    for e in entries:
        src = e.get("_source")
        for k in REQUIRED_KEYS:
            if e.get(k) in (None, [], ""):
                errs.append(f"{src}[{e.get('id')}]: 缺少必需字段 {k!r}")
        rng = e.get("expected_range")
        if not (isinstance(rng, list) and len(rng) == 2
                and all(isinstance(x, (int, float)) for x in rng) and rng[0] < rng[1]):
            errs.append(f"{src}[{e.get('id')}]: expected_range 须为 [min, max] 且 min < max")
        if e.get("source_type") not in ("case_reference", "published"):
            errs.append(f"{src}[{e.get('id')}]: source_type 须为 case_reference|published")
        # enforce 门槛：published + ≥2 条带 doi/url 的引用
        if e.get("enforce") is True:
            refs = e.get("references") or []
            cited = [r for r in refs if isinstance(r, dict) and (r.get("doi") or r.get("url"))]
            if e.get("source_type") != "published" or len(cited) < 2:
                errs.append(
                    f"{src}[{e.get('id')}]: enforce=true 要求 source_type=published 且 "
                    f"≥2 条带 doi/url 的引用（当前 case/single-case 只能 advisory）"
                )
    return errs


def evaluate(metrics: dict[str, float], entries: list[dict],
             taxon: str | None = None) -> list[dict]:
    """对照一组 {指标名: 数值} 与基线，返回逐条判定。

    status ∈ {within, out_of_range, unknown_metric}；
    范围外时 enforce=true 报 warning，否则 info（advisory）。
    anchor ∈ {project_reference, clade_fallback, none}：判定依据的层级。
    """
    pool = [e for e in entries
            if taxon is None or e.get("taxon_scope") in (taxon, "any")]
    verdicts: list[dict] = []
    known = set()
    for e in pool:
        metric = e["metric"]
        known.add(metric)
        if metric not in metrics:
            continue
        value = metrics[metric]
        lo, hi = e["expected_range"]
        if lo <= value <= hi:
            status, sev = "within", "info"
        else:
            status = "out_of_range"
            sev = "warning" if e.get("enforce") is True else "info"
        verdicts.append({
            "id": e.get("id"), "metric": metric, "value": value,
            "expected_range": [lo, hi], "unit": e.get("unit"),
            "taxon_scope": e.get("taxon_scope"),
            "status": status, "severity": sev,
            "anchor": e.get("_anchor", "clade_fallback"),
            "advisory_only": e.get("enforce") is not True,
            "notes": (e.get("notes") or "").strip(),
            "references": [r.get("text") for r in (e.get("references") or [])
                           if isinstance(r, dict)],
        })
    for metric in metrics:
        if metric not in known:
            verdicts.append({
                "id": None, "metric": metric, "value": metrics[metric],
                "expected_range": None, "unit": None, "taxon_scope": taxon,
                "status": "unknown_metric", "severity": "info",
                "anchor": "none",
                "advisory_only": True,
                "notes": "注册表中无此指标的基线——不猜，可按 README 流程补充条目。",
                "references": [],
            })
    return verdicts


# --- 项目级锚点（D-016：intake 阶段确定，权威于全局兜底带）-------------------

def load_project_baselines(project: dict) -> dict:
    """从 project dict 提取 baselines 节；缺省视为未选定。"""
    b = project.get("baselines") or {}
    return {
        "status": b.get("status") or "not_selected",
        "references": b.get("references") or [],
        "metric_overrides": b.get("metric_overrides") or [],
    }


def validate_project_overrides(pb: dict) -> list[str]:
    errs: list[str] = []
    refs = pb["references"]
    if pb["status"] == "selected" and not refs:
        errs.append("baselines.status=selected 但 references 为空——选定锚点须至少给出 1 条可比参考")
    for i, o in enumerate(pb["metric_overrides"]):
        rng = o.get("expected_range") or []
        if not (isinstance(rng, list) and len(rng) == 2
                and all(isinstance(x, (int, float)) for x in rng) and rng[0] < rng[1]):
            errs.append(f"metric_overrides[{i}]({o.get('metric')}): expected_range 须为 [min,max] 且 min<max")
        if o.get("enforce") is True and not (o.get("based_on") and refs):
            errs.append(
                f"metric_overrides[{i}]({o.get('metric')}): enforce=true 须有 based_on 且项目已给 "
                f"references（intake 选锚是人类决策，1 条带 accession/doi 的明确锚即可）"
            )
    return errs


def merge_entries(pb: dict, registry: list[dict],
                  taxon: str | None = None) -> list[dict]:
    """项目 overrides（anchor=project_reference）优先，覆盖同指标注册表条目；
    其余注册表条目按类群过滤后保留（anchor=clade_fallback）。"""
    merged: list[dict] = []
    overridden: set[str] = set()
    for o in pb["metric_overrides"]:
        ts = o.get("taxon_scope")
        if taxon is not None and ts not in (taxon, None):
            continue  # 该 override 不适用于当前类群
        overridden.add(o["metric"])
        notes = (o.get("notes") or "").strip()
        if o.get("based_on"):
            notes = (notes + " " if notes else "") + f"[based_on: {o['based_on']}]"
        merged.append({
            "id": None,
            "metric": o["metric"],
            "taxon_scope": ts or "any",
            "unit": o.get("unit") or "",
            "expected_range": o["expected_range"],
            "source_type": "project_reference",
            "enforce": bool(o.get("enforce")),
            "references": pb["references"],
            "notes": notes,
            "_anchor": "project_reference",
        })
    for e in registry:
        ts = e.get("taxon_scope")
        if taxon is not None and ts not in (taxon, "any"):
            continue
        if e["metric"] in overridden:
            continue
        copy = dict(e)
        copy.setdefault("_anchor", "clade_fallback")
        merged.append(copy)
    return merged


def _parse_kv(pairs: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for kv in pairs:
        if "=" not in kv:
            raise SystemExit(f"参数格式应为 metric=value，收到: {kv!r}")
        k, v = kv.split("=", 1)
        out[k.strip()] = float(v)
    return out


def _cli() -> int:
    p = argparse.ArgumentParser(
        description="文献基线对照：'这个数正常吗？'（范围外报警并解释合法/非法偏离）")
    p.add_argument("metrics", nargs="+", help="指标键值对，如 protein_coding_gene_count=23924")
    p.add_argument("--project", help="project.yaml/json：intake 选定的参考锚点优先于全局兜底带")
    p.add_argument("--taxon", help="类群（匹配条目 taxon_scope；缺省对全部条目）")
    p.add_argument("--dir", help="基线目录（默认 knowledge/baselines）")
    p.add_argument("--json", action="store_true", help="输出 JSON")
    args = p.parse_args()

    registry = load_registry(Path(args.dir) if args.dir else None)
    errs = validate_registry(registry)

    pb = {"status": "not_selected", "references": [], "metric_overrides": []}
    if args.project:
        doc_path = Path(args.project)
        if doc_path.suffix.lower() in (".yaml", ".yml"):
            project = yaml.safe_load(doc_path.read_text(encoding="utf-8"))
        else:
            project = json.loads(doc_path.read_text(encoding="utf-8"))
        pb = load_project_baselines(project or {})
        errs.extend(validate_project_overrides(pb))
    if errs:
        for e in errs:
            print(f"[基线配置错误] {e}", file=sys.stderr)
        return 2

    entries = merge_entries(pb, registry, taxon=args.taxon)
    verdicts = evaluate(_parse_kv(args.metrics), entries, taxon=args.taxon)
    if args.json:
        print(json.dumps({"baselines_status": pb["status"], "verdicts": verdicts},
                         ensure_ascii=False, indent=2))
        return 0

    print("=== 文献基线对照 ===")
    if pb["status"] != "selected":
        print("  [提示] 项目未选定参考锚点（intake 确定数据来源时应一并选定最近已发表同类）——"
              "以下仅类群兜底带（advisory）。")
    for v in verdicts:
        if v["status"] == "unknown_metric":
            print(f"  [未知指标] {v['metric']} = {v['value']}（无基线，不猜）")
            continue
        rng = f"[{v['expected_range'][0]}, {v['expected_range'][1]}] {v['unit'] or ''}".strip()
        flag = "OK " if v["status"] == "within" else ("GAP" if v["severity"] == "warning" else "注意")
        adv = "" if not v["advisory_only"] else "（advisory）"
        anchor = {"project_reference": "项目文献锚点",
                  "clade_fallback": "类群兜底带", "none": "无"}.get(v.get("anchor"), v.get("anchor"))
        print(f"  [{flag:>2}] {v['metric']} = {v['value']}，基线 {rng} [{anchor}]{adv}")
        if v["status"] == "out_of_range":
            print(f"        ↓ {v['notes']}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
