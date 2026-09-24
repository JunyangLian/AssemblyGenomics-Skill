#!/usr/bin/env python3
"""段 1：重复注释（RepeatModeler2 de novo 建库 → RepeatMasker 软屏蔽 → mask_qc）。

给第一次做基因组注释的你，这个阶段做的事：
  把基因组里的重复序列找出来并"软屏蔽"——重复区碱基标记成小写，不删除。
  后续基因预测（BRAKER --softmasking）靠小写标记避开重复区。
  为什么重要：屏蔽做错（拿成硬屏蔽 / 库版本太旧），后面注释悄悄变差，
  全程没有一个报错——这正是本项目要拦的"静默缺口"。

运行方式见 README.md。只依赖 Python 3 标准库；
每个阶段落 .stages/<name>.done 检查点，失败目录保留、不覆盖、不伪造完成标记。
"""
from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
STAGES = ["prepare_input", "builddb", "repeatmodeler", "collect_library",
          "repeatmasker", "mask_qc", "finalize"]


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_settings(path: Path) -> dict:
    s = json.loads(path.read_text(encoding="utf-8"))
    for key in ("run_id", "thread_budget", "genome_gz", "repeat"):
        if key not in s:
            raise SystemExit(f"[settings] 缺少必需字段 {key!r}")
    return s


def run(cmd: list[str], log, cwd=None) -> None:
    log(f"[cmd] {' '.join(cmd)}" + (f"  (cwd={cwd})" if cwd else ""))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, errors="replace", cwd=cwd)
    for line in (proc.stdout or "").splitlines():
        log("  | " + line)
    if proc.returncode != 0:
        raise RuntimeError(f"命令失败（exit {proc.returncode}）：{cmd[0]}——保留现场，看上方输出定位")
    return proc.stdout


def fasta_records(path: Path):
    """流式读 FASTA → (id, [seq 行]) 生成器；顺序与文件一致。"""
    with path.open(encoding="utf-8") as f:
        seq_id, chunks = None, []
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if seq_id is not None:
                    yield seq_id, chunks
                seq_id, chunks = line[1:].split()[0], []
            elif line and seq_id is not None:
                chunks.append(line)
        if seq_id is not None:
            yield seq_id, chunks


def version_of(cmd: list[str]) -> str:
    """抓取工具版本行；RepeatMasker 等会先打 Perl 警告，取含 'version' 的行。"""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=60)
        lines = [l for l in ((out.stdout or "") + (out.stderr or "")).splitlines() if l.strip()]
        for l in lines:
            if "version" in l.lower():
                return l.strip()
        return lines[0] if lines else ""
    except Exception:
        return ""


def log_maker(workdir: Path):
    logs = workdir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logf = (logs / "stage1.log").open("a", encoding="utf-8")

    def log(msg: str) -> None:
        line = f"[{now()}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description="段 1 驱动：重复注释（先 --check 后 --execute）")
    ap.add_argument("--settings", default="settings.json")
    ap.add_argument("--check", action="store_true", help="只做预检（文件/工具/预算），不启动计算")
    ap.add_argument("--execute", action="store_true", help="正式执行")
    ap.add_argument("--resume", action="store_true", help="目录已有半成品时，跳过已完成阶段续跑")
    args = ap.parse_args()

    settings = load_settings(Path(args.settings))
    root = SCRIPT_PATH.parent
    workdir = root / "runs" / settings["run_id"] / "1.Repeat_Annotation"
    rep = settings["repeat"]
    budget = int(settings["thread_budget"])

    # ---- 预检（PIT-007/D-019：预算是用户确认值，且不得超过全机核数） ----
    problems = []
    ncpu = os.cpu_count() or 0
    if budget <= 0:
        problems.append("thread_budget 必须为正数")
    if ncpu and budget > ncpu:
        problems.append(f"thread_budget={budget} ≥ 全机核数 {ncpu}——共享服务器拉满不合适（PIT-007），须确认独占或调低")
    for key in ("repeatmodeler", "builddatabase", "repeatmasker", "env_python"):
        p = Path(rep[key])
        if not p.exists():
            problems.append(f"repeat.{key} 不存在：{p}")
    gz = Path(settings["genome_gz"])  # settings 中为服务器绝对路径（0.Raw_Data 只读，driver 只解压拷贝）
    if not gz.exists():
        problems.append(f"基因组文件不存在：{gz}")
    for key in ("repeatmodeler_threads", "repeatmasker_pa"):
        if int(rep[key]) > budget:
            problems.append(f"repeat.{key}={rep[key]} 超过确认预算 {budget}")

    famdb_text = ""
    fm = Path(rep["famdb"])
    if fm.exists():
        proc = subprocess.run([rep["env_python"], str(fm), "info"],
                              capture_output=True, text=True, errors="replace")
        famdb_text = (proc.stdout + proc.stderr).strip()
        for line in famdb_text.splitlines():
            if line.strip().lower().startswith("version"):
                print(f"[预检] FamDB {line.strip()}（PIT-001：此版本已冻结进 settings）")
    else:
        problems.append(f"famdb.py 不存在：{fm}（PIT-001：无版本记录 = 重复分类可能静默失败）")

    if problems:
        print("[预检失败] 共 %d 项：" % len(problems))
        for p in problems:
            print("  - " + p)
        return 2
    print(f"[预检通过] 预算 {budget} 线程 ≤ 全机 {ncpu} 核；工具与输入齐备。")

    if args.check or not args.execute:
        print("[--check 模式] 未启动计算。确认无误后加 --execute 正式运行。")
        return 0

    # ---- 目录守卫（Siganus 规则：不覆盖半成品，不伪造完成标记） ----
    markers = workdir / ".stages"
    if (workdir / "COMPLETE.json").exists():
        print(f"[停止] {workdir} 已有 COMPLETE.json——要重跑请换 run_id 或手动归档后删除该目录。")
        return 1
    if workdir.exists() and any(workdir.iterdir()) and not args.resume:
        done = {p.name for p in markers.glob("*.done")} if markers.exists() else set()
        if not done:
            print(f"[停止] {workdir} 非空且无任何检查点——先人工查看/归档，再加 --resume 或删除。")
            return 1
        print("[续跑] 检测到检查点，跳过已完成阶段。")
    markers.mkdir(parents=True, exist_ok=True)
    log = log_maker(workdir)
    log(f"=== 段 1 开始（run_id={settings['run_id']}，预算 {budget} 线程）===")

    def done_stage(name: str) -> bool:
        return (markers / f"{name}.done").exists()

    def mark(name: str, payload: dict) -> None:
        (markers / f"{name}.done").write_text(
            json.dumps({"stage": name, "ts": now(), **payload}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    env = dict(os.environ)
    env["PATH"] = rep["env_bin"] + os.pathsep + env.get("PATH", "")
    env.pop("PYTHONPATH", None)  # 本机 base 壳有污染（CPhasing-main），一律清除

    try:
        # 1. 准备输入：解压到工作目录（0.Raw_Data 保持只读）
        if not done_stage("prepare_input"):
            genome_fa = workdir / "genome.fa"
            log("[1/7] 解压基因组 → genome.fa（0.Raw_Data 原件不动）")
            with gzip.open(gz, "rt") as src, genome_fa.open("w") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            mark("prepare_input", {"genome_fa_sha256": sha256_file(genome_fa)})
        genome_fa = workdir / "genome.fa"

        # 2. BuildDatabase（在 workdir 下运行：产物 SC288C.* 落在 workdir）
        if not done_stage("builddb"):
            log("[2/7] BuildDatabase 建库（RepeatModeler 的输入索引；产物落在 runs 目录）")
            run([rep["builddatabase"], "-name", rep["db_prefix"], str(genome_fa)],
                log, cwd=str(workdir))
            mark("builddb", {})

        # 3. RepeatModeler2 de novo 建库
        # 注意：RM 2.0.7 没有 -dir 选项（曾臆造导致产物落错位置）——运行的 RM_* 目录
        # 出现在进程的工作目录下，因此显式 cwd=workdir。
        if not done_stage("repeatmodeler"):
            log(f"[3/7] RepeatModeler2 de novo（-threads {rep['repeatmodeler_threads']}，"
                f"酵母 12 Mb 预计 5-15 分钟；RM_* 目录与产物落在 runs 目录）")
            run([rep["repeatmodeler"], "-database", rep["db_prefix"],
                 "-threads", str(rep["repeatmodeler_threads"])],
                log, cwd=str(workdir))
            mark("repeatmodeler", {})

        # 4. 收集 de novo 库
        if not done_stage("collect_library"):
            log("[4/7] 收集 consensi.fa.classified → repeat_library.final.fa")
            cands = sorted((workdir).glob("RM_*/consensi.fa.classified"))
            if not cands:
                raise RuntimeError("workdir 下未找到 RM_*/consensi.fa.classified——RM 阶段实际失败，看日志")
            if len(cands) > 1:
                log(f"  注意：发现 {len(cands)} 个 RM 运行目录，取最新：{cands[-1]}")
            lib = workdir / "repeat_library.final.fa"
            shutil.copyfile(cands[-1], lib)
            fam = sum(1 for line in lib.open(encoding="utf-8") if line.startswith(">"))
            if fam < 1:
                raise RuntimeError("de novo 库为空——RM 未产出任何 repeat family")
            log(f"  de novo 库：{fam} 个 repeat family")
            mark("collect_library", {"families": fam, "library": str(lib)})

        # 5. RepeatMasker 软屏蔽（-xsmall = 重复区小写，绝不丢碱基）
        lib = workdir / "repeat_library.final.fa"
        if not done_stage("repeatmasker"):
            log(f"[5/7] RepeatMasker -s -xsmall -pa {rep['repeatmasker_pa']}"
                f"（-xsmall 是软屏蔽的关键参数，PIT-006）")
            run([rep["repeatmasker"], "-pa", str(rep["repeatmasker_pa"]), "-s", "-xsmall",
                 "-lib", str(lib), "-dir", str(workdir / "RepeatMasker_Final"),
                 "-e", rep["repeatmasker_engine"], str(genome_fa)], log, cwd=str(workdir))
            mark("repeatmasker", {})

        # 6. mask_qc：软屏蔽三重核验（ID/长度/忽略大小写序列一致 + 确有小写）
        if not done_stage("mask_qc"):
            log("[6/7] mask_qc 核验（PIT-006：防硬屏蔽/未屏蔽冒充软屏蔽）")
            masked = workdir / "RepeatMasker_Final" / "genome.fa.masked"
            if not masked.exists():
                raise RuntimeError(f"未找到屏蔽产物：{masked}")
            soft = workdir / "genome.softmasked.fa"
            shutil.copyfile(masked, soft)

            a = {i: "".join(s) for i, s in fasta_records(genome_fa)}
            b = {i: "".join(s) for i, s in fasta_records(soft)}
            ids_ok = list(a) == list(b)
            len_ok = ids_ok and all(len(a[i]) == len(b[i]) for i in a)
            seq_ok = ids_ok and all(a[i].upper() == b[i].upper() for i in a)
            total = sum(len(v) for v in b.values())
            lower = sum(1 for v in b.values() for ch in v if ch.islower())
            nbase = sum(1 for v in b.values() for ch in v.upper() if ch == "N")
            lower_pct = round(100.0 * lower / total, 3) if total else 0.0
            n_pct = round(100.0 * nbase / total, 3) if total else 0.0
            qc = {
                "status": "PASS" if (ids_ok and len_ok and seq_ok and lower_pct >= 0.5) else "FAIL",
                "ids_equal": ids_ok, "lengths_equal": len_ok,
                "sequence_equal_ignorecase": seq_ok,
                "lowercase_pct": lower_pct, "n_pct": n_pct,
                "rule": "ID/长度/忽略大小写序列必须与输入完全一致；小写比例须 ≥0.5%（酵母参考带 [1,10] advisory）",
                "input_sha256": sha256_file(genome_fa), "softmasked_sha256": sha256_file(soft),
                "ts": now(),
            }
            (workdir / "mask_qc.json").write_text(
                json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log(f"  mask_qc: {qc['status']} lowercase={lower_pct}% N={n_pct}%")
            if qc["status"] != "PASS":
                raise RuntimeError("mask_qc FAIL——软屏蔽核验未过，禁止带病进入 BRAKER（PIT-006）")
            mark("mask_qc", {"status": "PASS", "lowercase_pct": lower_pct})

        # 7. 收尾：provenance + COMPLETE
        if not done_stage("finalize"):
            log("[7/7] 写 provenance 与 COMPLETE.json")
            prov = {
                "run_id": settings["run_id"], "stage": "stage1_repeat",
                "thread_budget": budget, "settings": settings,
                "tools": {
                    "repeatmodeler": version_of([rep["repeatmodeler"], "-version"]),
                    "repeatmasker": version_of([rep["repeatmasker"], "-version"]),
                    "famdb": [l.strip() for l in famdb_text.splitlines()
                              if l.strip().lower().startswith(("database", "version"))],
                },
                "inputs": {"genome_gz": str(gz), "genome_gz_sha256": sha256_file(gz),
                           "genome_fa_sha256": sha256_file(genome_fa)},
                "outputs": {
                    "genome_softmasked": str(workdir / "genome.softmasked.fa"),
                    "library": str(workdir / "repeat_library.final.fa"),
                    "mask_qc": str(workdir / "mask_qc.json"),
                },
                "script_sha256": sha256_file(SCRIPT_PATH), "ts": now(),
            }
            (workdir / "provenance.json").write_text(
                json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (workdir / "COMPLETE.json").write_text(
                json.dumps({"stage": "stage1_repeat", "status": "SUCCEEDED", "ts": now()},
                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            mark("finalize", {})

    except RuntimeError as exc:
        log(f"[失败] {exc}")
        log("按 README『失败了怎么办』处理：保留现场、看日志、勿删目录。")
        return 1

    log("=== 段 1 完成。交付物：genome.softmasked.fa + repeat_library.final.fa + mask_qc.json ===")
    log("把 mask_qc.json 与 logs/stage1.log 尾部贴回给 skill 做回传校验与基线对照。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
