#!/usr/bin/env python3
"""段 2：RNA-seq 比对（hisat2 索引 → 成对比对 → sort/index/quickcheck → 比对率 QC）。

给第一次做注释的你：基因预测软件（BRAKER）需要"转录证据"——把 RNA-seq 读段
比对回基因组，得到的 BAM 文件就是证据。这个阶段只产证据，不产注释。

上游绑定：启动即核验 genome.softmasked.fa 的 sha256 与段 1 冻结值一致，
上游产物变了就停。比对率（overall alignment rate）是本段的结果合理性指标：
显著低于 ~50% 先不要往下走，把 hisat2 日志贴回给 skill。
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def version_of(cmd: list[str]) -> str:
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
    logf = (logs / "stage2.log").open("a", encoding="utf-8")

    def log(msg: str) -> None:
        line = f"[{now()}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description="段 2 驱动：RNA-seq 比对（先 --check 后 --execute）")
    ap.add_argument("--settings", default="settings2.json")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    s = json.loads(Path(args.settings).read_text(encoding="utf-8"))
    tools = s["tools"]
    budget = int(s["thread_budget"])
    ht, st = int(s["hisat2_threads"]), int(s["sort_threads"])
    if ht + st > budget:
        print(f"[预检失败] hisat2_threads({ht}) + sort_threads({st}) = {ht + st} 超过预算 {budget}")
        return 2

    root = SCRIPT_PATH.parent
    workdir = root / "runs" / s["run_id"] / "2.RNAseq"
    soft = Path(s["softmasked_genome"])
    idx = workdir / "idx" / s["index_prefix"]

    problems = []
    ncpu = os.cpu_count() or 0
    if ncpu and budget > ncpu:
        problems.append(f"thread_budget={budget} ≥ 全机核数 {ncpu}（PIT-007 共享服务器拉满不合适）")
    for k in ("hisat2", "hisat2_build", "samtools"):
        if not Path(tools[k]).exists():
            problems.append(f"tools.{k} 不存在：{tools[k]}")
    if not soft.exists():
        problems.append(f"上游产物缺失：{soft}")
    elif sha256_file(soft) != s["expected_softmasked_sha256"]:
        problems.append("softmasked 基因组 sha256 与段 1 冻结值不符——上游产物被改动，拒绝混用")
    for smp in s["samples"]:
        for k in ("r1", "r2"):
            fq = Path(smp[k])
            if not fq.exists():
                problems.append(f"样本 {smp['id']} 的 {k} 不存在：{fq}")
    if not shutil.which("bash"):
        problems.append("未找到 bash（比对管道需要 bash -o pipefail）")
    if problems:
        print("[预检失败] 共 %d 项：" % len(problems))
        for p in problems:
            print("  - " + p)
        return 2
    print(f"[预检通过] 预算 {budget} ≤ 全机 {ncpu} 核；softmasked sha256 与段 1 绑定一致；"
          f"{len(s['samples'])} 个样本齐备。")

    if args.check or not args.execute:
        print("[--check 模式] 未启动计算。")
        return 0

    markers = workdir / ".stages"
    if (workdir / "COMPLETE.json").exists():
        print(f"[停止] {workdir} 已有 COMPLETE.json——重跑请换 run_id 或归档。")
        return 1
    if workdir.exists() and any(workdir.iterdir()) and not args.resume:
        done = {p.name for p in markers.glob("*.done")} if markers.exists() else set()
        if not done:
            print(f"[停止] {workdir} 非空且无检查点——先人工查看/归档。")
            return 1
        print("[续跑] 检测到检查点，跳过已完成阶段。")
    markers.mkdir(parents=True, exist_ok=True)
    log = log_maker(workdir)
    log(f"=== 段 2 开始（run_id={s['run_id']}，预算 {budget} 线程）===")

    def done(name: str) -> bool:
        return (markers / f"{name}.done").exists()

    def mark(name: str, payload: dict) -> None:
        (markers / f"{name}.done").write_text(
            json.dumps({"stage": name, "ts": now(), **payload}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    try:
        # 1. hisat2 索引（用软屏蔽基因组；坐标与输入一致由段 1 QC 保证）
        if not done("index"):
            log("[1/4] hisat2-build 索引（12 Mb 参考，秒级）")
            (workdir / "idx").mkdir(parents=True, exist_ok=True)
            proc = subprocess.run(
                [tools["hisat2_build"], str(soft), str(idx)],
                capture_output=True, text=True, errors="replace", env=env)
            log("  | " + "".join([proc.stdout or "", proc.stderr or ""]).strip().replace("\n", "\n  | "))
            if proc.returncode != 0:
                raise RuntimeError(f"hisat2-build 失败（exit {proc.returncode}）")
            mark("index", {"index_prefix": s["index_prefix"]})

        # 2. 逐样本比对（bash -o pipefail：hisat2 和 sort 任一失败都报错）
        rate_re = re.compile(r"([\d.]+)%\s+overall alignment rate")
        for smp in s["samples"]:
            mk = f"map_{smp['id']}"
            if done(mk):
                continue
            log(f"[2/4] 比对 {smp['id']}（{smp['srr']}，hisat2 {ht} 线程 + sort 辅助 {st}）")
            (workdir / "bam").mkdir(parents=True, exist_ok=True)
            bam = workdir / "bam" / f"{smp['id']}.sorted.bam"
            hisat2_log = workdir / "bam" / f"{smp['id']}.hisat2.log"
            extra = " ".join(s["hisat2_extra"])
            pipeline = (
                "set -o pipefail; "
                f"'{tools['hisat2']}' -p {ht} {extra} -x '{idx}' "
                f"-1 '{smp['r1']}' -2 '{smp['r2']}' 2> '{hisat2_log}' | "
                f"'{tools['samtools']}' sort -@ {st} -m 1G -o '{bam}' -"
            )
            proc = subprocess.run(["bash", "-o", "pipefail", "-c", pipeline],
                                  capture_output=True, text=True, errors="replace", env=env)
            if proc.returncode != 0:
                log("  | " + (proc.stdout or "").strip()[-2000:])
                raise RuntimeError(f"样本 {smp['id']} 比对管道失败（exit {proc.returncode}）——保留现场看 {hisat2_log}")
            histext = hisat2_log.read_text(encoding="utf-8", errors="replace")
            m = rate_re.search(histext)
            rate = round(float(m.group(1)), 2) if m else None
            qc = {"sample": smp["id"], "srr": smp["srr"],
                  "overall_alignment_rate_pct": rate,
                  "rule": "比对率是咨询性指标：显著低于 ~50% 先排查（配对/输入/索引），不硬拦",
                  "hisat2_log": str(hisat2_log), "ts": now()}
            (workdir / "bam" / f"{smp['id']}.qc.json").write_text(
                json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log(f"  样本 {smp['id']}: alignment rate = {rate if rate is not None else '未解析(看日志)'}%")
            mark(mk, {"sample": smp["id"], "rate_pct": rate})

        # 3. 索引 + quickcheck + provenance + COMPLETE
        if not done("finalize"):
            log("[3/4] samtools index + quickcheck")
            bams = sorted((workdir / "bam").glob("*.sorted.bam"))
            for bam in bams:
                proc = subprocess.run([tools["samtools"], "index", str(bam)],
                                      capture_output=True, text=True, errors="replace", env=env)
                if proc.returncode != 0:
                    raise RuntimeError(f"samtools index 失败：{bam.name}（exit {proc.returncode}）")
            proc = subprocess.run([tools["samtools"], "quickcheck", "-v", *map(str, bams)],
                                  capture_output=True, text=True, errors="replace", env=env)
            if proc.returncode != 0:
                raise RuntimeError("quickcheck 未通过：\n" + (proc.stdout or "") + (proc.stderr or ""))
            log("[4/4] provenance + COMPLETE")
            prov = {
                "run_id": s["run_id"], "stage": "stage2_rnaseq",
                "thread_budget": budget,
                "upstream": {"genome_softmasked": str(soft),
                             "sha256": sha256_file(soft),
                             "expected_sha256": s["expected_softmasked_sha256"],
                             "bound": sha256_file(soft) == s["expected_softmasked_sha256"]},
                "tools": {"hisat2": version_of([tools["hisat2"], "--version"]),
                          "samtools": version_of([tools["samtools"], "--version"])},
                "samples": [{"id": smp["id"], "srr": smp["srr"],
                             "bam": str(workdir / "bam" / f"{smp['id']}.sorted.bam"),
                             "bam_sha256": sha256_file(workdir / "bam" / f"{smp['id']}.sorted.bam"),
                             "r1": smp["r1"], "r2": smp["r2"],
                             "r1_sha256": sha256_file(Path(smp["r1"])),
                             "r2_sha256": sha256_file(Path(smp["r2"]))}
                            for smp in s["samples"]],
                "script_sha256": sha256_file(SCRIPT_PATH), "ts": now(),
            }
            (workdir / "provenance.json").write_text(
                json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (workdir / "COMPLETE.json").write_text(
                json.dumps({"stage": "stage2_rnaseq", "status": "SUCCEEDED", "ts": now()},
                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            mark("finalize", {})
    except RuntimeError as exc:
        log(f"[失败] {exc}")
        log("保留现场、看日志、勿删目录；排除后 --resume 续跑或归档重来。")
        return 1

    log("=== 段 2 完成。交付物：bam/*.sorted.bam(+bai) + 每样本 qc.json ===")
    log("把 bam/ 下各 qc.json 与 logs/stage2.log 尾部贴回给 skill。")
    return 0


if __name__ == "__main__":
    sys.exit(main())