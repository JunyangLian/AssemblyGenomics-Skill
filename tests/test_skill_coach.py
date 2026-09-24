"""skill_coach 新手向导雏形测试：

- 数据识别：从文件名（含真实 SM-4_hic_all_1.fq.gz 样式）判断有哪些数据
- 双端不完整检测：只给 R1 缺 R2 → 提示；A_R1+B_R2 跨样本不算成对
- 路由：wgs+hic → assemble_and_scaffold；只有 hic → 阻断
- 每个 SOP 步至少带 pitfalls 字段；重复序列(注释)步能关联到 Dfam 陷阱库
- P0 语义（D-025）：BAM 不当 assembly；识别不了的 FASTQ 是 unknown 不是 WGS；
  hiseq 是平台名不是 Hi-C；交付表示缺省即阻断（不默认）；hap hint 不自动采纳
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


def test_classify_bam_not_assembly():
    """BAM 是比对产物不是组装源（scope-and-routing：BAM 不视作组装源）。"""
    assert sc.classify_filename("rna_sorted.bam")["kind"] == "bam"
    res = sc.run_coach(["rna.bam"], delivery_repr="primary_reference")
    assert res["route_intent"] == "blocked"
    assert res["observed_data"] == {}
    assert any("BAM 不视作组装源" in w for w in res["data_warnings"])


def test_classify_unlabeled_fastq_is_unknown():
    """无 WGS/Hi-C/RNA 证据的 FASTQ（ATAC/ChIP/裸命名）不得默认当 WGS。"""
    assert sc.classify_filename("sample_ATAC_R1.fastq.gz")["kind"] == "unknown_reads"
    assert sc.classify_filename("ChIP_R1.fastq.gz")["kind"] == "unknown_reads"
    assert sc.classify_filename("sample_R1.fastq.gz")["kind"] == "unknown_reads"


def test_hiseq_platform_name_not_hic():
    """hiseq 是 Illumina 平台名，不能作为 Hi-C 关键词。"""
    assert sc.classify_filename("Sample_HiSeq_R1.fastq.gz")["kind"] == "unknown_reads"
    fid = sc.identify_data(["Sample_HiSeq_R1.fastq.gz", "Sample_HiSeq_R2.fastq.gz"])
    assert fid["has_hic"] is False


def test_unknown_fastq_blocked_until_confirmed():
    res = sc.run_coach(["sample_R1.fastq.gz", "sample_R2.fastq.gz"],
                       delivery_repr="primary_reference")
    assert res["route_intent"] == "blocked"
    assert any("不得默认当作 WGS" in b for b in res["blockers"])
    assert res["unknown_reads"] == ["sample_R1.fastq.gz", "sample_R2.fastq.gz"]


def test_unknown_fastq_confirmed_as_wgs_routes():
    """显式 --assume-wgs 后按用户确认走 WGS 路线（technology_source 记 user_confirmed）。"""
    res = sc.run_coach(["sample_R1.fastq.gz", "sample_R2.fastq.gz"],
                       delivery_repr="primary_reference", assume_wgs=True)
    assert res["route_intent"] == "assemble_only"
    fid = sc.identify_data(["sample_R1.fastq.gz", "sample_R2.fastq.gz"])
    project = sc.build_project(fid, delivery_repr="primary_reference", assume_wgs=True)
    wgs = [l for l in project["inputs"]["libraries"] if l["library_type"] == "wgs"]
    assert wgs and wgs[0]["technology_source"] == "user_confirmed"
    assert len(wgs[0]["read_files"]) == 2


def test_repr_required_by_default_no_silent_choice():
    """交付表示缺省即阻断，不默认 primary_reference（"不得默认"是代码事实）。"""
    res = sc.run_coach(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz"])
    assert res["route_intent"] == "blocked"
    assert res["delivery_repr_resolved"] is None
    assert any("representation" in b for b in res["blockers"])


def test_identify_detects_hic_and_wgs():
    fid = sc.identify_data(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz",
                            "SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"])
    assert fid["has_hic"] is True
    assert "wgs" in fid["discovered"]
    assert fid["warnings"] == []


def test_identify_flags_missing_r2():
    fid = sc.identify_data(["SM_WGS_1.fq.gz"])
    assert any("R2" in w for w in fid["warnings"])


def test_cross_sample_r1_r2_not_paired():
    """A 的 R1 + B 的 R2 各自缺端：warning 提示 + 路由层硬阻断。"""
    fid = sc.identify_data(["A_WGS_R1.fq.gz", "B_WGS_R2.fq.gz"])
    assert any("R1" in w for w in fid["warnings"])
    project = sc.build_project(fid, delivery_repr="primary_reference")
    routed = plan_mod.route(project)
    assert routed["intent"] == "blocked"
    assert any("R1 或 R2" in b for b in routed["blockers"])


def test_build_project_keeps_read_files():
    """read_files 全量带入 library：路由层 R1/R2 硬阻断依赖它（层间信息不丢失）。"""
    fid = sc.identify_data(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz"])
    project = sc.build_project(fid, delivery_repr="primary_reference")
    wgs = [l for l in project["inputs"]["libraries"] if l["library_type"] == "wgs"]
    assert wgs and wgs[0]["read_files"]


def test_route_with_hic_only_blocked():
    fid = sc.identify_data(["SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"])
    project = sc.build_project(fid, delivery_repr="primary_reference")
    routed = plan_mod.route(project)
    assert routed["intent"] == "blocked"


def test_route_wgs_hic_scaffold():
    res = sc.run_coach(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz",
                        "SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"],
                       delivery_repr="primary_reference")
    assert res["route_intent"] == "assemble_and_scaffold"
    assert res["steps"]
    for s in res["steps"]:
        assert "pitfalls" in s
        assert "gate_note" in s


def test_annotation_suggested_step_carries_dfam_pitfall():
    """流程未含注释步时，应追加 annotation 建议步并挂上 Dfam 坑（silent-gap 种子）。
    代表"skill 做完后告诉新手：下一步做注释，且注释有个 Dfam 的坑"。"""
    res = sc.run_coach(["SM-4_hic_all_1.fq.gz", "SM-4_hic_all_2.fq.gz", "SM4b.hap1.clear.fa"],
                       delivery_repr="phase_separated")
    assert res["route_intent"] == "existing_then_scaffold"
    ann = [s for s in res["steps"] if s["name"] == "annotation"]
    assert ann, "应追加 annotation 建议步"
    assert ann[0]["status"] == "SUGGESTED"
    ids = {p["id"] for p in ann[0]["pitfalls"]}
    assert "PIT-001" in ids, "Dfam 坑应挂到注释建议步"
    assert ann[0]["pitfalls"][0]["has_auto_check"] is True


def test_coach_unclassifiable_collected():
    res = sc.run_coach(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz", "readme.txt"],
                       delivery_repr="primary_reference")
    assert "readme.txt" in res["unclassifiable"]


def test_coach_hap_hint_requires_explicit_repr():
    """hap1/hap2 文件名只产生 hint：未显式声明时阻断并提示确认，不自动采纳 phase_separated。"""
    res = sc.run_coach(["SM-4_hic_all_1.fq.gz", "SM-4_hic_all_2.fq.gz", "SM4b.hap1.clear.fa"])
    assert res["delivery_repr_resolved"] is None
    assert res["route_intent"] == "blocked"
    assert any("phase_separated" in r for r in res["recommendations"])
    assert any("representation" in b for b in res["blockers"])


def test_coach_hap_hint_conflict_with_explicit_choice_warns():
    """显式指定的交付表示与文件名 hint 冲突时给出人工核实警告（不阻断）。"""
    res = sc.run_coach(["SM4b.hap1.clear.fa"], delivery_repr="primary_reference")
    assert res["route_intent"] == "existing_only_validate"
    assert any("不一致" in w for w in res["data_warnings"])


def test_coach_ploidy_gt2_blocked():
    res = sc.run_coach(["SM_WGS_1.fq.gz", "SM_WGS_2.fq.gz",
                        "SM_hic_all_1.fq.gz", "SM_hic_all_2.fq.gz"],
                       delivery_repr="primary_reference", ploidy=3)
    assert res["route_intent"] == "blocked"
    assert any("ploidy" in b or "倍性" in b for b in res["blockers"])
