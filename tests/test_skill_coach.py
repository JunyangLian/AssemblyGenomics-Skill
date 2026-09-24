"""skill_coach 新手向导雏形测试：

- 数据识别：从文件名（含真实 SM-4_hic_all_1.fq.gz 样式）判断有哪些数据
- 双端不完整检测：只给 R1 缺 R2 → 提示
- 路由：wgs+hic → assemble_and_scaffold；只有 hic → 阻断
- 每个 SOP 步至少带 pitfalls 字段；重复序列(注释)步能关联到 Dfam 陷阱库
- 全程可离线（不依赖真实工具/服务器）
"""
from __future__ import annotations

from scripts import skill_coach as sc
from scripts import plan as plan_mod


def test_classify_types():
    assert sc.classify_filename("SM_WGS_1.fq.gz")["kind"] == "wgs_reads"
    assert sc.classify_filename("SM_hic_all_2.fq.gz")["kind"] == "hic_reads"
    assert sc.classify_filename("SM_RNA_1.fq.gz")["kind"] == "rna_reads"
    assert sc.classify_filename("hap1.clear.fa")["kind"] == "assembly"
    assert sc.classify_filename("notes.txt")["kind"] == "other"


def test_identify_detects_hic_and_wgs():
    fid = sc.identify_data(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz",
                            "SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"])
    assert fid["has_hic"] is True
    assert "wgs" in fid["discovered"]
    assert fid["warnings"] == []


def test_identify_flags_missing_r2():
    fid = sc.identify_data(["SM_WGS_1.fq.gz"])
    assert any("R2" in w for w in fid["warnings"])


def test_route_with_hic_only_blocked():
    fid = sc.identify_data(["SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"])
    project = sc.build_project(fid, delivery_repr="primary_reference")
    routed = plan_mod.route(project)
    assert routed["intent"] == "blocked"


def test_route_wgs_hic_scaffold():
    fid = sc.identify_data(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz",
                            "SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"])
    res = sc.run_coach(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz",
                        "SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"])
    assert res["route_intent"] == "assemble_and_scaffold"
    assert res["steps"]
    for s in res["steps"]:
        assert "pitfalls" in s
        assert "gate_note" in s


def test_annotation_suggested_step_carries_dfam_pitfall():
    """流程未含注释步时，应追加 annotation 建议步并挂上 Dfam 坑（silent-gap 种子）。
    代表"skill 做完后告诉新手：下一步做注释，且注释有个 Dfam 的坑"。"""
    res = sc.run_coach(["SM-4_hic_all_1.fq.gz", "SM-4_hic_all_2.fq.gz", "SM4b.hap1.clear.fa"])
    ann = [s for s in res["steps"] if s["name"] == "annotation"]
    assert ann, "应追加 annotation 建议步"
    assert ann[0]["status"] == "SUGGESTED"
    ids = {p["id"] for p in ann[0]["pitfalls"]}
    assert "PIT-001" in ids, "Dfam 坑应挂到注释建议步"
    assert ann[0]["pitfalls"][0]["has_auto_check"] is True


def test_coach_unclassifiable_collected():
    res = sc.run_coach(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz", "readme.txt"])
    assert "readme.txt" in res["unclassifiable"]


def test_coach_hap_name_infers_phase_separated():
    res = sc.run_coach(["SM-4_hic_all_1.fq.gz", "SM-4_hic_all_2.fq.gz", "SM4b.hap1.clear.fa"])
    assert res["delivery_repr_resolved"] == "phase_separated"


def test_coach_ploidy_gt2_blocked():
    res = sc.run_coach(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz",
                        "SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"], ploidy=3)
    assert res["route_intent"] == "blocked"
    assert any("ploidy" in b or "倍性" in b for b in res["blockers"])