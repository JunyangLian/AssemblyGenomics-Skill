#!/usr/bin/env python3
"""针对冻结流程 #001 的服务器环境预检（preflight.py）。

运行位置：用户的服务器（SOP 版后端由用户在服务器执行，或本地模拟）。
作用：探测冻结流程 #001 的 required 工具是否可用并报版本、检查数据文件存在性与
      R1/R2 配对完整性、探测资源（核 / 内存 / 磁盘）并对照 use-case-001 的缺口。

原则：
- 只报探测到的客观事实，缺失如实列为 blocker，不臆测可运行。
- 真实组装能否跑通不由本脚本判定（那是 smoke/真实验证的事）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# 来自 technology_registry 冻结流程 #001 的 required 工具（组装/评估段）
REQUIRED_TOOLS = {
    "fastp": [],
    "bwa": [r"bwa 2>&1"],
    "samtools": [r"samtools --version"],
    "juicer_dpnII": [],  # 手写 Juicer 流程 + DpnII 酶切
    "run-asm-pipeline.sh": [r"run-asm-pipeline.sh --help"],  # 3D-DNA
    "juicebox": [],
    "busco": [r"busco --version"],
}

# 注释阶段（use-case-001 步 10~11，skill 接管目标）required 工具
ANNOTATION_TOOLS = {
    "maker": [],  # MAKER2
    "augustus": [],
    "snap": [],
    "RepeatModeler": [],
    "RepeatMasker": [],
    "InterProScan": [r"interproscan.sh -h"],
    "eggnog-mapper": [r"emapper.py --version 2>&1"],
}

# 真实环境线索：conda env 与 ${HOME}/env 下可能出现工具（use-case-001 第七/八节）
CONDA_ENV_HINTS = [
    "$HOME/.conda/envs/bwa/bin",
    "$HOME/.conda/envs/samtools/bin",
    "$HOME/.conda/envs/java8/bin",
    "$HOME/env/3D-DNA",
    "$HOME/env/Juicer",
]
SGE_SCHEDULERS = ["qsub-sge.pl", "qsub", "qsub-sge"]

OPTIONAL_TOOLS = ["quast", "seqkit", "seqtk"]


def _run(cmd: str, timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out.strip()
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def _probe_one(tool: str, exe_map: dict[str, str], required: bool) -> dict[str, Any]:
    exe_path = exe_map.get(tool) or tool
    path = shutil.which(exe_path)
    entry: dict[str, Any] = {
        "found": path is not None,
        "path": path,
        "version": None,
        "required": required,
    }
    ver_cmds = REQUIRED_TOOLS.get(tool, [])
    if not path:
        for hint in CONDA_ENV_HINTS:
            cand = Path(os.path.expandvars(hint)) / tool
            if tool == "juicebox":
                cand = cand.with_suffix(".jar")
            if cand.exists():
                path = str(cand)
                entry["path"] = path
                entry["source"] = "conda_hint"
                break
    if path:
        for vc in ver_cmds:
            vc_fixed = vc.replace(tool, path)
            code, out = _run(vc_fixed)
            if out and ("version" in out.lower() or re.search(r"\bv?[0-9]+\.", out[:200])):
                entry["version"] = out.split("\n")[0][:120]
                break
    return entry


def probe_tools(exe: dict[str, str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    # 组装/评估段（use-case-001 步 0~9，required）
    for tool in REQUIRED_TOOLS:
        results[tool] = _probe_one(tool, exe, required=True)
    # 注释段（use-case-001 步 10~11，skill 接管，required）
    for tool in ANNOTATION_TOOLS:
        results[tool] = _probe_one(tool, exe, required=True)
        results[tool]["phase"] = "annotation"
    # optional
    for tool in OPTIONAL_TOOLS:
        p = shutil.which(tool)
        results[tool] = {
            "found": p is not None,
            "path": p,
            "version": None,
            "required": False,
        }
    return results


def check_data(manifest: dict | None, data_root: Path | None) -> dict[str, Any]:
    """检查数据文件存在性与 R1/R2 配对完整性。manifest 缺失时用 data_root 扫描。"""
    report: dict[str, Any] = {"pairs": {}, "missing": [], "unpaired": []}
    if manifest:
        libs = manifest.get("inputs", {}).get("libraries", [])
        for lib in libs:
            r1 = lib.get("read1")
            r2 = lib.get("read2")
            if r1:
                if Path(r1).exists():
                    report["pairs"].setdefault(r1, {})
                else:
                    report["missing"].append(r1)
            if r2:
                if Path(r2).exists():
                    report["pairs"].setdefault(r1 or "", {})["read2"] = r2
                else:
                    report["missing"].append(r2)
        return report

    if data_root and data_root.exists():
        fqs = sorted(data_root.rglob("*.fq.gz")) + sorted(data_root.rglob("*.fastq.gz"))
        uniq = {}
        for f in fqs:
            # 提取配对 key：去掉 _1/_2/_R1/_R2
            m = re.match(r"(.*)[_-]?([12RI])\.(fq|fastq)\.gz$", f.name)
            key = m.group(1) if m else f.name
            uniq.setdefault(key, []).append(str(f))
        for k, files in uniq.items():
            if len(files) == 2:
                report["pairs"][k] = {"read1": files[0], "read2": files[1]}
            else:
                report["unpaired"].append((k, files))
    return report


def probe_resources() -> dict[str, Any]:
    import shutil as _sh

    mem_bytes = None
    try:
        # Linux /proc/meminfo
        with open("/proc/meminfo") as fh:
            m = re.search(r"MemTotal:\s+(\d+) kB", fh.read())
        if m:
            mem_bytes = int(m.group(1)) * 1024
    except Exception:  # noqa: BLE001
        pass

    disk_total, disk_free = None, None
    try:
        du = _sh.disk_usage("/")
        disk_total, disk_free = du.total, du.free
    except Exception:  # noqa: BLE001
        pass

    # 调度器探测：SGE（qsub-sge.pl / qsub）优先，其次 SLURM/PBS
    scheduler = None
    for s in SGE_SCHEDULERS:
        if shutil.which(s):
            scheduler = f"SGE({s})"
            break
    if not scheduler and shutil.which("sbatch"):
        scheduler = "SLURM"
    if not scheduler and shutil.which("qsub"):
        scheduler = "PBS"

    return {
        "cpu_cores": os.cpu_count(),
        "mem_bytes": mem_bytes,
        "disk_total": disk_total,
        "disk_free": disk_free,
        "platform": sys.platform,
        "scheduler": scheduler,
    }


def _summarize(tools: dict[str, Any], res: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    for name, e in tools.items():
        if e.get("required") and not e.get("found"):
            blockers.append(f"required 工具缺少: {name}")
    if data.get("unpaired"):
        blockers.append(f"存在未配对的 FASTQ: {[u[0] for u in data['unpaired']]}")
    if data.get("missing"):
        blockers.append(f"数据文件缺失: {data['missing']}")
    if res.get("cpu_cores") is None:
        blockers.append("无法探测 CPU 核数")
    return {
        "ok": not blockers,
        "blockers": blockers,
        "tools": tools,
        "resources": res,
        "data": data,
    }


def _cli() -> int:
    parser = argparse.ArgumentParser(description="冻结流程 #001 服务器预检")
    parser.add_argument("--manifest", help="manifest.json（优先）")
    parser.add_argument("--data-root", help="数据目录（无 manifest 时扫描）")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    args = parser.parse_args()

    manifest = None
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    data_root = Path(args.data_root) if args.data_root else None

    tools = probe_tools({})
    res = probe_resources()
    data = check_data(manifest, data_root)
    report = _summarize(tools, res, data)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("=== 冻结流程 #001 预检 ===")
        print("--- 组装/评估段（步 0~9）---")
        for name, e in tools.items():
            if e.get("phase") == "annotation":
                continue
            status = "OK" if e["found"] else ("缺失" if e["required"] else "(可选缺失)")
            ver = f"  {e['version']}" if e.get("version") else ""
            print(f"  {name:24s} {status:12s} {e['path'] or ''}{ver}")
        print("--- 注释段（步 10~11，skill 接管）---")
        for name, e in tools.items():
            if e.get("phase") == "annotation":
                status = "OK" if e["found"] else "缺失"
                print(f"  {name:24s} {status:12s} {e['path'] or ''}")
        print(f"  CPU 核数    : {res.get('cpu_cores')}")
        print(f"  内存        : {res.get('mem_bytes')}")
        print(f"  调度器      : {res.get('scheduler')}")
        print(f"  磁盘可用    : {res.get('disk_free')}")
        for b in report["blockers"]:
            print(f"  [阻断] {b}")
        print("结论:", "通过（可进入 smoke）" if report["ok"] else "存在阻断，需补齐")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(_cli())