"""Smoke test：冻结流程 #001 的 adapter 通道契约（配置/模拟层）。

注意验证类型边界：
- 本测试用 **mock 工具** 驱动 adapter 通道与状态流转，验证的是"编排 + 产物捕获 +
  人工门控"逻辑，**不是** Juicer/3D-DNA/BUSCO 的真实生物学正确性。
- 真实工具执行与生物学质量属于小样本 smoke / 真实验证，需在服务器完成，见 validation_report。

默认以 pytest marker `smoke` 运行： `pytest -m smoke`。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.preflight import REQUIRED_TOOLS, probe_tools

pytestmark = pytest.mark.smoke


def _mock_run_draft(fasta_lines: list[str]) -> str:
    """mock 短读组装器：返回最小 draft FASTA（仅测编排，非真实组装）。"""
    return "".join(f">{c}\n{g}\n" for c, g in fasta_lines)


def test_draft_fasta_producible() -> None:
    fa = _mock_run_draft([("contig1", "ACGTACGTACGT"), ("contig2", "TTTTGGGGCCCC")])
    assert ">contig1" in fa
    assert ">contig2" in fa
    # GFA 脚手架在真实流程中来自 3D-DNA；此处仅验证 draft 可被构造
    assert fa.count("\n>") == 1


def test_frozen_flow_required_tools_defined() -> None:
    """冻结流程 #001 的 required 工具必须在预检清单中。
    注：SOAPdenovo-63mer 已在真实还原中移除（contig 已有，不重跑）；Juicer 记为手写流程。"""
    for tool in ("run-asm-pipeline.sh", "busco", "bwa", "samtools", "juicer_dpnII", "juicebox"):
        assert tool in REQUIRED_TOOLS, f"冻结流程缺少 required 工具 {tool}"
    # 已不使用/待确认项不得误列入 required
    assert "SOAPdenovo-63mer" not in REQUIRED_TOOLS


def test_probe_tools_reports_without_crash() -> None:
    """在本地（无这些工具）探测不崩溃，且如实报 found=False。"""
    tools = probe_tools({})
    assert "juicer_dpnII" in tools
    # 本地 Windows 通常无这些生物工具，断言其结构存在而非必然 found
    for name in ("fastp", "bwa"):
        assert "found" in tools[name]
        assert "required" in tools[name]


def test_annotation_tools_probed_and_flagged() -> None:
    """注释阶段（skill 接管目标）工具必须被探测并标记 phase=annotation。"""
    from scripts.preflight import ANNOTATION_TOOLS

    assert "maker" in ANNOTATION_TOOLS
    assert "RepeatMasker" in ANNOTATION_TOOLS
    assert "InterProScan" in ANNOTATION_TOOLS
    tools = probe_tools({})
    assert tools["maker"]["phase"] == "annotation"
    assert tools["RepeatMasker"]["required"] is True


def _versions_path() -> Path:
    return Path(__file__).parents[1] / "workflows/adapters/juicer_3ddna/versions.json"


def test_juicer_3ddna_versions_lock_human_gate() -> None:
    ver = json.loads(_versions_path().read_text(encoding="utf-8"))
    # 关键：Juicebox 必须标记为 human_gate=true 且位于 approved 后
    assert ver["tools"]["juicebox"]["human_gate"] is True
    assert ver["human_gate"]["after"] == "3d_dna_scaffold"
    assert ver["human_gate"]["required_state"] == "WAITING_REVIEW"
    # 3D-DNA/Juicer 不是人工门控
    assert ver["tools"]["3d-dna"]["human_gate"] is False
    assert ver["tools"]["juicer"]["human_gate"] is False


def test_hic_fastq_not_mistaken_for_hic_matrix() -> None:
    """数据识别教训：SM.hic_1.fq.gz 是 Hi-C READ 而非 .hic 矩阵。"""
    ver = json.loads(_versions_path().read_text(encoding="utf-8"))
    # constraint 声明 BAM 不得被误作组装源，呼应 Hi-C read→矩阵 须经 Juicer 生成
    assert "BAM 不默认等于组装源" in ver["constraint"]
    # 输入通道以读段（hic_r1/hic_r2）命名，而非 .hic 矩阵文件
    assert "hic_r1" in ver["channels"]["input"]
    assert "hic_r2" in ver["channels"]["input"]