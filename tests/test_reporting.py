"""M1 段 5 测试：报告如实输出（test_reporting）。

覆盖需求文档 14.2 必测情形的报告部分：
- 指标缺失、工具失败不被包装成正常通过
- 污染/细胞器候选不未经批准直接删除
- 交付表示在运行前明确，primary 不冒充分相结果
- 数字由结构化产物确定性提取，缺失如实显示
"""
from __future__ import annotations

import pytest

from scripts.summarize_results import METRICS, render_markdown, summarize


def _project(rep="primary_reference") -> dict:
    return {"delivery": {"representation": rep}, "inputs": {"libraries": []}}


def test_missing_metric_marked_not_fabricated() -> None:
    report = summarize(_project(), {"metrics": {"contig_n50": 12345}})
    assert report["metrics"]["contig_count"] == "未评估/无记录"
    assert report["metrics"]["total_bp"] == "未评估/无记录"
    assert report["metrics"]["contig_n50"] == 12345


def test_tool_failure_not_packed_as_pass() -> None:
    products = {"metrics": {}, "failures": ["busco_complete_single"]}
    report = summarize(_project(), products)
    assert report["metrics"]["busco_complete_single"] == "执行失败"
    assert report["clean"] is False
    assert "execution_failed" in report["judgement"]


def test_no_failure_full_metrics_clean() -> None:
    m = {k: 100 for k in METRICS}
    report = summarize(_project(), {"metrics": m})
    assert report["clean"] is True
    assert report["judgement"] == []


def test_pollution_not_deleted_without_approval() -> None:
    products = {"pollution_candidates": [{"id": "mito", "approved": False, "deleted": False}]}
    report = summarize(_project(), products)
    assert report["pollution"]["deleted_without_approval"] is False
    assert report["pollution"]["candidates"] == products["pollution_candidates"]


def test_pollution_illegal_delete_flagged() -> None:
    products = {"pollution_candidates": [{"id": "endo", "approved": False, "deleted": True}]}
    report = summarize(_project(), products)
    assert report["pollution"]["deleted_without_approval"] is True


def test_unresolved_representation_blocks_report() -> None:
    p = _project("unresolved")
    report = summarize(p, {"metrics": {}})
    assert report["blocked"] is True
    assert "未定义" in report["blocked_reason"]


def test_primary_does_not_claim_phased() -> None:
    products = {"phase_report": {"phased": True}}
    report = summarize(_project("primary_reference"), products)
    assert report.get("phase_warning", "") != ""
    assert "primary" in report["phase_warning"]


def test_primary_without_phasing_no_warning() -> None:
    products = {"phase_report": {"phased": False}}
    report = summarize(_project("primary_reference"), products)
    assert report.get("phase_warning") is None


def test_markdown_renders_lists_missing_as_is() -> None:
    report = summarize(_project(), {"metrics": {}})
    md = render_markdown(report)
    assert "未评估/无记录" in md
    assert "contig_count" in md