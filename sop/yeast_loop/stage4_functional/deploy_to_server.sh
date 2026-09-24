#!/usr/bin/env bash
# stage4_functional SOP 落盘脚本（脱敏版，heredoc + sha256 自校验）
set -e
cd ~
mkdir -p ~/yeast_test/sop/yeast_loop/stage4_functional
cd ~/yeast_test/sop/yeast_loop/stage4_functional
cat > settings4.json <<'SKILL_EOF'
{
  "run_id": "batch01",
  "thread_budget": 32,
  "diamond_threads": 16,
  "interpro_cpu": 16,
  "input_proteins": "${HOME}/yeast_test/sop/yeast_loop/stage3_braker/runs/batch01/4.BRAKER3/5.Longest/SC288C.nofilter.longest.pep.fa",
  "expected_input_sha256": "c3258d39041952157003d6434362573172a775a408dd9fd45ff50f7fd57807af",
  "expected_protein_count": 5384,
  "tools": {
    "diamond": "${SHARED}/.conda/envs/braker3/bin/diamond",
    "interproscan": "${SHARED}/ann/interproscan-5.76-107.0/interproscan.sh",
    "java11": "${HOME}/env/java11"
  },
  "diamond": {
    "evalue": "1e-5",
    "max_target_seqs": 25,
    "max_hsps": 1,
    "very_sensitive": true,
    "qcov_filter_pct": 50,
    "ambiguity_bitscore_frac": 0.05,
    "outfmt_cols": ["qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
                    "qstart", "qend", "sstart", "send", "evalue", "bitscore",
                    "qlen", "slen", "qcovhsp", "scovhsp", "stitle"]
  },
  "databases": {
    "NR": {
      "db": "${DB}/nr_20240416_diamond_v2.1.9.163/fungi.fa.dmnd",
      "annot": null,
      "note": "真菌子集（酵母适配；非 Siganus 的动物子集）"
    },
    "Swissprot": {
      "db": "${DB}/swissport/diamond/uniprot_sprot.Eukaryota.fasta.simple.dmnd",
      "annot": "${DB}/swissport/uniprot_sprot.Eukaryota.id.annot.xls",
      "note": "真核（含真菌）"
    },
    "KEGG": {
      "db": "${DB}/kegg/101.0/kegg_all_clean.fa.dmnd",
      "annot": "${DB}/kegg/101.0/kegg_all_clean.id.annot.xls",
      "note": "全库版（含真菌；非 animal 子集）"
    },
    "KOG": {
      "db": "${DB}/kog/20090331/kog_clean.fa.dmnd",
      "annot": "${DB}/kog/20090331/kog_clean.fa.id",
      "note": "KOG 模式生物全集"
    },
    "TrEMBL": {
      "db": "${DB}/trembl/uniprot_trembl.Eukaryota.fasta.simple.dmnd",
      "annot": "${DB}/trembl/uniprot_trembl.Eukaryota.fasta.simple.ann.tsv",
      "note": "真核（含真菌）"
    }
  }
}
SKILL_EOF
cat > run_stage4.py <<'SKILL_EOF'
#!/usr/bin/env python3
"""段 4：功能注释（DIAMOND×5 同源比对 + InterProScan + 七类集成）。

Siganus 实证流程的酵母适配版（use-case-002 §四）。
- 输入绑定：最长转录本蛋白集（5,384 条）sha256 预检核验。
- 库选择为真菌适配：NR fungi 子集、KEGG 全库版、Swiss-Prot/TrEMBL 真核（含真菌）、KOG。
- 比对：diamond blastp --very-sensitive -e 1e-5 -k 25 --max-hsps 1，17 列含覆盖度；
  qcovhsp>=50% 过滤 → 最高 bitscore 选最佳命中；KEGG/KOG 近最高 5% 冲突标记 ambiguous_near_top。
- InterProScan 5.76 + Java 11（JAVA_HOME 隔离注入，不动 base）；GO 只取 --goterms。
- 输出：七类 0/1 标记 + Any-Annotated + 覆盖率 + validation.json（技术性 PASS ≠ 功能正确）。
"""
from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
HERE = SCRIPT_PATH.parent


def now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log_maker(workdir: Path):
    logs = workdir / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logf = (logs / "stage4.log").open("a", encoding="utf-8")

    def log(msg: str) -> None:
        line = f"[{now()}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()
    return log


def run_cmd(cmd: list[str], log, env: dict | None = None, cwd: Path | None = None,
            timeout: int = 7200) -> str:
    log(f"[cmd] {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace", env=env or dict(os.environ),
                              cwd=str(cwd) if cwd else None, timeout=timeout)
    except OSError as exc:
        raise RuntimeError(f"无法执行 {cmd[0]}：{exc}")
    tail = (proc.stdout or "").strip()
    if tail:
        log("  | " + tail[-3000:].replace("\n", "\n  | "))
    if proc.returncode != 0:
        raise RuntimeError(f"命令失败（exit {proc.returncode}）：{cmd[0]}")
    return proc.stdout


def parse_diamond_hits(raw_path: Path, qcov: float, log) -> list[dict]:
    """解析 17 列 raw → 过滤(qcovhsp>=阈值) → 每 query 最高 bitscore 最佳命中。"""
    cols = ["qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
            "qstart", "qend", "sstart", "send", "evalue", "bitscore",
            "qlen", "slen", "qcovhsp", "scovhsp", "stitle"]
    rows: list[dict] = []
    with raw_path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            if len(p) != len(cols):
                continue
            row = dict(zip(cols, p))
            row["bitscore"] = float(row["bitscore"])
            row["evalue"] = float(row["evalue"])
            row["qcovhsp"] = float(row["qcovhsp"])
            row["scovhsp"] = float(row["scovhsp"])
            if row["qcovhsp"] >= qcov:
                rows.append(row)
    best: dict[str, dict] = {}
    for r in rows:
        q = r["qseqid"]
        if q not in best or (r["bitscore"], -r["evalue"], r["qcovhsp"], r["sseqid"]) > (
                best[q]["bitscore"], -best[q]["evalue"], best[q]["qcovhsp"], best[q]["sseqid"]):
            best[q] = r
    return rows, best


def main() -> int:
    ap = argparse.ArgumentParser(description="段 4 驱动：功能注释（先 --check 后 --execute）")
    ap.add_argument("--settings", default="settings4.json")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    s = json.loads(Path(args.settings).read_text(encoding="utf-8"))
    budget = int(s["thread_budget"])
    dt, ic = int(s["diamond_threads"]), int(s["interpro_cpu"])
    if max(dt, ic) > budget:
        print(f"[预检失败] diamond/interpro 线程超过预算 {budget}")
        return 2

    root = HERE
    workdir = root / "runs" / s["run_id"] / "6.Functional"
    prot = Path(s["input_proteins"])
    tools = s["tools"]

    problems = []
    ncpu = os.cpu_count() or 0
    if ncpu and budget > ncpu:
        problems.append(f"thread_budget={budget} ≥ 全机核数 {ncpu}（PIT-007）")
    if not prot.exists():
        problems.append(f"输入蛋白缺失：{prot}")
    elif sha256_file(prot) != s["expected_input_sha256"]:
        problems.append("输入蛋白 sha256 ≠ 段 3 绑定值（c3258d39…）——上游被改动，拒绝混用")
    for key in ("diamond", "interproscan"):
        if not Path(tools[key]).exists():
            problems.append(f"tools.{key} 缺失：{tools[key]}")
    j11 = Path(tools["java11"]) / "bin/java"
    if not j11.exists():
        problems.append(f"Java 11 缺失：{j11}——按 D-017 用 TUNA 装：conda create -p {tools['java11']} -c conda-forge openjdk=11")
    else:
        ver = subprocess.run([str(j11), "-version"], capture_output=True, text=True).stderr
        if "11." not in ver:
            problems.append(f"java11 路径版本不对（期望 11.x）：{ver.strip()[:60]}")
    for key, cfg in s["databases"].items():
        if not Path(cfg["db"]).exists():
            problems.append(f"库 {key} 的 db 缺失：{cfg['db']}")
        if cfg.get("annot") and not Path(cfg["annot"]).exists():
            problems.append(f"库 {key} 的 annot 缺失：{cfg['annot']}")

    if problems:
        print("[预检失败] 共 %d 项：" % len(problems))
        for p in problems:
            print("  - " + p)
        return 2
    print(f"[预检通过] 预算 {budget} ≤ 全机 {ncpu} 核；输入绑定与工具/库齐备。")

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
    log(f"=== 段 4 开始（run_id={s['run_id']}，预算 {budget} 线程）===")

    def done(name: str) -> bool:
        return (markers / f"{name}.done").exists()

    def mark(name: str, payload: dict) -> None:
        (markers / f"{name}.done").write_text(
            json.dumps({"stage": name, "ts": now(), **payload}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)

    amb_frac = float(s["diamond"]["ambiguity_bitscore_frac"])
    qcov = float(s["diamond"]["qcov_filter_pct"])

    try:
        # A. query 准备：复制 + QC（PIT-004 钩子：内部 '.'/'*'）
        if not done("query_prep"):
            log("[A] query 准备与 QC（PIT-004：内部歧义字符）")
            qdir = workdir / "0.Query"
            qdir.mkdir(parents=True, exist_ok=True)
            query = qdir / "query.faa"
            shutil.copyfile(prot, query)
            bad = []
            n = 0
            with query.open(encoding="utf-8") as f:
                pid = None; seq = []
                for line in f:
                    if line.startswith(">"):
                        if pid is not None:
                            sseq = "".join(seq)
                            n += 1
                            inner = sseq[:-1] if sseq.endswith("*") else sseq
                            if "." in inner or (inner and "*" in inner):
                                bad.append(pid)
                        pid = line[1:].split()[0]; seq = []
                    else:
                        seq.append(line.strip())
                if pid is not None:
                    sseq = "".join(seq); n += 1
                    inner = sseq[:-1] if sseq.endswith("*") else sseq
                    if "." in inner or (inner and "*" in inner):
                        bad.append(pid)
            if n != s["expected_protein_count"]:
                raise RuntimeError(f"蛋白条数不符：{n} ≠ {s['expected_protein_count']}")
            if bad:
                raise RuntimeError(f"PIT-004：检出 {len(bad)} 条内部歧义蛋白（{bad[:5]}...）——先隔离再注释")
            qc = {"count": n, "internal_ambiguity": 0, "query": str(query),
                  "input_sha256": sha256_file(query), "ts": now()}
            (qdir / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
            log(f"  query 就绪：{n} 条蛋白，无内部歧义字符")
            mark("query_prep", qc)

        query = workdir / "0.Query" / "query.faa"

        # B. DIAMOND × 5
        for key, cfg in s["databases"].items():
            mk = f"diamond_{key}"
            if done(mk):
                continue
            d = workdir / key
            d.mkdir(parents=True, exist_ok=True)
            log(f"[B] {key} 比对（{cfg['db'].split('/')[-1]}，{cfg.get('note','')}）")
            raw = d / "raw_hits.tsv"
            run_cmd([tools["diamond"], "blastp",
                     "--db", cfg["db"], "--query", str(query),
                     "-o", str(raw), "--outfmt", "6",
                     *(s["diamond"]["outfmt_cols"]),
                     "--evalue", s["diamond"]["evalue"],
                     "--max-target-seqs", str(s["diamond"]["max_target_seqs"]),
                     "--max-hsps", str(s["diamond"]["max_hsps"]),
                     "--very-sensitive", "--threads", str(dt)],
                    log, env=env, cwd=d)
            rows, best = parse_diamond_hits(raw, qcov, log)
            with (d / "filtered_hits.tsv").open("w", encoding="utf-8") as fo:
                fo.write("\t".join(s["diamond"]["outfmt_cols"]) + "\n")
                for r in rows:
                    fo.write("\t".join(str(r[c]) for c in s["diamond"]["outfmt_cols"]) + "\n")
            # 注释表：只取 best 命中的 sseqid（流式扫，防大表爆内存）
            annot: dict[str, str] = {}
            sset = {r["sseqid"] for r in best.values()}
            if cfg.get("annot"):
                with Path(cfg["annot"]).open(encoding="utf-8", errors="replace") as af:
                    for line in af:
                        parts = line.rstrip("\n").split("\t")
                        if parts and parts[0] in sset:
                            annot[parts[0]] = "\t".join(parts[1:])
            with (d / "best_hits.tsv").open("w", encoding="utf-8") as fo:
                fo.write("qseqid\tsseqid\tbitscore\tevalue\tqcovhsp\tsqcovhsp\tstitle\tannot\tambiguous_near_top\n")
                for q, r in sorted(best.items()):
                    # 近最高 5% 冲突（KEGG/KOG 语义）
                    amb = ""
                    if key in ("KEGG", "KOG"):
                        top = max(x["bitscore"] for x in rows if x["qseqid"] == q)
                        close = [x for x in rows if x["qseqid"] == q
                                 and x["bitscore"] >= top * (1 - amb_frac)]
                        if len(close) > 1:
                            amb = "1"
                    fo.write("\t".join([
                        q, r["sseqid"], f"{r['bitscore']:.1f}", f"{r['evalue']:.2e}",
                        f"{r['qcovhsp']:.1f}", f"{r['scovhsp']:.1f}",
                        r["stitle"], annot.get(r["sseqid"], ""), amb]) + "\n")
            qc = {"raw_rows": len(rows), "filtered_queries": len(best),
                  "queries_with_hit": sum(1 for r in rows if r["qseqid"] in best),
                  "annot_missing_ids": len(sset - set(annot)) if cfg.get("annot") else None}
            (d / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
            log(f"  {key}: filtered_hits={len(rows)}，best_queries={len(best)}")
            mark(mk, qc)

        # C. InterProScan（Java 11 隔离注入）
        if not done("interpro"):
            log("[C] InterProScan 5.76（--goterms --iprlookup，Java 11 注入）")
            d = workdir / "Interpro"
            d.mkdir(parents=True, exist_ok=True)
            ipr_env = dict(env)
            ipr_env["JAVA_HOME"] = tools["java11"]
            ipr_env["PATH"] = str(Path(tools["java11"]) / "bin") + os.pathsep + ipr_env.get("PATH", "")
            run_cmd([tools["interproscan"],
                     "--input", str(query), "--seqtype", "p", "--formats", "TSV",
                     "--outfile", str(d / "interproscan.tsv"),
                     "--cpu", str(ic), "--goterms", "--iprlookup",
                     "--tempdir", str(d / "tmp"), "--disable-precalc"],
                    log, env=ipr_env, cwd=d, timeout=10800)
            mark("interpro", {})

        # D. GO 组装（只取 IPR --goterms；正则内容识别，不依赖脆列号——PIT-003 教训）
        if not done("go"):
            log("[D] GO 去重与蛋白映射（来源：IPR --goterms）")
            gdir = workdir / "GO"
            gdir.mkdir(parents=True, exist_ok=True)
            ipr_rows = {}
            p2g: dict[str, set] = {}
            with (workdir / "Interpro" / "interproscan.tsv").open(encoding="utf-8", errors="replace") as f:
                for line in f:
                    p = line.rstrip("\n").split("\t")
                    q = p[0]
                    iprs = {m for cell in p for m in re.findall(r"IPR\d{6,}", cell)}
                    gos = {m for cell in p for m in re.findall(r"GO:\d{7}", cell)}
                    if q not in ipr_rows:
                        ipr_rows[q] = {"iprs": set(), "gos": set()}
                    ipr_rows[q]["iprs"] |= iprs
                    ipr_rows[q]["gos"] |= gos
                    p2g.setdefault(q, set()).update(gos)
            n_ipr = sum(1 for v in ipr_rows.values() if v["iprs"])
            n_go = sum(1 for v in ipr_rows.values() if v["gos"])
            with (gdir / "protein2go.tsv").open("w", encoding="utf-8") as fo:
                for q in sorted(p2g):
                    for g in sorted(p2g[q]):
                        fo.write(f"{q}\t{g}\n")
            qc = {"proteins_with_ipr": n_ipr, "proteins_with_go": n_go}
            (gdir / "qc.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
            log(f"  IPR 蛋白 {n_ipr} / GO 蛋白 {n_go}")
            mark("go", qc)
            ipr_rows_saved = ipr_rows
        else:
            ipr_rows_saved = {}

        # E. 七类集成
        if not done("integrate"):
            log("[E] 七类集成与统计")
            edir = workdir / "Integration"
            edir.mkdir(parents=True, exist_ok=True)
            order = ["NR", "Swissprot", "KEGG", "KOG", "TrEMBL"]
            hit_sets: dict[str, set] = {}
            for key in order:
                hit_sets[key] = {r["qseqid"] for r in parse_diamond_hits(
                    workdir / key / "raw_hits.tsv", qcov, log)[1].values()}
            ipr_rows = ipr_rows_saved
            if not ipr_rows:
                with (workdir / "Interpro" / "interproscan.tsv").open(encoding="utf-8", errors="replace") as f:
                    for line in f:
                        p = line.rstrip("\n").split("\t")
                        q = p[0]
                        if q not in ipr_rows:
                            ipr_rows[q] = {"iprs": set(), "gos": set()}
                        ipr_rows[q]["iprs"] |= {m for cell in p for m in re.findall(r"IPR\d{6,}", cell)}
                        ipr_rows[q]["gos"] |= {m for cell in p for m in re.findall(r"GO:\d{7}", cell)}
            ids = []
            with query.open(encoding="utf-8") as f:
                for line in f:
                    if line.startswith(">"):
                        ids.append(line[1:].split()[0])
            any_set = set()
            rows_out = []
            for q in ids:
                ann = {
                    "Nr-Annotated": int(q in hit_sets["NR"]),
                    "Swissprot-Annotated": int(q in hit_sets["Swissprot"]),
                    "KEGG-Annotated": int(q in hit_sets["KEGG"]),
                    "KOG-Annotated": int(q in hit_sets["KOG"]),
                    "TrEMBL-Annotated": int(q in hit_sets["TrEMBL"]),
                    "Interpro-Annotated": int(bool(ipr_rows.get(q, {}).get("iprs"))),
                    "GO-Annotated": int(bool(ipr_rows.get(q, {}).get("gos"))),
                }
                if any(ann.values()):
                    any_set.add(q)
                rows_out.append({"query": q, **ann,
                                 "IPR": ";".join(sorted(ipr_rows.get(q, {}).get("iprs", []))),
                                 "GO": ";".join(sorted(ipr_rows.get(q, {}).get("gos", [])))})
            with (edir / "functional_annotation.tsv").open("w", encoding="utf-8") as fo:
                fo.write("\t".join(rows_out[0].keys()) + "\n")
                for r in rows_out:
                    fo.write("\t".join(str(r[k]) for k in r) + "\n")
            total = len(ids) or 1
            stats = {"total_queries": len(ids)}
            for key in ("Nr", "Swissprot", "KEGG", "KOG", "TrEMBL", "Interpro", "GO"):
                stats[f"{key}-Annotated"] = sum(1 for r in rows_out if r[f"{key}-Annotated"])
                stats[f"{key}-Annotated_pct"] = round(100.0 * stats[f"{key}-Annotated"] / total, 2)
            stats["Any-Annotated"] = len(any_set)
            stats["Any-Annotated_pct"] = round(100.0 * len(any_set) / total, 2)
            stats["None-Annotated"] = total - len(any_set)
            with (edir / "annotation_statistics.tsv").open("w", encoding="utf-8") as fo:
                for k, v in stats.items():
                    fo.write(f"{k}\t{v}\n")
            combos: Counter = Counter()
            for r in rows_out:
                combos[tuple(r[k] for k in
                             ("Nr-Annotated", "Swissprot-Annotated", "KEGG-Annotated",
                              "KOG-Annotated", "TrEMBL-Annotated", "Interpro-Annotated",
                              "GO-Annotated"))] += 1
            with (edir / "annotation_overlap.tsv").open("w", encoding="utf-8") as fo:
                fo.write("Nr\tSwissprot\tKEGG\tKOG\tTrEMBL\tInterpro\tGO\tcount\n")
                for combo, cnt in sorted(combos.items()):
                    fo.write("\t".join(map(str, list(combo) + [cnt])) + "\n")
            val = {
                "status": "PASS",
                "checks": {
                    "all_queries_one_row": len(rows_out) == len(ids),
                    "denominator_is_total": stats["total_queries"] == s["expected_protein_count"],
                    "seven_flags_complete": all(len(r) == len(rows_out[0]) for r in rows_out),
                    "unannotated_kept": stats["None-Annotated"] >= 0,
                },
                "statistics": stats,
                "note": "技术一致性 PASS ≠ 每个功能推断正确（同源注释、候选 KO，非实验验证）",
            }
            val["status"] = "PASS" if all(val["checks"].values()) else "FAIL"
            (edir / "validation.json").write_text(
                json.dumps(val, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log(f"  Any-Annotated {stats['Any-Annotated']}/{total} = {stats['Any-Annotated_pct']}%")
            mark("integrate", stats)

        # F. 收尾
        if not done("finalize"):
            log("[F] provenance + COMPLETE")
            prov = {
                "run_id": s["run_id"], "stage": "stage4_functional", "thread_budget": budget,
                "upstream": {"input_proteins": str(prot),
                             "sha256": sha256_file(prot),
                             "expected": s["expected_input_sha256"],
                             "bound": sha256_file(prot) == s["expected_input_sha256"]},
                "tools": {"diamond": "2.1.24（settings 冻结值）",
                          "interproscan": "5.76-107.0 + Java 11（JAVA_HOME 隔离注入）"},
                "databases": {k: {"db": v["db"], "note": v.get("note")}
                              for k, v in s["databases"].items()},
                "diamond_params": s["diamond"],
                "outputs": {
                    "functional_annotation": str(workdir / "Integration" / "functional_annotation.tsv"),
                    "statistics": str(workdir / "Integration" / "annotation_statistics.tsv"),
                    "overlap": str(workdir / "Integration" / "annotation_overlap.tsv"),
                    "validation": str(workdir / "Integration" / "validation.json"),
                    "fa_sha256": sha256_file(workdir / "Integration" / "functional_annotation.tsv"),
                },
                "script_sha256": sha256_file(SCRIPT_PATH), "ts": now(),
            }
            (workdir / "provenance.json").write_text(
                json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (workdir / "COMPLETE.json").write_text(
                json.dumps({"stage": "stage4_functional", "status": "SUCCEEDED", "ts": now()},
                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            mark("finalize", {})
    except RuntimeError as exc:
        log(f"[失败] {exc}")
        log("保留现场、看日志、勿删目录；排除后 --resume 续跑或归档重来。")
        return 1

    log("=== 段 4 完成。交付物：Integration/{functional_annotation,annotation_statistics,validation}.json ===")
    log("把 statistics、validation.json 与日志尾部贴回给 skill 做基线对照。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
SKILL_EOF
cat > README.md <<'SKILL_EOF'
# 段 4：功能注释（新手版）

> 酵母项目 `yeast_s288c_loop`（run_id=batch01）第四段，也是结构→功能的总收官：给段 3 的 5,384 条蛋白打上功能标签。

## 这个阶段做什么、为什么

段 3 产出了“有哪些基因”（结构），本段回答“这些基因干什么”（功能）——两大证据源：

```
DIAMOND 同源比对 ×5 库（NR/Swiss-Prot/KEGG/KOG/TrEMBL）→ 每蛋白最佳命中 + 功能注释
InterProScan（结构域/家族 + GO 术语）→ IPR 号 + GO 富集证据
→ 七类标记集成 → 覆盖率统计 + validation.json
```

**库选择是酵母适配的关键点**（探测实测，非抄 Siganus）：

| 库 | 本用例选定 | 为什么 |
|---|---|---|
| NR | `fungi.fa.dmnd`（真菌子集） | 酵母是真菌——不用 Siganus 的动物子集 |
| Swiss-Prot | Eukaryota（含真菌）+ 描述表 | 真核范围覆盖酵母 |
| KEGG | `kegg_all_clean`（全库版） | 含真菌通路——不用 animal 子集 |
| KOG | kog_clean + .id | 真核共有功能类 |
| TrEMBL | Eukaryota + 描述表 | 真核范围覆盖酵母 |

参数沿用 Siganus 实证：`--very-sensitive -e 1e-5 -k 25 --max-hsps 1`，17 列含覆盖度，`qcovhsp≥50%` 后取最高 bitscore 为最佳命中；KEGG/KOG 近最高 5% 分数内的不同编号标 `ambiguous_near_top`（结论前须复核——候选 KO 不等同功能确认）。

## 相互关联的纪律

| 坑/纪律 | 本包防线 |
|---|---|
| PIT-004 内部歧义蛋白污染 | query 准备阶段检测内部 `.`/`*`，检出即停 |
| PIT-003 列号脆断教训 | InterProScan 输出解析按正则内容识别（`IPR\d{6,}`/`GO:\d{7}`），不依赖脆列号 |
| GO 来源纪律 | 只取本次 IPR `--goterms`，不从描述文本猜 GO |
| Java 版本隔离 | JAVA_HOME 只注入 InterProScan 子进程（Java 11），不动 base |
| 上游绑定 | 5,384 蛋白 sha256（c3258d39…）预检核验 |
| 诚实边界 | validation.json 的 PASS 是技术一致性，不是功能正确性 |

## 运行前检查单

1. 段 3 已交付（5,384 最长蛋白在位）
2. **Java 11 已装**（本包预检硬门槛）：`${HOME}/env/java11/bin/java -version` 显示 11.x
3. 四个文件落在包目录：`settings4.json`、`run_stage4.py`、`README.md`、`deploy_to_server.sh`（可选）

## 怎么跑

```bash
cd ~/yeast_test/sop/yeast_loop/stage4_functional
python3 run_stage4.py --check      # 预检：绑定/JAVA11/库/工具
nohup python3 -u run_stage4.py --execute > stage4.nohup.log 2>&1 &
# 时长预估：DIAMOND ×5 约 20-60 分钟；InterProScan 5,384 蛋白约 10-30 分钟；总计 <1.5h
```

中断续跑：`python3 run_stage4.py --execute --resume`（每库/每阶段有检查点）。

## 怎么判断成功

1. `runs/batch01/6.Functional/COMPLETE.json` = SUCCEEDED
2. `Integration/validation.json` 的 `status=PASS`（技术一致性）
3. `annotation_statistics.tsv` 的 `Any-Annotated_pct` 落在基线锚带（advisory [80, 99]——模式生物酵母预期高覆盖率；若显著偏低，第一嫌疑是库范围/过滤参数，回传层对照）

## 跑完贴回给 skill

- `Integration/annotation_statistics.tsv` 全文
- `Integration/validation.json` 全文
- `provenance.json` 全文
- 日志尾部 40 行

skill 据此做段 4 回传校验（哈希绑定 + 七类覆盖率基线对照 + 冲突标记复核），全部通过后，酵母环四段收官——到那时，**毕业包**（可复用的四段 SOP + settings + 检查点）就齐了，你会拿到一套属于你自己的、从原始数据到功能注释的完整可复用流水线（D-020 的承诺兑现）。

## 失败了怎么办

- `--resume` 续跑；某库比对失败看该库的 raw_hits.tsv 是否生成（diamond 输出在库目录）；
- InterProScan 失败先看 `Interpro/` 下日志 + 确认 Java 11（预检已拦）；`--disable-precalc` 下临时目录会保留，属正常；
- 保留现场、勿删目录；排查后重跑或贴回给我。
SKILL_EOF
cat > .expected.sha256 <<'EXPECT_EOF'
0d9b442825f2c3f303014fa981bd80afdbfd02a0f5ea49ad08342db8e04b27d8  settings4.json
9bb571725161507157c47ff1cfda55fd9814823215015d75d55cf62de83c0b22  run_stage4.py
94bfe6ef1bfff2840c2fc76637c420107a23c682276eeec9ba274ced32f43d6a  README.md
EXPECT_EOF
sha256sum -c .expected.sha256 && rm .expected.sha256 && echo '=== 落盘校验通过 ==='
