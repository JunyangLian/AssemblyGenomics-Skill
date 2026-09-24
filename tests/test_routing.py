"""M1 段 3 测试（一）：路由判定（test_routing）。

覆盖需求文档 14.2 必测情形的路由部分：
- 有/无 Hi-C 路由正确并记录原因
- 缺 R2、错误文库类型被阻断
- 倍性/交付表示未知时不擅自选择
- 多倍体未验证路径自动阻断
- 只有 Hi-C 无组装时阻断并给出可执行范围
"""
from __future__ import annotations

import pytest

from scripts.plan import route, SUPPORTED_COMBOS


def _base_project() -> dict:
    return {
        "project_id": "p",
        "sample": {"id": "s", "ploidy": 2, "mixed_sample": False},
        "delivery": {"representation": "primary_reference"},
        "inputs": {"libraries": [], "existing_assembly": None},
        "execution": {"backend": "sop_package"},
    }


def _lib(tech, ltype, reads=None, role="proband") -> dict:
    return {
        "library_id": "l",
        "technology": tech,
        "library_type": ltype,
        "read_files": reads or [],
        "sample_role": role,
    }


def test_has_hic_routes_to_scaffold() -> None:
    p = _base_project()
    p["inputs"]["libraries"] = [
        _lib("hifi", "wgs"),
        _lib("illumina_hiseq_hic", "hic"),
    ]
    r = route(p)
    assert r["intent"] == "assemble_and_scaffold"
    assert "hic_mapping" in [s["name"] for s in r["steps"]]
    assert r["blockers"] == []


def test_no_hic_routes_to_assemble_only_and_records_skip() -> None:
    p = _base_project()
    p["inputs"]["libraries"] = [_lib("hifi", "wgs")]
    r = route(p)
    assert r["intent"] == "assemble_only"
    assert r["has_hic"] is False
    names = [s["name"] for s in r["steps"]]
    assert "hic_mapping" not in names


def test_existing_assembly_routes_to_validate() -> None:
    p = _base_project()
    p["inputs"]["existing_assembly"] = {"path": "/x/a.fa", "hash": "a" * 64}
    p["inputs"]["libraries"] = [_lib("illumina_hiseq_hic", "hic")]
    r = route(p)
    assert r["intent"] == "existing_then_scaffold"


def test_missing_r2_blocked() -> None:
    p = _base_project()
    p["inputs"]["libraries"] = [
        _lib("illumina_wgs", "wgs", reads=["/x/sample_R1.fastq.gz"])
    ]
    r = route(p)
    assert r["intent"] == "blocked"
    assert any("R1 或 R2" in b for b in r["blockers"])


def test_unsupported_library_combo_blocked() -> None:
    assert ("illumina_wgs", "hic") not in SUPPORTED_COMBOS
    p = _base_project()
    p["inputs"]["libraries"] = [_lib("illumina_wgs", "hic")]  # 二代数错当 Hi-C
    r = route(p)
    assert r["intent"] == "blocked"
    assert any("文库类型不支持" in b for b in r["blockers"])


def test_unresolved_representation_not_silently_chosen() -> None:
    p = _base_project()
    p["inputs"]["libraries"] = [_lib("hifi", "wgs")]
    p["delivery"]["representation"] = "unresolved"
    r = route(p)
    assert r["intent"] == "blocked"
    assert any("不擅自选择" in b for b in r["blockers"])


def test_polyploid_untested_path_blocked() -> None:
    p = _base_project()
    p["inputs"]["libraries"] = [_lib("hifi", "wgs")]
    p["sample"]["ploidy"] = 4
    r = route(p)
    assert r["intent"] == "blocked"
    assert any("多倍体" in b for b in r["blockers"])


def test_mixed_sample_blocked() -> None:
    p = _base_project()
    p["inputs"]["libraries"] = [_lib("hifi", "wgs")]
    p["sample"]["mixed_sample"] = True
    r = route(p)
    assert r["intent"] == "blocked"


def test_hic_without_assembly_source_blocked_with_scope() -> None:
    p = _base_project()
    p["inputs"]["libraries"] = [_lib("illumina_hiseq_hic", "hic")]
    p["inputs"]["existing_assembly"] = None
    r = route(p)
    assert r["intent"] == "blocked"
    assert any("无任何可组装读段" in b for b in r["blockers"])
    assert any("补充长读段" in rec for rec in r["recommendations"])