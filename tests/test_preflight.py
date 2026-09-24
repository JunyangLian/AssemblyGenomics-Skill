"""M1+ (preflight) 测试：冻结流程 #001 环境预检。

覆盖：
- required 工具缺失被如实列为 blocker（本地环境通常缺 SOAPdenovo/Juicer/3D-DNA）
- 数据 R1/R2 配对完整 vs 未配对/缺失的识别（用 manifest）
- 资源探测不因单点失败崩溃
"""
from __future__ import annotations

import pytest

from scripts import preflight


def test_required_missing_tools_are_blockers() -> None:
    tools = {name: {"found": False, "required": True, "path": None}
             for name in ("fastp", "run-asm-pipeline.sh")}
    res = {"cpu_cores": 8, "mem_bytes": 1, "disk_free": 2}
    data = {"pairs": {}, "unpaired": [], "missing": []}
    report = preflight._summarize(tools, res, data)
    assert report["ok"] is False
    assert any("run-asm-pipeline.sh" in b for b in report["blockers"])


def test_all_required_found_passes() -> None:
    tools = {"fastp": {"found": True, "required": True, "path": "/x", "version": "0.23"}}
    res = {"cpu_cores": 8}
    data = {"pairs": {}, "unpaired": [], "missing": []}
    report = preflight._summarize(tools, res, data)
    assert report["ok"] is True


def test_optional_missing_does_not_block() -> None:
    tools = {"quast": {"found": False, "required": False, "path": None}}
    res = {"cpu_cores": 8}
    data = {"pairs": {}, "unpaired": [], "missing": []}
    report = preflight._summarize(tools, res, data)
    assert report["ok"] is True


def test_unpaired_fastq_blocked() -> None:
    tools = {}
    res = {"cpu_cores": 8}
    data = {"pairs": {}, "unpaired": [("SM1", ["SM1_1.fq.gz"])], "missing": []}
    report = preflight._summarize(tools, res, data)
    assert report["ok"] is False
    assert any("未配对" in b for b in report["blockers"])


def test_missing_data_file_blocked() -> None:
    tools = {}
    res = {"cpu_cores": 8}
    data = {"pairs": {}, "unpaired": [], "missing": ["/x/SM_1.fq.gz"]}
    report = preflight._summarize(tools, res, data)
    assert report["ok"] is False
    assert any("缺失" in b for b in report["blockers"])


def test_check_data_with_manifest_pairs_r1_r2(tmp_path) -> None:
    r1 = tmp_path / "SM_1.fq.gz"
    r2 = tmp_path / "SM_2.fq.gz"
    r1.write_bytes(b"x")
    r2.write_bytes(b"x")
    manifest = {"inputs": {"libraries": [
        {"id": "s1", "read1": str(r1), "read2": str(r2)}
    ]}}
    report = preflight.check_data(manifest, None)
    assert report["pairs"][str(r1)]["read2"] == str(r2)
    assert report["missing"] == []
    assert report["unpaired"] == []


def test_check_data_missing_manifest_pair(tmp_path) -> None:
    r1 = tmp_path / "SM_1.fq.gz"
    r1.write_bytes(b"x")
    manifest = {"inputs": {"libraries": [
        {"id": "s1", "read1": str(r1), "read2": str(tmp_path / "SM_2.fq.gz")}
    ]}}
    report = preflight.check_data(manifest, None)
    assert str(tmp_path / "SM_2.fq.gz") in report["missing"]
    assert report["pairs"].get(str(r1)) is not None


def test_probe_resources_does_not_crash() -> None:
    res = preflight.probe_resources()
    assert isinstance(res, dict)
    assert "cpu_cores" in res
    assert "platform" in res
    assert "scheduler" in res