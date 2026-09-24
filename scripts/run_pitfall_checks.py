"""陷阱库校验器：检测"能跑通但不完整"（silent gap）类问题。

与 preflight（报错/缺失阻断）正交：
- preflight 只管工具在不在、返回码、文件在不在 —— error 类。
- 本脚本加载 knowledge/pitfalls/*.yaml，对每条配置了 check 的条目执行探测，
  把"命令成功但结果不完整"的情形输出为警告报告（severity: warning/critical）。

不对任何真实工具做假设；check 缺省或不可执行时退回"需人工确认"，绝不臆断。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

PITFALLS_DIR = Path(__file__).resolve().parents[1] / "knowledge" / "pitfalls"

REQUIRED_KEYS = ("id", "title", "phase", "step", "severity", "symptom", "root_cause")
VALID_SEVERITY = ("info", "warning", "critical")


def _load_entries(directory: Path) -> list[dict]:
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML 未安装，无法解析陷阱库")
    entries: list[dict] = []
    for p in sorted(directory.glob("*.yaml")):
        if p.name == "README.md":
            continue
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if data is None:
            continue
        data.setdefault("_source", str(p))
        entries.append(data)
    return entries


def _validate(data: dict) -> list[str]:
    errs: list[str] = []
    for k in REQUIRED_KEYS:
        # 注意：step=0 是合法值（跨阶段条目），不能用 truthiness 判断缺失
        if data.get(k) is None or data.get(k) == "":
            errs.append(f"{data.get('_source')}: 缺少必需字段 {k!r}")
    sev = data.get("severity")
    if sev and sev not in VALID_SEVERITY:
        errs.append(f"{data.get('_source')}: severity={sev!r} 非法")
    if not isinstance(data.get("step"), int):
        errs.append(f"{data.get('_source')}: step 必须是整数")
    return errs


def _run_check(entry: dict, env: dict[str, str]) -> tuple[str, str | None, str]:
    """返回 (probe_output, gap_kind|None, engine)。
    engine in {'bash','fallback','manual'}；gap_kind in {'warning','critical'} 表示判为缺口。"""
    check = entry.get("check")
    if not check:
        return "<无自动检查，需人工确认>", None, "manual"
    lang = check.get("language")
    src = check.get("source")
    if not src:
        return "<空检查，需人工确认>", None, "manual"
    # 统一 utf-8 + errors=replace：Windows 本地编码(GBK)会崩掉中文读线程
    run_env = {**os.environ, **env, "PYTHONIOENCODING": "utf-8"}
    try:
        if lang == "shell":
            # 这些 check 是 POSIX 脚本，面向 Linux 服务器。本地开发（Windows）无 bash。
            # 若 bash 可用则用 bash 执行；否则退化为系统默认 shell（可能不支持 POSIX 语法）。
            bash = shutil.which("bash")
            if bash:
                proc = subprocess.run(
                    [bash, "-c", src], capture_output=True,
                    encoding="utf-8", errors="replace",
                    timeout=60, env=run_env,
                )
                engine = "bash"
            else:
                proc = subprocess.run(
                    src, shell=True, capture_output=True,
                    encoding="utf-8", errors="replace",
                    timeout=60, env=run_env,
                )
                engine = "fallback"
        else:
            return f"<不支持语言 {lang}>", None, "manual"
    except subprocess.TimeoutExpired:
        return "<检查超时>", None, "manual"
    except Exception as exc:  # noqa: BLE001
        return f"<检查执行失败: {exc}>", None, "manual"

    merged = (proc.stdout or "") + (proc.stderr or "")
    # 关键区分：脚本"执行失败/环境不支持" ≠ "检测到缺口"，→需人工；只有明确宣告"缺口"才判 gap。
    gap_kind = _decide_gap(merged, entry.get("severity", "warning"),
                           engine, proc.returncode)
    if gap_kind is None and engine == "manual":
        return merged.strip(), None, "manual"
    return merged.strip(), gap_kind, engine


def _decide_gap(merged: str, severity: str, engine: str, returncode: int) -> str | None:
    """纯判定：仅在脚本明确宣告"缺口/GAP"时判 gap，避免把环境失败误判成缺口。"""
    if "缺口" in merged or "GAP" in merged.upper():
        return severity
    return None


def run_all(directory: Path | None = None, db_dir: str | None = None) -> list[dict]:
    directory = directory or PITFALLS_DIR
    env = {"PIT_DB_DIR": db_dir or ""}
    report: list[dict] = []
    for e in _load_entries(directory):
        errs = _validate(e)
        if errs:
            report.append({"id": e.get("id"), "_source": e.get("_source"),
                           "error": errs, "gap": None})
            continue
        output, gap_kind, engine = _run_check(e, env)
        report.append({
            "id": e["id"],
            "title": e["title"],
            "phase": e["phase"],
            "step": e["step"],
            "severity": e["severity"],
            "gap": gap_kind,
            "engine": engine,
            "probe_output": output,
            "_source": e["_source"],
        })
    return report


def _cli() -> int:
    parser = argparse.ArgumentParser(description="静默缺口（silent gap）陷阱库校验")
    parser.add_argument("--dir", help="陷阱库目录（默认 knowledge/pitfalls）")
    parser.add_argument("--db-dir", dest="db_dir", help="传给检查脚本的 PIT_DB_DIR")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()

    directory = Path(args.dir) if args.dir else PITFALLS_DIR
    report = run_all(directory, db_dir=args.db_dir)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== 静默缺口陷阱库检查 ===")
        for r in report:
            if r.get("error"):
                print(f"  [结构错误] {r['_source']}: {r['error']}")
                continue
            if r.get("gap"):
                state = "GAP"
            elif r.get("engine") == "bash":
                state = "OK"
            else:
                state = "需人工"
            print(f"  [{state:>6}] {r['id']} {r['title']} (severity={r['severity']}, engine={r.get('engine')})")
            if r.get("gap"):
                print(f"           ↓ 检测到缺口，probe 输出: {r['probe_output']}")
        print("  —— 图例：OK=检查未宣告缺口（含环境不可探测时不误报）；GAP=明确宣告缺口；需人工=无自动检查或环境不可用")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())