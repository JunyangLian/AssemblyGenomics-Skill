"""M1 段 1 测试：project 配置校验的通过/阻断路径。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = ROOT / "scripts" / "validate_project.py"
SCHEMA = ROOT / "schemas" / "project.schema.json"
FIXTURES = ROOT / "tests" / "fixtures"


def run_validator(doc: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(doc), "--schema", str(SCHEMA)],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "fixture, blocked",
    [
        ("project_valid.yaml", False),
        ("project_missing_representation.yaml", True),
        ("project_unresolved.yaml", True),
        ("project_missing_resources.yaml", True),
        ("project_mixed_roles.yaml", True),
        ("project_missing_parent.yaml", True),
    ],
)
def test_project_validation(fixture: str, blocked: bool) -> None:
    proc = run_validator(FIXTURES / fixture)
    if blocked:
        assert proc.returncode != 0, f"{fixture} 应被阻断，实际通过：\n{proc.stdout}{proc.stderr}"
        assert "[blocked]" in proc.stdout
    else:
        assert proc.returncode == 0, f"{fixture} 应通过，实际阻断：\n{proc.stdout}{proc.stderr}"


def test_blocked_errors_are_specific() -> None:
    """阻断原因应定位到字段路径，而非笼统错误。"""
    cases = {
        "project_missing_representation.yaml": "delivery.representation",
        "project_missing_resources.yaml": "execution.",
        "project_missing_parent.yaml": "parental_identity_required",
    }
    for fixture, needle in cases.items():
        proc = run_validator(FIXTURES / fixture)
        assert proc.returncode != 0
        assert needle in proc.stderr or needle in proc.stdout


def _write(tmp_path: Path, body: str) -> Path:
    doc = tmp_path / "project.yaml"
    doc.write_text(body, encoding="utf-8")
    return doc


_HEAD = """schema_version: 1
project_id: t
sample: {id: s}
delivery: {representation: primary_reference}
execution: {backend: sop_package, cpu_limit: 8, memory_gb_limit: 16, disk_gb_limit: 100}
"""


def test_multiple_rna_seq_proband_allowed(tmp_path):
    """同一样本的多条 RNA-seq 文库是合法重复证据，不按混样冲突阻断。"""
    doc = _write(tmp_path, _HEAD + """inputs:
  libraries:
    - {library_id: rna1, technology: illumina_wgs, library_type: rna_seq, sample_role: proband}
    - {library_id: rna2, technology: illumina_wgs, library_type: rna_seq, sample_role: proband}
""")
    proc = run_validator(doc)
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_multiple_wgs_proband_still_blocked(tmp_path):
    """组装源文库（wgs）多 proband 仍是混样冲突。"""
    doc = _write(tmp_path, _HEAD + """inputs:
  libraries:
    - {library_id: wgs1, technology: illumina_wgs, library_type: wgs, sample_role: proband}
    - {library_id: wgs2, technology: illumina_wgs, library_type: wgs, sample_role: proband}
""")
    proc = run_validator(doc)
    assert proc.returncode != 0
    assert "组装源文库" in proc.stdout