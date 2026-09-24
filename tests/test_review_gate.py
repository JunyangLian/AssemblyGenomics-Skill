"""M1 段 4 测试：审核门槛（test_review_gate）。

覆盖需求文档 14.2 必测情形的审核部分：
- 未经人类批准不得进入 post-review 或交付
- 旧 review（hash 绑定失败/版本不一致）被识别为不可复用
- 错用 liftover、错误片段或坐标被识别
- 合法拆分的编辑可通过，不被粗糙 ID 校验误判
- hap1/hap2 数据与命名不串用
"""
from __future__ import annotations

import pytest

from scripts.validate_review import validate_review


def _good_review() -> dict:
    return {
        "review_round_id": "r1",
        "project_id": "p",
        "sample": "s",
        "assembly_identity": "hap1/round_001",
        "upstream_route": "juicer-3ddna",
        "status": "accepted",
        "binds_to": {"input_assembly_hash": "a" * 64, "review_package_hash": "b" * 64},
        "edits": [{"ref": "chr1:100-200"}],
        "approval": {"approved_by_human": True, "submission_action": "juicebox_session_xyz"},
    }


def test_human_approved_passes() -> None:
    assert validate_review(_good_review())["ok"] is True


def test_not_approved_by_human_blocked() -> None:
    p = _good_review()
    p["approval"]["approved_by_human"] = False
    res = validate_review(p)
    assert res["ok"] is False
    assert any("approved_by_human" in b for b in res["blockers"])


def test_missing_submission_action_blocked() -> None:
    """approved_by_human=true 但 submission_action 为空 -> 未批准（二者缺一）。"""
    p = _good_review()
    p["approval"]["submission_action"] = None
    res = validate_review(p)
    assert res["ok"] is False
    assert any("submission_action" in b for b in res["blockers"])


def test_status_rejected_blocked() -> None:
    p = _good_review()
    p["status"] = "rejected"
    assert validate_review(p)["ok"] is False


def test_status_undetermined_blocked() -> None:
    p = _good_review()
    p["status"] = "undetermined"
    assert validate_review(p)["ok"] is False


def test_stale_binding_blocked() -> None:
    """绑定旧版产物（stale）禁止复用旧批准。"""
    p = _good_review()
    p["binds_to"]["stale"] = True
    res = validate_review(p)
    assert res["ok"] is False
    assert any("旧版" in b for b in res["blockers"])


def test_missing_review_package_hash_blocked() -> None:
    p = _good_review()
    del p["binds_to"]["review_package_hash"]
    assert validate_review(p)["ok"] is False


def test_illegal_fragment_reference_blocked() -> None:
    p = _good_review()
    p["edits"] = [{"ref": "chr1:bad-location"}]  # 非坐标格式
    assert validate_review(p)["ok"] is False


def test_duplicate_coordinate_blocked() -> None:
    p = _good_review()
    p["edits"] = [{"ref": "chr1:100-200"}, {"ref": "chr1:100-200"}]
    res = validate_review(p)
    assert res["ok"] is False
    assert any("重复引用" in b for b in res["blockers"])


def test_legal_split_edits_pass() -> None:
    """合法拆分的编辑可通过，不被粗糙 ID 校验误判。"""
    p = _good_review()
    p["edits"] = [
        {"ref": "chr1:100-200"},
        {"ref": "chr2_scaf_3"},  # scaffold 级引用
    ]
    assert validate_review(p)["ok"] is True


def test_hap_mismatch_in_liftover_blocked() -> None:
    """hap1 坐标却从 hap2 liftover，命名串用被识别。"""
    p = _good_review()
    p["edits"] = [
        {
            "ref": "chr1:100-200:hap1",
            "liftover_from": {"hap": "hap2", "assembly": "x"},
        }
    ]
    res = validate_review(p)
    assert res["ok"] is False
    assert any("hap1/hap2" in b for b in res["blockers"])


def test_hap_consistent_liftover_passes() -> None:
    p = _good_review()
    p["edits"] = [
        {
            "ref": "chr1:100-200:hap1",
            "liftover_from": {"hap": "hap1", "assembly": "x"},
        }
    ]
    assert validate_review(p)["ok"] is True