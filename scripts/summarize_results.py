#!/usr/bin/env python3
"""从结构化产物确定性提取指标生成汇总报告。

原则：
- 只从结构化记录取数，不臆造数字。
- 缺失/失败/不适用如实标注：missing -> "未评估/无记录"，tool_failed -> "执行失败"，na -> "不适用"。
- 工具失败、指标缺失不得被包装成"正常通过"。
- 交付表示需在运行前明确；primary 不得冒充分相结果。

本模块只做配置/模拟的报告生成，不宣称真实组装已通过。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

MARKERS = {
    "missing": "未评估/无记录",
    "tool_failed": "执行失败",
    "na": "不适用",
}

# 组装质量指标；BUSCO 需在门控中被如实解读，不单独作为通过证据。
METRICS = (
    "contig_count",
    "contig_n50",
    "total_bp",
    "busco_complete_single",
    "busco_complete_dup",
    "busco_fragmented",
    "busco_missing",
)


def summarize(project: dict, products: dict, state: dict | None = None) -> dict:
    """生成汇总报告。

    参数:
        project: 项目配置（须含已确定的 delivery.representation）。
        products: 结构化产物，形如 {"metrics": {...}, "failures": [...], "pollution_candidates": [...], "phase_report": {...}}。
        state: 可选的 run 状态，用于标注当前阶段。

    返回:
        report dict，含 representation、metrics（如实标注）、状态判定。
    """
    report: dict[str, Any] = {}

    # 交付表示必须在运行前明确；未明确视为阻断。
    rep = (project.get("delivery") or {}).get("representation")
    if rep in (None, "unresolved"):
        report["blocked"] = True
        report["blocked_reason"] = "delivery.representation 未定义，无法生成交付报告"
        report["representation"] = None
    else:
        report["blocked"] = False
        report["representation"] = rep

    # 指标：确定性提取 + 如实标注缺失/失败
    raw_metrics = products.get("metrics") or {}
    metrics_out: dict[str, Any] = {}
    for m in METRICS:
        val = raw_metrics.get(m)
        if isinstance(val, (int, float)):
            metrics_out[m] = val
        elif m in (products.get("failures") or []):
            metrics_out[m] = MARKERS["tool_failed"]
        elif val is None:
            metrics_out[m] = MARKERS["missing"]
        else:
            metrics_out[m] = MARKERS["na"]
    report["metrics"] = metrics_out

    # 汇报总判定
    judgements = []
    failed_markers = list((products.get("failures") or []))
    any_missing = any(v == MARKERS["missing"] for v in metrics_out.values())
    if failed_markers:
        judgements.append("execution_failed")
    if any_missing:
        judgements.append("metric_incomplete")
    report["judgement"] = judgements
    report["clean"] = (not failed_markers) and (not any_missing)

    # pollution/细胞器候选：不得未经批准直接删除
    pollution = products.get("pollution_candidates") or []
    report["pollution"] = {
        "candidates": pollution,
        "deleted_without_approval": any(c.get("deleted") and not c.get("approved") for c in pollution),
        "note": "细胞器/污染候选须经人工批准后才会删除" if pollution else None,
    }

    # 相分：primary 不得冒充分相结果
    phase = products.get("phase_report")
    if rep == "primary_reference" and phase and phase.get("phased"):
        report["phase_warning"] = "声明为 primary_reference 但产物声称已分相，标识冲突：需人工核实"

    report["state"] = (state or {}).get("status")
    return report


def render_markdown(report: dict) -> str:
    """把 report dict 渲染成 Markdown（report.md 模板）。"""
    lines = ["# 组装阶段汇总报告", ""]

    if report.get("blocked"):
        lines.append(f"**阻断：** {report['blocked_reason']}")
        return "\n".join(lines)

    lines.append(f"- 交付表示：`{report.get('representation')}`")
    if report.get("phase_warning"):
        lines.append(f"- ⚠ {report['phase_warning']}")
    lines.append("")
    lines.append("## 质量指标")
    lines.append("| 指标 | 值 |")
    lines.append("|---|---|")
    for k, v in report.get("metrics", {}).items():
        lines.append(f"| {k} | {v} |")
    lines.append("")

    if report.get("pollution", {}).get("candidates"):
        lines.append("## 污染 / 细胞器候选")
        for c in report["pollution"]["candidates"]:
            state = "（已批准删除）" if c.get("approved") else "（待人工批准，未删除）"
            lines.append(f"- {c.get('id')}: {c.get('desc')} {state}")
        lines.append("")

    lines.append("## 判定")
    if report.get("clean"):
        lines.append("- 本阶段无失败，指标完整。")
    else:
        if "execution_failed" in report.get("judgement", []):
            lines.append("- 存在执行失败，不视为通过。")
        if "metric_incomplete" in report.get("judgement", []):
            lines.append("- 存在指标缺失，如实标注，不推断通过。")
    if report.get("state"):
        lines.append(f"- 当前 run 状态：`{report['state']}`")
    return "\n".join(lines)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="汇总报告生成 CLI")
    parser.add_argument("--project", required=True, help="project.json")
    parser.add_argument("--products", required=True, help="products.json")
    parser.add_argument("--markdown", action="store_true", help="输出 Markdown 而非 JSON")
    args = parser.parse_args()

    project = json.loads(Path(args.project).read_text(encoding="utf-8"))
    products = json.loads(Path(args.products).read_text(encoding="utf-8"))
    report = summarize(project, products)
    if args.markdown:
        print(render_markdown(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report.get("blocked") else 1


if __name__ == "__main__":
    sys.exit(_cli())