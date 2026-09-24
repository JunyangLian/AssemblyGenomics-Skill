"""文献基线对照器测试。

- 注册表结构校验（缺字段 / 非法范围 / 非法 source_type）
- enforce 门槛：单案例（case_reference）不允许 enforce=true —— 防个案冒充共识
- 对照判定：范围内 within / 范围外 advisory=info / enforce 范围外=warning
- 未知指标如实报 unknown，不猜
- 项目真实基线注册表本身可加载且校验通过
- 用 Siganus 真实交付值回归（23,924 基因等应全部 within）
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import check_baselines as cb


def _entry(**over):
    e = {
        "id": "BASE-T", "metric": "m", "taxon_scope": "any", "unit": "x",
        "expected_range": [0, 100], "source_type": "case_reference",
        "enforce": False, "references": [{"text": "case", "doi": None}],
    }
    e.update(over)
    return e


def test_registry_missing_field():
    e = _entry()
    del e["unit"]
    assert any("unit" in x for x in cb.validate_registry([e]))


def test_registry_bad_range():
    assert cb.validate_registry([_entry(expected_range=[100, 0])])
    assert cb.validate_registry([_entry(expected_range=[50])])


def test_registry_bad_source_type():
    assert any("source_type" in x for x in cb.validate_registry([_entry(source_type="literature")]))


def test_enforce_requires_published_with_two_dois():
    """enforce 门槛：单案例或引用不足 → 注册表报错，不许冒充共识。"""
    errs = cb.validate_registry([_entry(enforce=True)])
    assert any("enforce" in x for x in errs)
    errs = cb.validate_registry([_entry(
        enforce=True, source_type="published",
        references=[{"text": "only one", "doi": "10.1/x"}])])
    assert any("enforce" in x for x in errs)
    ok = _entry(
        enforce=True, source_type="published",
        references=[{"text": "a", "doi": "10.1/x"}, {"text": "b", "url": "https://e"}])
    assert cb.validate_registry([ok]) == []


def test_evaluate_within_and_out():
    entries = [_entry(metric="m")]
    v = cb.evaluate({"m": 50}, entries)
    assert v[0]["status"] == "within"
    v = cb.evaluate({"m": 200}, entries)
    assert v[0]["status"] == "out_of_range"
    assert v[0]["severity"] == "info"      # advisory 档
    assert v[0]["advisory_only"] is True


def test_evaluate_enforced_gap_is_warning():
    e = _entry(metric="m", enforce=True, source_type="published",
               references=[{"text": "a", "doi": "10.1/x"}, {"text": "b", "doi": "10.1/y"}])
    v = cb.evaluate({"m": 200}, [e])
    assert v[0]["status"] == "out_of_range"
    assert v[0]["severity"] == "warning"
    assert v[0]["advisory_only"] is False


def test_evaluate_unknown_metric_reported():
    v = cb.evaluate({"no_such": 1}, [_entry()])
    assert v[0]["status"] == "unknown_metric"


def test_evaluate_taxon_filter():
    fish = _entry(id="BASE-F", metric="m", taxon_scope="actinopterygii")
    plant = _entry(id="BASE-P", metric="m", taxon_scope="eudicotyledons",
                   expected_range=[20000, 60000])
    v = cb.evaluate({"m": 10}, [fish, plant], taxon="actinopterygii")
    assert all(x["id"] != "BASE-P" for x in v)


def test_project_registry_loads_and_validates():
    entries = cb.load_registry()
    assert entries, "项目基线注册表应非空"
    assert cb.validate_registry(entries) == []


def test_siganus_real_delivery_values_within():
    """Siganus 真实交付值（use-case-002）应全部落在参考带内——首版种子的回归锚。"""
    entries = cb.load_registry()
    v = cb.evaluate({
        "protein_coding_gene_count": 23924,
        "annotation_busco_complete_pct": 97.4,
        "repeat_masked_pct": 11.98,
        "median_protein_length_aa": 418,
        "functional_any_annotated_pct": 86.09,
    }, entries, taxon="actinopterygii")
    assert len(v) == 5
    assert all(x["status"] == "within" for x in v), [x for x in v if x["status"] != "within"]


def test_siganus_default_params_symptom_would_flag():
    """PIT-002 修复前的 93.3% 仍在带内但偏低；异常低（如 70）应范围外提示。"""
    entries = cb.load_registry()
    v = cb.evaluate({"annotation_busco_complete_pct": 70}, entries, taxon="actinopterygii")
    assert v[0]["status"] == "out_of_range"
    assert "PIT-002" in v[0]["notes"] or "流程问题" in v[0]["notes"]


# --- 项目级锚点（D-016 双层设计）---------------------------------------------

def _project(**over):
    b = {
        "status": "selected",
        "references": [{"kind": "published_genome_annotation",
                        "organism": "Siganus canaliculatus",
                        "accession_or_doi": "GCA_053572195.1",
                        "why": "同种已发表染色体级注释"}],
        "metric_overrides": [
            {"metric": "protein_coding_gene_count", "expected_range": [20000, 28000],
             "enforce": True, "based_on": "GCA_053572195.1"},
        ],
    }
    b.update(over)
    return {"project_id": "p1", "baselines": b}


def test_project_override_priority_over_registry():
    """项目锚点带 [20000,28000]（enforce）优先于注册表 [15000,45000]（advisory）：
    40000 在注册带内但超出项目带 → 必须 GAP，anchor=project_reference。"""
    pb = cb.load_project_baselines(_project())
    entries = cb.merge_entries(pb, cb.load_registry(), taxon="actinopterygii")
    v = cb.evaluate({"protein_coding_gene_count": 40000}, entries, taxon="actinopterygii")
    assert len(v) == 1  # 注册表同指标条目被覆盖，不出现两条
    assert v[0]["anchor"] == "project_reference"
    assert v[0]["status"] == "out_of_range"
    assert v[0]["severity"] == "warning"
    assert v[0]["advisory_only"] is False


def test_project_anchor_within_reports_project_reference():
    pb = cb.load_project_baselines(_project())
    v = cb.evaluate({"protein_coding_gene_count": 23924},
                    cb.merge_entries(pb, cb.load_registry(), taxon="actinopterygii"),
                    taxon="actinopterygii")
    assert v[0]["status"] == "within"
    assert v[0]["anchor"] == "project_reference"


def test_uncovered_metric_falls_back_to_clade_band():
    """项目只覆盖基因数；BUSCO 等其余指标退回类群兜底带。"""
    pb = cb.load_project_baselines(_project())
    v = cb.evaluate({"annotation_busco_complete_pct": 97.4},
                    cb.merge_entries(pb, cb.load_registry(), taxon="actinopterygii"),
                    taxon="actinopterygii")
    assert v[0]["anchor"] == "clade_fallback"
    assert v[0]["status"] == "within"


def test_project_overrides_validation():
    errs = cb.validate_project_overrides(cb.load_project_baselines(
        _project(status="selected", references=[])))
    assert any("references 为空" in x for x in errs)
    errs = cb.validate_project_overrides(cb.load_project_baselines(_project(
        metric_overrides=[{"metric": "m", "expected_range": [10, 5], "enforce": True,
                           "based_on": "x"}])))
    assert any("expected_range" in x for x in errs)
    errs = cb.validate_project_overrides(cb.load_project_baselines(_project(
        metric_overrides=[{"metric": "m", "expected_range": [0, 10], "enforce": True}])))
    assert any("enforce" in x for x in errs)
    assert cb.validate_project_overrides(cb.load_project_baselines(_project())) == []


def test_project_absent_defaults_to_not_selected():
    pb = cb.load_project_baselines({"project_id": "p"})
    assert pb["status"] == "not_selected"
    assert pb["references"] == [] and pb["metric_overrides"] == []
    assert cb.validate_project_overrides(pb) == []


def test_metric_override_taxonomy_scoping():
    """override 限定其他类群时，不覆盖当前类群的注册表条目。"""
    pb = cb.load_project_baselines(_project(metric_overrides=[
        {"metric": "protein_coding_gene_count", "expected_range": [0, 10],
         "taxon_scope": "eudicotyledons", "enforce": True, "based_on": "x"}]))
    entries = cb.merge_entries(pb, cb.load_registry(), taxon="actinopterygii")
    v = cb.evaluate({"protein_coding_gene_count": 23924}, entries, taxon="actinopterygii")
    assert v[0]["anchor"] == "clade_fallback"  # 鱼类项目锚不适用于鸟/植物等
    assert v[0]["status"] == "within"


def test_siganus_project_anchor_example_passes_schema():
    """带 baselines 节的项目样例须通过 project schema 校验。"""
    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[1]
                         / "schemas" / "project.schema.json").read_text(encoding="utf-8"))
    project = _project()
    project.update({"schema_version": 1, "sample": {"id": "s1"},
                    "delivery": {}, "execution": {"backend": "sop_package"}})
    jsonschema.validate(project, schema)
