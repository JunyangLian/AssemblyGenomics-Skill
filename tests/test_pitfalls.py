"""陷阱库校验器测试：覆盖静默缺口（能跑通但不完整）的识别。

- YAML 结构校验（缺字段 / severity 非法 / step 非整数）
- 自动检查：脚本输出含"缺口/GAP"关键词 → gap
- 脚本 exit 非零但未宣告缺口（环境失败）→ 不是 gap（需人工，不误报）
- 无 check / 空 check → 需人工（不判 gap，不臆断）
- cluster 入口加载 + 空库容错
"""
from __future__ import annotations

import pytest

from scripts import run_pitfall_checks as pc


def _mk(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(yaml_dump(data), encoding="utf-8")
    return p


def yaml_dump(data):
    import yaml

    return yaml.safe_dump(data, allow_unicode=True)


def test_validate_missing_field(tmp_path):
    e = {"_source": "x.yaml"}
    errs = pc._validate(e)
    assert any("id" in x for x in errs)


def test_validate_bad_severity(tmp_path):
    e = {"id": "PIT-X", "title": "t", "phase": "p", "step": 10,
         "severity": "fatal", "symptom": "s", "root_cause": "r"}
    errs = pc._validate(e)
    assert any("severity" in x for x in errs)


def test_validate_step_not_int(tmp_path):
    e = {"id": "PIT-X", "title": "t", "phase": "p", "step": "ten",
         "severity": "warning", "symptom": "s", "root_cause": "r"}
    errs = pc._validate(e)
    assert any("step" in x for x in errs)


def test_validate_step_zero_is_valid():
    """step=0 是合法值（跨阶段条目如 PIT-007），不得按缺失处理。"""
    e = {"id": "PIT-Z", "title": "t", "phase": "general", "step": 0,
         "severity": "warning", "symptom": "s", "root_cause": "r"}
    assert pc._validate(e) == []


def test_decide_gap_keyword_present():
    """脚本明确输出'缺口'关键词 → 判为缺口（返回 severity）。"""
    assert pc._decide_gap("缺口：库版本过旧", "warning", "bash", 0) == "warning"
    assert pc._decide_gap("GAP found", "critical", "bash", 0) == "critical"
    assert pc._decide_gap("gap detected", "critical", "bash", 0) == "critical"


def test_decide_gap_env_error_not_gap():
    """脚本执行失败但未宣告缺口（如环境不支持）→ 不是缺口，需人工。"""
    assert pc._decide_gap("'#' is not recognized", "warning", "fallback", 1) is None
    assert pc._decide_gap("", "warning", "fallback", 1) is None


def test_run_check_no_check_returns_manual():
    e = {"id": "PIT-4"}
    out, gap, engine = pc._run_check(e, {})
    assert gap is None
    assert engine == "manual"
    assert "人工" in out


def test_run_check_empty_source_manual():
    e = {"id": "PIT-5", "check": {"language": "shell", "source": ""}}
    out, gap, engine = pc._run_check(e, {})
    assert gap is None
    assert engine == "manual"


def test_run_all_loads_and_validates(tmp_path):
    (tmp_path / "01-a.yaml").write_text(yaml_dump(_NOSCRIPT), encoding="utf-8")
    (tmp_path / "02-b.yaml").write_text(yaml_dump(_NOSCRIPT2), encoding="utf-8")
    rep = pc.run_all(tmp_path)
    assert len(rep) == 2
    by_id = {r["id"]: r for r in rep}
    # 无脚本条目 → 不判 gap（需人工），且须结构有效
    assert by_id["PIT-002"]["gap"] is None
    assert by_id["PIT-003"]["gap"] is None
    assert all("error" not in (r.get("error") or []) for r in rep)


_NOSCRIPT = {
    "id": "PIT-002", "title": "无自动检查 A", "phase": "p",
    "step": 11, "severity": "info", "symptom": "s", "root_cause": "r",
}
_NOSCRIPT2 = {
    "id": "PIT-003", "title": "无自动检查 B", "phase": "p",
    "step": 12, "severity": "warning", "symptom": "s", "root_cause": "r",
}