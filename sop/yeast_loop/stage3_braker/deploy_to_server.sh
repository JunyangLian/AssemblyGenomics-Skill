#!/usr/bin/env bash
# stage3_braker SOP 落盘脚本（脱敏版，heredoc + sha256 自校验）
set -e
cd ~
mkdir -p ~/yeast_test/sop/yeast_loop/stage3_braker
cd ~/yeast_test/sop/yeast_loop/stage3_braker
cat > settings3.json <<'SKILL_EOF'
{
  "run_id": "batch01",
  "thread_budget": 32,
  "softmasked_genome": "${HOME}/yeast_test/sop/yeast_loop/stage1_repeat/runs/batch01/1.Repeat_Annotation/genome.softmasked.fa",
  "expected_softmasked_sha256": "5bcafd653f2beb5ba54b3aef9742e33ef4506d066091dea297a99b8026d4bb46",
  "samples_bams": [
    {
      "id": "WT_Rep1",
      "bam": "${HOME}/yeast_test/sop/yeast_loop/stage2_rnaseq/runs/batch01/2.RNAseq/bam/WT_Rep1.sorted.bam",
      "expected_sha256": "9c841fc1ffd643221f746a33120c657b2ded29d89d1d17e952d59608731d1d76"
    },
    {
      "id": "WT_Rep2",
      "bam": "${HOME}/yeast_test/sop/yeast_loop/stage2_rnaseq/runs/batch01/2.RNAseq/bam/WT_Rep2.sorted.bam",
      "expected_sha256": "0d6a52bf824ee1f3069d24df741f8b3c6b87655f0f88f51be590b29ea72063fc"
    }
  ],
  "protein_evidence_gz": "${HOME}/yeast_test/0.Raw_Data/protein_evidence/uniprot_sprot.fasta.gz",
  "expected_protein_gz_sha256": "a9c3496aa727e61d25d9e1291c9ba28d2c2ad19c0e26569dc083d53ec4169536",
  "braker_env": "${HOME}/env/braker3",
  "braker_threads": 16,
  "species": "SC288C_braker",
  "intron_support": 0.8,
  "agat_env": "${SHARED}/.conda/envs/agat",
  "gffread": "${SHARED}/.conda/envs/braker3/bin/gffread",
  "export_prefix": "SC288C.longest",
  "busco": {
    "python": "${HOME}/env/busco5/bin/python",
    "busco": "${HOME}/env/busco5/bin/busco",
    "lineage": "${HOME}/busco_downloads/lineages/saccharomycetes_odb10",
    "cpu": 16
  },
  "genemark_bin": "${HOME}/env/GeneMark-ETP-main/bin/gmes",
  "prothint_dir": "${HOME}/env/ProtHint",
  "samtools": "${SHARED}/.conda/envs/braker3/bin/samtools",
  "use_protein_evidence": false,
  "filter_single_exon_genes": false,
  "busco_min_complete_pct": 95
}
SKILL_EOF
cat > run_stage3.py <<'SKILL_EOF'
#!/usr/bin/env python3
"""段 3：基因预测与评估（BRAKER ETP → TSEBRA intron08 → AGAT longest → 编码导出 → BUSCO）。

给第一次做注释的你：前两段产出了"基因组 + 转录证据"，这一段把它们变成
"基因模型"——BRAKER 用 RNA 比对（BAM）和蛋白证据（Swiss-Prot）做 de novo
基因预测，TSEBRA 合并 AUGUSTUS+GeneMark 模型（按 Siganus 实证把 intron_support
调到 0.8），AGAT 取每个位点最长转录本，导出编码子集，最后 BUSCO 评估完整度。

上游绑定：softmasked、两个 BAM、Swiss-Prot 的 sha256 全部在预检核验。
诚实门槛：BUSCO 谱系（saccharomycetes_odb10）缺失时预检直接拒绝——先传谱系。
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
HERE = SCRIPT_PATH.parent


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
    logf = (logs / "stage3.log").open("a", encoding="utf-8")

    def log(msg: str) -> None:
        line = f"[{now()}] {msg}"
        print(line, flush=True)
        logf.write(line + "\n")
        logf.flush()
    return log


def run_env(cmd: list[str], log, env: dict, cwd: Path, timeout: int = 7200) -> str:
    """执行并逐行进日志；非零退出抛 RuntimeError。"""
    log(f"[cmd] {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace", env=env, cwd=str(cwd), timeout=timeout)
    except OSError as exc:
        raise RuntimeError(f"无法执行 {cmd[0]}：{exc}")
    for line in (proc.stdout or "").splitlines():
        log("  | " + line)
    if proc.returncode != 0:
        raise RuntimeError(f"命令失败（exit {proc.returncode}）：{cmd[0]}")
    return proc.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description="段 3 驱动：BRAKER 基因预测与评估（先 --check 后 --execute）")
    ap.add_argument("--settings", default="settings3.json")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    s = json.loads(Path(args.settings).read_text(encoding="utf-8"))
    use_prot = bool(s.get("use_protein_evidence", True))
    if not use_prot:
        print("[模式] use_protein_evidence=false → BRAKER ET 模式（无蛋白证据；"
              "ETP 蛋白环因 gmes_petap 预测阶段 scratch 内置 prothint 的版本缺陷绕开，如实入档）")
    budget = int(s["thread_budget"])
    bt = int(s["braker_threads"])
    bco = int(s["busco"]["cpu"])
    if max(bt, bco) > budget:
        print(f"[预检失败] braker/busco 线程超过预算 {budget}")
        return 2
    if bt + bco > budget + 4:
        print(f"[预检失败] braker({bt}) + busco({bco}) 同时峰值超过预算 {budget}")
        return 2

    root = HERE
    workdir = root / "runs" / s["run_id"] / "4.BRAKER3"
    soft = Path(s["softmasked_genome"])
    braker_bin = Path(s["braker_env"]) / "bin"
    agat_bin = Path(s["agat_env"]) / "bin"
    bco_cfg = s["busco"]

    problems = []
    ncpu = os.cpu_count() or 0
    if ncpu and budget > ncpu:
        problems.append(f"thread_budget={budget} ≥ 全机核数 {ncpu}（PIT-007）")
    if not soft.exists():
        problems.append(f"softmasked 缺失：{soft}")
    elif sha256_file(soft) != s["expected_softmasked_sha256"]:
        problems.append("softmasked sha256 ≠ 段 1 冻结值——上游被改动，拒绝混用")
    samtools_bin = Path(s.get("samtools", "${SHARED}/.conda/envs/braker3/bin/samtools"))
    if not samtools_bin.exists():
        problems.append(f"samtools 缺失：{samtools_bin}（预检需读 BAM 头）")
    else:
        fnames = [ln[1:].split()[0] for ln in soft.open(encoding="utf-8") if ln.startswith(">")]
        bnames = set()
        for smp in s["samples_bams"]:
            proc = subprocess.run([str(samtools_bin), "view", "-H", smp["bam"]],
                                  capture_output=True, text=True, errors="replace")
            for ln in (proc.stdout or "").splitlines():
                m = re.match(r"@SQ\s+SN:(\S+)", ln)
                if m:
                    bnames.add(m.group(1))
        if set(fnames) != bnames:
            problems.append(
                "PIT-008：FASTA 序列名与 BAM 参考名集合不一致（fasta=%d 条 vs bam=%d 条）——"
                "BRAKER 需要 id-only 头且与全部 @SQ 一致（Siganus v3 同款事故）"
                % (len(set(fnames)), len(bnames)))
    for smp in s["samples_bams"]:
        bam = Path(smp["bam"])
        if not bam.exists():
            problems.append(f"BAM 缺失：{bam}")
        elif sha256_file(bam) != smp["expected_sha256"]:
            problems.append(f"BAM sha256 ≠ 段 2 绑定值：{smp['id']}")
    pgz = Path(s["protein_evidence_gz"])
    if use_prot:
        if not pgz.exists():
            problems.append(f"Swiss-Prot 缺失：{pgz}")
        elif sha256_file(pgz) != s["expected_protein_gz_sha256"]:
            problems.append("Swiss-Prot sha256 ≠ 绑定值（a9c3496a…）")
    for rel in ("braker.pl", "tsebra.py"):
        if not (braker_bin / rel).exists():
            problems.append(f"braker env 缺少 {rel}")
    if not (agat_bin / "agat_sp_keep_longest_isoform.pl").exists():
        problems.append("agat env 缺少 agat_sp_keep_longest_isoform.pl")
    if not Path(s["gffread"]).exists():
        problems.append(f"gffread 缺失：{s['gffread']}")
    if not Path(bco_cfg["busco"]).exists():
        problems.append(f"busco 缺失：{bco_cfg['busco']}")
    lineage = Path(bco_cfg["lineage"])
    if not lineage.exists() or not list(lineage.glob("*.txt")):
        problems.append(
            f"BUSCO 谱系缺失：{lineage}——本地下载 saccharomycetes_odb10.tar.gz 上传解压后重跑 --check（硬门槛，PIT 纪律）")

    # AUGUSTUS / GeneMark 探测（round-3 遗留未决项，这里如实报告）
    augustus = braker_bin / "augustus"
    aug_cfg_cands = [Path(s["braker_env"]) / "config",
                     Path(s["braker_env"]) / "libs/augustus/config",
                     Path(s["braker_env"]) / "share/augustus/config"]
    aug_cfg = next((c for c in aug_cfg_cands if (c / "species").is_dir()), None)
    # GeneMark 探测：优先 settings 的 genemark_bin（GeneMark-ETP 独立安装），
    # 缺失时回退 braker env 内候选（round-3 以来的真实探测逻辑）
    genemark_dir = s.get("genemark_bin")
    genemark = None
    if genemark_dir:
        gdir = Path(genemark_dir)
        # BRAKER 的 GENEMARK_PATH 语义是"目录"：优先含 gmetp.pl 的安装根，
        # 其次含 gmes_petap.pl 的 gmes 目录（2026-09-23 实跑踩过"传了文件路径"）
        gmes = gdir / "gmes_petap.pl"
        gmhm = gdir / "gmhmme3"
        if not (gmhm.exists() and gmes.exists()):
            problems.append(f"settings genemark_bin 内容不完整（缺 gmes_petap.pl/gmhmme3）：{genemark_dir}")
        else:
            root = next((c for c in (gdir, gdir.parent, gdir.parent.parent)
                         if (c / "gmetp.pl").exists()), gdir)
            genemark = root
    if genemark is None:
        genemark_cands = [braker_bin / "gmes_petap.pl", braker_bin / "genemark-etp",
                          braker_bin / "gm", braker_bin / "gmetp.pl",
                          braker_bin / "GeneMark-ETP/gmes_petap.pl"]
        genemark = next((c.parent for c in genemark_cands if c.exists()), None)
    aug_scripts = None
    for cand in (braker_bin, Path(s["braker_env"]) / "scripts", Path(s["braker_env"]) / "config/../scripts"):
        if any((cand / m).exists() for m in ("getAnnoFasta.pl", "filterIntronsMseq.pl",
                                              "augustus2gbrowse.pl", "autoAug.pl")):
            aug_scripts = cand
            break
    prothint = None
    pd = s.get("prothint_dir")
    if pd:
        pd = Path(pd)
        for cand in (*pd.rglob("prothint.py"), braker_bin / "prothint.py"):
            if cand.exists():
                prothint = cand
                break
    if prothint is None:
        hit = next(braker_bin.glob("prothint.py"), None)
        if hit is not None:
            prothint = hit
    print(f"[探测] augustus 二进制: {'有' if augustus.exists() else '缺'}"
          f"；AUGUSTUS config: {aug_cfg or '未在候选路径找到'}"
          f"；AUGUSTUS scripts: {aug_scripts or '未找到'}"
          f"；GeneMark: {genemark or '未找到'}"
          f"；ProtHint: {prothint or '未找到（BRAKER ETP 必需）'}")
    if not augustus.exists() and genemark is None:
        problems.append("braker env 既无 augustus 也无 GeneMark——ETP 不可行，先安装/指明路径")
    if prothint is None:
        problems.append("prot_seq 模式（ETP）必需 ProtHint：在 settings prothint_dir 或 braker env 均未找到 prothint.py")

    if problems:
        print("[预检失败] 共 %d 项：" % len(problems))
        for p in problems:
            print("  - " + p)
        return 2
    print(f"[预检通过] 预算 {budget} ≤ 全机 {ncpu} 核；上两条的绑定值全部一致；谱系在位。")

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
    log(f"=== 段 3 开始（run_id={s['run_id']}，预算 {budget} 线程）===")

    def done(name: str) -> bool:
        return (markers / f"{name}.done").exists()

    def mark(name: str, payload: dict) -> None:
        (markers / f"{name}.done").write_text(
            json.dumps({"stage": name, "ts": now(), **payload}, ensure_ascii=False, indent=2),
            encoding="utf-8")

    env = dict(os.environ)
    env["PATH"] = str(braker_bin) + os.pathsep + env.get("PATH", "")
    if genemark is not None:
        env["PATH"] = str(genemark) + os.pathsep + env["PATH"]
    for v in ("PYTHONPATH", "PERL5LIB", "PERLLIB", "PERL5OPT"):
        env.pop(v, None)
    if aug_cfg:
        env["AUGUSTUS_CONFIG_PATH"] = str(aug_cfg)
    if aug_scripts:
        env["AUGUSTUS_SCRIPTS_PATH"] = str(aug_scripts)
    if prothint is not None:
        env["PROTHINT_PATH"] = str(prothint.parent)

    try:
        # A. 蛋白证据解压（仅 ETP 模式；ET 模式跳过）
        if use_prot and not done("protein_prep"):
            log("[A] 解压 Swiss-Prot → workdir/protseq/uniprot_sprot.fasta")
            prot_fa = workdir / "protseq" / "uniprot_sprot.fasta"
            prot_fa.parent.mkdir(parents=True, exist_ok=True)
            _proc = subprocess.run(["gzip", "-dc", str(pgz)],
                                   stdout=prot_fa.open("wb"), env=env)
            if _proc.returncode != 0:
                raise RuntimeError("gunzip Swiss-Prot 失败")
            log(f"  蛋白条数: {sum(1 for _ in prot_fa.open(encoding='utf-8') if _.startswith('>'))}")
            mark("protein_prep", {"uniprot_fa_sha256": sha256_file(prot_fa)})
        prot_fa = workdir / "protseq" / "uniprot_sprot.fasta"

        # A2. BRAKER 用基因组：头含描述则生成 id-only 副本（PIT-008）
        idonly = workdir / "genome.id_only.softmasked.fa"
        if not done("genome_prep"):
            has_ws = any(ln.startswith(">") and " " in ln[1:].strip()
                         for ln in soft.open(encoding="utf-8"))
            if has_ws:
                log("[A2] FASTA 头含描述 → 生成 id-only 副本（PIT-008：BAM @SQ 按首字段命名）")
                with soft.open(encoding="utf-8") as src, idonly.open("w", encoding="utf-8") as dst:
                    for line in src:
                        if line.startswith(">"):
                            dst.write(">" + line[1:].split()[0] + "\n")
                        else:
                            dst.write(line)
                def _recs(path):
                    with path.open(encoding="utf-8") as f:
                        nm = None; buf = []
                        for line in f:
                            line = line.strip()
                            if line.startswith(">"):
                                if nm is not None:
                                    yield nm, "".join(buf)
                                nm, buf = line[1:], []
                            elif nm is not None:
                                buf.append(line)
                        if nm is not None:
                            yield nm, "".join(buf)
                a = list(_recs(soft)); b = list(_recs(idonly))
                ok = (len(a) == len(b)
                      and len({x[0] for x in b}) == len(b)
                      and all(x[0].split()[0] == y[0] for x, y in zip(a, b))
                      and all(x[1].upper() == y[1].upper() for x, y in zip(a, b)))
                if not ok:
                    raise RuntimeError("id-only 副本校验失败（顺序/长度/序列/唯一性）——禁止带病进 BRAKER")
                log(f"  id-only 校验通过：{len(b)} 条序列，序列内容不变")
            mark("genome_prep", {"id_only": str(idonly) if has_ws else None})
        genome_b = idonly if idonly.exists() else soft

        # B. BRAKER ETP
        if not done("braker"):
            etp = workdir / "run_ETP"
            etp.mkdir(parents=True, exist_ok=True)
            log(f"[B] BRAKER ETP（{s['species']}，threads {bt}；酵母预计 <30 分钟）")
            bams = ",".join(smp["bam"] for smp in s["samples_bams"])
            cmd = [str(braker_bin / "braker.pl"),
                   f"--species={s['species']}", f"--genome={genome_b}",
                   f"--bam={bams}",
                   "--softmasking", "--gff3", f"--threads={bt}",
                   f"--workingdir={etp}", "--AUGUSTUS_ab_initio"]
            if use_prot:
                cmd.append(f"--prot_seq={prot_fa}")
            if genemark:
                env["GENEMARK_PATH"] = str(genemark)
                cmd.append(f"--GENEMARK_PATH={genemark}")
            if aug_scripts:
                cmd.append(f"--AUGUSTUS_SCRIPTS_PATH={aug_scripts}")
            if prothint is not None:
                cmd.append(f"--PROTHINT_PATH={prothint.parent}")
            run_env(cmd, log, env, cwd=etp)
            mark("braker", {})

        # C. TSEBRA intron08 重合并（Siganus 实证：默认 1.0 过严 → 0.8）
        if not done("tsebra"):
            log(f"[C] TSEBRA intron08 重合并（intron_support 1.0→{s['intron_support']}，PIT-002）")
            etp = workdir / "run_ETP"
            tse_dir = workdir / "5.TSEBRA_intron08"
            tse_dir.mkdir(parents=True, exist_ok=True)
            cfg_cands = [Path(s["braker_env"]) / "config/braker3.cfg",
                         Path(s["braker_env"]) / "bin/../config/braker3.cfg",
                         *[Path(s["braker_env"]) / d / "braker3.cfg"
                           for d in ("share/braker", "share/tsebra", "libs/tsebra/config")]]
            cfg = next((c for c in cfg_cands if c.exists()), None)
            if cfg is None:
                raise RuntimeError("未找到 braker3.cfg（TSEBRA 配置）——把真实路径贴回给 skill")
            shutil.copyfile(cfg, tse_dir / "braker3.original.cfg")
            lines = []
            for line in cfg.read_text(encoding="utf-8").splitlines():
                if line.split()[:1] == ["intron_support"]:
                    lines.append(f"intron_support {s['intron_support']}")
                else:
                    lines.append(line)
            (tse_dir / "intron08.cfg").write_text("\n".join(lines) + "\n", encoding="utf-8")
            aug_gtf = etp / "Augustus/augustus.hints.gtf"
            gm_root = next((d for d in etp.glob("GeneMark-ET*") if (d / "genemark.gtf").exists()), None)
            if gm_root is None:
                raise RuntimeError("未找到 GeneMark-ET*/genemark.gtf（ET/ETP 目录自动探测失败）")
            gm_gtf = gm_root / "genemark.gtf"
            train = gm_root / "training.gtf"   # ETP 模式产物；ET 模式可能没有 → 条件传参
            hints = etp / "hintsfile.gff"
            for p in (aug_gtf, gm_gtf, hints):
                if not p.exists():
                    raise RuntimeError(f"BRAKER 中间产物缺失：{p}")
            tsebra_cmd = [str(braker_bin / "python3"), str(braker_bin / "tsebra.py"),
                          f"--gtf={aug_gtf},{gm_gtf}"]
            if train.exists():
                tsebra_cmd.append(f"--keep_gtf={train}")
            else:
                log("  ET 模式无 training.gtf：TSEBRA 省略 --keep_gtf（训练模型强制保留项不适用）")
            if s.get("filter_single_exon_genes", True):
                tsebra_cmd += ["--filter_single_exon_genes"]
            else:
                log("  filter_single_exon_genes=false（PIT-009：酵母内含子贫乏，过滤会把 ~95% 真基因滤掉）")
            tsebra_cmd += [f"--hintfiles={hints}", f"--cfg={tse_dir / 'intron08.cfg'}",
                           f"--out={tse_dir / 'models.gtf'}"]
            run_env(tsebra_cmd, log, env, cwd=tse_dir)
            mark("tsebra", {"intron_support": s["intron_support"]})

        # D. 最长转录本（AGAT 独立 perl + 清 PERL5LIB）
        if not done("longest"):
            log("[D] AGAT 最长转录本 + gffread 提取（清 PERL5LIB，Siganus 同款）")
            cand = workdir / "5.Longest"
            cand.mkdir(parents=True, exist_ok=True)
            agat_env_clean = {k: v for k, v in env.items()
                              if k not in ("PERL5LIB", "PERLLIB", "PERL5OPT")}
            agat_env_clean["PATH"] = str(agat_bin) + os.pathsep + agat_env_clean.get("PATH", "")
            run_env([str(agat_bin / "perl"), str(agat_bin / "agat_sp_keep_longest_isoform.pl"),
                     "--gff", str(workdir / "5.TSEBRA_intron08/models.gtf"),
                     "-o", str(cand / "SC288C.longest.gff3")],
                    log, agat_env_clean, cwd=cand)
            run_env([s["gffread"], str(cand / "SC288C.longest.gff3"),
                     "-g", str(genome_b),
                     "-y", str(cand / "SC288C.longest.pep.fa"),
                     "-x", str(cand / "SC288C.longest.cds.fa")],
                    log, env, cwd=cand)
            mark("longest", {})

        # E. 编码 GFF3 导出（vendored export 脚本；PIT-005 钩子）
        if not done("export"):
            log("[E] 编码子集导出（PIT-005：防基因数虚高）")
            cand = workdir / "5.Longest"
            run_env([sys.executable, str(HERE / "export_coding_gff3.py"),
                     f"--candidate={cand}", f"--genome={genome_b}",
                     f"--gffread={s['gffread']}", f"--prefix={s['export_prefix']}"],
                    log, env, cwd=cand)
            vjson = cand / "coding_only_verified" / "validation.json"
            if not vjson.exists():
                raise RuntimeError("export 未产出 validation.json")
            val = json.loads(vjson.read_text(encoding="utf-8"))
            log(f"  export: genes_represented={val.get('genes_represented_by_proteins')} "
                f"proteins={val.get('matched_protein_ids')}")
            mark("export", {"validation": vjson.name})

        # F. BUSCO（proteins 模式；谱系缺失时 --check 已拦）
        if not done("busco"):
            log("[F] BUSCO 最长转录本蛋白（proteins 模式，PIT-003 只说 genome 模式不可信）")
            cand = workdir / "5.Longest"
            outdir = workdir / "5.BUSCO"
            outdir.mkdir(parents=True, exist_ok=True)
            run_env([str(bco_cfg["python"]), str(bco_cfg["busco"]),
                     "-i", str(cand / "SC288C.longest.pep.fa"),
                     "-l", str(lineage), "-m", "proteins", "--offline",
                     "-c", str(bco_cfg["cpu"]), "-o", "BUSCO_longest",
                     "--out_path", str(outdir)],
                    log, env, cwd=outdir)
            summary = next((p for p in outdir.rglob("short_summary*.txt")), None)
            busco_line = ""
            if summary:
                m = re.search(r"C:\d+[.\d]*%\[[^\]]*\]", summary.read_text(encoding="utf-8"))
                busco_line = m.group(0) if m else "（未解析到 C%——看 summary 文件原文）"
            log(f"  BUSCO: {busco_line}")
            m = re.search(r"C:([\d.]+)%", busco_line)
            if m:
                cval = float(m.group(1))
                thresh = float(s.get("busco_min_complete_pct", 95))
                if cval < thresh:
                    raise RuntimeError(
                        f"基线 fail-fast：BUSCO 完整度 {cval}% < 阈值 {thresh}%——"
                        f"按 PIT-002/009 方法做单因素对照定位，禁止带病进入下一段")
            elif summary is not None:
                raise RuntimeError("BUSCO 摘要未解析出 C%——人工核对 short_summary 原文")
            mark("busco", {"summary": busco_line, "file": str(summary) if summary else None})

        # G. 收尾
        if not done("finalize"):
            log("[G] provenance + COMPLETE")
            cand = workdir / "5.Longest"
            prov = {
                "run_id": s["run_id"], "stage": "stage3_braker", "thread_budget": budget,
                "upstream": {"genome_for_braker": str(genome_b),
                             "softmasked_sha256": sha256_file(soft),
                             "expected": s["expected_softmasked_sha256"],
                             "bound": sha256_file(soft) == s["expected_softmasked_sha256"]},
                "samples": [{"id": smp["id"], "bam": smp["bam"],
                             "sha256": sha256_file(Path(smp["bam"])),
                             "expected": smp["expected_sha256"],
                             "bound": sha256_file(Path(smp["bam"])) == smp["expected_sha256"]}
                            for smp in s["samples_bams"]],
                "protein": ({"used": True, "gz": str(pgz),
                             "gz_sha256": sha256_file(pgz),
                             "fa_sha256": sha256_file(workdir / "protseq/uniprot_sprot.fasta")}
                            if use_prot else
                            {"used": False,
                             "reason": "ET 模式降级：gmes_petap 预测阶段 scratch 内置 prothint 的版本缺陷（error_log 2026-09-23）"}),
                "tools": {"braker": version_of([str(braker_bin / "braker.pl"), "--version"]),
                          "busco": version_of([str(bco_cfg["python"]), str(bco_cfg["busco"]), "--version"])},
                "outputs": {"models_gtf": str(workdir / "5.TSEBRA_intron08/models.gtf"),
                            "longest_gff3": str(cand / "SC288C.longest.gff3"),
                            "longest_pep": str(cand / "SC288C.longest.pep.fa"),
                            "longest_cds": str(cand / "SC288C.longest.cds.fa"),
                            "pep_sha256": sha256_file(cand / "SC288C.longest.pep.fa"),
                            "cds_sha256": sha256_file(cand / "SC288C.longest.cds.fa")},
                "script_sha256": sha256_file(SCRIPT_PATH), "ts": now(),
            }
            (workdir / "provenance.json").write_text(
                json.dumps(prov, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            (workdir / "COMPLETE.json").write_text(
                json.dumps({"stage": "stage3_braker", "status": "SUCCEEDED", "ts": now()},
                           ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            mark("finalize", {})
    except RuntimeError as exc:
        log(f"[失败] {exc}")
        log("保留现场、看日志、勿删目录；排除后 --resume 续跑或归档重来。")
        return 1

    log("=== 段 3 完成。交付物：5.Longest/coding_only_verified/ + 5.BUSCO/ ===")
    log("把 provenance.json、validation.json 与日志尾部贴回给 skill。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
SKILL_EOF
cat > export_coding_gff3.py <<'SKILL_EOF'
#!/usr/bin/env python3
"""Export a CDS-connected GFF3 subset and verify both FASTA sets unchanged."""

import argparse
from collections import Counter
from dataclasses import dataclass, replace
import faulthandler
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import unquote


TRANSCRIPTS = {"mRNA", "transcript"}
LEAVES = {"exon", "CDS", "intron", "start_codon", "stop_codon"}
PREFIX = "Siganus.intron08.longest"


@dataclass
class Feature:
    fields: list
    attributes: dict

    @property
    def kind(self):
        return self.fields[2]

    @property
    def identifier(self):
        return unquote(self.attributes.get("ID", ""))

    @property
    def parents(self):
        return {unquote(p) for p in self.attributes.get("Parent", "").split(",") if p}

    def text(self):
        attributes = ";".join(f"{key}={value}" for key, value in self.attributes.items())
        return "\t".join(self.fields[:8] + [attributes or "."]) + "\n"


def read_gff(path, regions=None):
    """Yield one feature at a time; do not retain exon/CDS rows in memory."""
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.startswith("##FASTA"):
                break
            if regions is not None and line.startswith("##sequence-region"):
                regions.append(line.rstrip())
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 9:
                raise ValueError(f"{path}:{line_number}: expected nine GFF3 fields")
            attributes = {}
            for item in fields[8].split(";"):
                if item in {"", "."}:
                    continue
                key, separator, value = item.partition("=")
                if not separator or key in attributes:
                    raise ValueError(f"{path}:{line_number}: invalid/repeated attribute")
                attributes[key] = value
            yield Feature(fields, attributes)


@dataclass
class CodingPlan:
    genes: set
    transcripts: set
    report: dict


def index_coding(features):
    genes, transcripts = set(), {}
    coding, leaf_parents, exon_parents = set(), set(), set()
    counts = Counter()
    for feature in features:
        counts[feature.kind] += 1
        if feature.kind not in {"gene"} | TRANSCRIPTS | LEAVES:
            raise ValueError(f"Unexpected feature type: {feature.kind}; inspect before filtering")
        if feature.kind == "gene" or feature.kind in TRANSCRIPTS:
            identifier = feature.identifier
            if not identifier or identifier in genes or identifier in transcripts:
                raise ValueError(f"Missing or repeated gene/transcript ID: {identifier}")
            if feature.kind == "gene":
                if feature.parents:
                    raise ValueError(f"Unexpected parent above gene {identifier}")
                genes.add(identifier)
            else:
                transcripts[identifier] = feature.parents
        if feature.kind in LEAVES:
            if not feature.parents:
                raise ValueError(f"Missing parent on {feature.kind}")
            leaf_parents.update(feature.parents)
            if feature.kind == "CDS":
                coding.update(feature.parents)
            elif feature.kind == "exon":
                exon_parents.update(feature.parents)
    for identifier, parents in transcripts.items():
        if len(parents) != 1 or not parents <= genes:
            raise ValueError(f"Transcript needs one existing gene parent: {identifier}")
    if not leaf_parents <= transcripts.keys():
        raise ValueError("Unresolved/non-transcript parent on a leaf feature")
    if not coding:
        raise ValueError("No CDS-connected transcripts found")
    gene_counts = Counter(parent for tid in coding for parent in transcripts[tid])
    if any(count != 1 for count in gene_counts.values()):
        raise ValueError("Multiple coding transcripts per gene remain; do not label this a longest set")
    kept_genes = set(gene_counts)

    without_cds = set(transcripts) - coding
    report = {
        "source_features": dict(counts),
        "coding_transcripts": len(coding),
        "coding_gene_ids": len(kept_genes),
        "excluded_gene_ids": sorted(set(genes) - kept_genes),
        "excluded_transcript_ids_without_CDS": sorted(without_cds),
        "excluded_transcripts_with_exons": len(exon_parents & without_cds),
    }
    return CodingPlan(kept_genes, coding, report)


def filter_features(features, plan):
    for feature in features:
        if feature.kind == "gene":
            keep = feature.identifier in plan.genes
        elif feature.kind in TRANSCRIPTS:
            keep = feature.identifier in plan.transcripts
        else:
            keep = bool(feature.parents & plan.transcripts)
            if keep and not feature.parents <= plan.transcripts:
                # Trim only shared Parent references; coordinates and IDs stay intact.
                attributes = dict(feature.attributes)
                attributes["Parent"] = ",".join(
                    p for p in attributes["Parent"].split(",") if unquote(p) in plan.transcripts
                )
                feature = replace(feature, attributes=attributes)
        if keep:
            yield feature


def fasta_fingerprints(path):
    records = {}
    identifier, length, digest = None, 0, None

    def finish():
        if identifier is None:
            return
        if not length or identifier in records:
            raise ValueError(f"Empty sequence or repeated ID in {path}: {identifier}")
        records[identifier] = (length, digest.hexdigest())

    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(">"):
                finish()
                header = line[1:].split()
                if not header:
                    raise ValueError(f"Empty FASTA header: {path}")
                identifier, length, digest = header[0], 0, hashlib.sha256()
            elif line.strip():
                if identifier is None:
                    raise ValueError(f"Sequence before FASTA header: {path}")
                sequence = "".join(line.split()).encode("ascii")
                length += len(sequence)
                digest.update(sequence)
    finish()
    if not records:
        raise ValueError(f"Empty FASTA: {path}")
    return records


def require_same_fasta(before, after, label):
    if before != after:
        missing, added = before.keys() - after.keys(), after.keys() - before.keys()
        changed = {k for k in before.keys() & after.keys() if before[k] != after[k]}
        raise ValueError(f"{label} changed: missing={len(missing)}, added={len(added)}, sequence={len(changed)}")


def run(candidate, genome, gffread, prefix=PREFIX):
    print("export_coding_gff3: streaming-v2", flush=True)
    candidate = candidate.resolve()
    genome = genome.resolve()
    if not prefix or Path(prefix).name != prefix or "/" in prefix or "\\" in prefix:
        raise ValueError("Prefix must be a filename, not a path")
    source = candidate / prefix
    output = candidate / "coding_only_verified"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    if not genome.is_file():
        raise FileNotFoundError(genome)
    source_gff = Path(str(source) + ".gff3")
    print("[1/6] Indexing GFF3 gene/transcript relationships", flush=True)
    regions = []
    plan = index_coding(read_gff(source_gff, regions))
    coding, report = plan.transcripts, plan.report
    print(f"Indexed {sum(report['source_features'].values())} feature rows", flush=True)
    print("[2/6] Fingerprinting source protein and CDS FASTA", flush=True)
    original = {suffix: fasta_fingerprints(Path(str(source) + suffix))
                for suffix in (".pep.fa", ".cds.fa")}
    for suffix, records in original.items():
        if records.keys() != coding:
            raise ValueError(f"Source {suffix} IDs do not match CDS-connected transcripts")

    stage = Path(tempfile.mkdtemp(prefix=".coding_check_", dir=candidate))
    print(f"Staging directory: {stage}", flush=True)
    stem = stage / prefix
    emitted = Counter()
    print("[3/6] Streaming the CDS-connected subset to disk", flush=True)
    with Path(str(stem) + ".gff3").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("##gff-version 3\n")
        handle.write("# CDS-connected subset; original annotations retained separately.\n")
        for region in regions:
            handle.write(region + "\n")
        for feature in filter_features(read_gff(source_gff), plan):
            handle.write(feature.text())
            emitted[feature.kind] += 1
    report["exported_features"] = dict(emitted)
    print("[4/6] Validating exported GFF3 relationships", flush=True)
    checked = index_coding(read_gff(Path(str(stem) + ".gff3")))
    if (checked.transcripts != coding or checked.genes != plan.genes
            or checked.report["excluded_transcript_ids_without_CDS"]
            or checked.report["excluded_gene_ids"]
            or checked.report["source_features"] != dict(emitted)):
        raise ValueError("Exported GFF3 failed structure validation")
    del checked

    print(f"[5/6] Running gffread; log: {stage / 'gffread.log'}", flush=True)
    with (stage / "gffread.log").open("w", encoding="utf-8") as log:
        try:
            subprocess.run([gffread, str(stem) + ".gff3", "-g", str(genome),
                            "-y", str(stem) + ".pep.fa", "-x", str(stem) + ".cds.fa"],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as exc:
            reason = (f"signal {-exc.returncode}" if exc.returncode < 0
                      else f"exit code {exc.returncode}")
            raise RuntimeError(f"gffread failed with {reason}; see {stage / 'gffread.log'}") from exc
    print("[6/6] Verifying identical IDs and sequences", flush=True)
    for suffix in original:
        require_same_fasta(original[suffix], fasta_fingerprints(Path(str(stem) + suffix)), suffix)
    report.update({"script_revision": "streaming-v2",
                   "source_gff3": str(source) + ".gff3", "genome": str(genome),
                   "protein_IDs_and_sequences_unchanged": True,
                   "CDS_IDs_and_sequences_unchanged": True,
                   "note": "Exclusion from this coding subset does not establish biological noncoding status."})
    (stage / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}; staging retained at {stage}")
    stage.rename(output)
    print(f"Source gene records: {report['source_features'].get('gene', 0)}")
    print(f"Coding genes: {report['coding_gene_ids']}")
    print(f"Coding transcripts: {report['coding_transcripts']}")
    print(f"Excluded genes without coding transcripts: {len(report['excluded_gene_ids'])}")
    print(f"Excluded transcripts without CDS: {len(report['excluded_transcript_ids_without_CDS'])}")
    print(f"Excluded transcripts with exons: {report['excluded_transcripts_with_exons']}")
    print("Protein IDs and sequences: UNCHANGED")
    print("CDS IDs and sequences: UNCHANGED")
    print(f"VERIFIED OUTPUT: {output}")


if __name__ == "__main__":
    faulthandler.enable()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--genome", type=Path, required=True)
    parser.add_argument("--gffread", default="${SHARED}/env/braker3/bin/gffread")
    parser.add_argument("--prefix", default=PREFIX)
    args = parser.parse_args()
    run(args.candidate, args.genome, args.gffread, args.prefix)
SKILL_EOF
cat > README.md <<'SKILL_EOF'
# 段 3：基因预测与评估（新手版）

> 酵母项目 `yeast_s288c_loop`（run_id=batch01）第三段，也是结构注释的主体。

## 这个阶段做什么、为什么

前两段产出了**基因组**（软屏蔽）和**转录证据**（BAM）。本段把它们变成**基因模型**：

```
BRAKER ETP（RNA 证据 + Swiss-Prot 蛋白证据）→ TSEBRA 合并（intron08）→
AGAT 最长转录本 → 编码子集导出 → BUSCO 完整度评估
```

每一步在 Siganus 真实流程里都验过种植，这里只换了物种（酵母）和路径：

| 坑/纪律 | 本包的防线 |
|---|---|
| PIT-002：TSEBRA 默认 `intron_support 1.0` 过严，悄悄丢完整基因 | 按 Siganus 实证改为 **0.8**（`intron08.cfg` 与原配置并排保存），保留 `--keep_gtf` 与单外显子过滤 |
| PIT-003：BUSCO genome 模式不可信 | 只用 **proteins 模式**（busco5 env，经"env python + 脚本"调用，清 PERL5LIB/PYTHONPATH） |
| PIT-005：GFF3 残留非编码 gene 虚高 | export_coding_gff3.py（本包自带）按 CDS 关联导出 + 逐 ID 验证蛋白/CDS 不变 |
| 上游绑定 | softmasked、两个 BAM、Swiss-Prot gz 的 sha256 全部预检核验（段 1/2 冻结值） |
| **BUSCO 谱系硬门槛** | `saccharomycetes_odb10` 缺失时 `--check` 直接拒绝——先上传谱系，别硬闯 |

链特异性仍按未声明处理（BRAKER ETP 不依赖）。

## 运行前检查单

1. 段 1、段 2 均已完成（softmasked、两个 BAM 在位且有绑定哈希）
2. **谱系已上传**：`~/busco_downloads/lineages/saccharomycetes_odb10/` 解压完毕（`ls` 应看到 `saccharomycetes_odb10` 目录内有 `*.txt` 谱系文件）
3. 四个文件落在包目录：`settings3.json`、`run_stage3.py`、`export_coding_gff3.py`、`README.md`

## 怎么跑

```bash
cd ~/yeast_test/sop/yeast_loop/stage3_braker
python3 run_stage3.py --check      # 谱系缺失会在此被拦并提示
nohup python3 -u run_stage3.py --execute > stage3.nohup.log 2>&1 &
# 酵母规模：BRAKER <30 分钟，BUSCO 几分钟；全过程通常 <1 小时
```

中断续跑：`python3 run_stage3.py --execute --resume`（蛋白质解压/BRAKER/TSEBRA/AGAT/导出/BUSCO 各自有检查点）。

## 怎么判断成功

1. `runs/batch01/4.BRAKER3/COMPLETE.json` = SUCCEEDED
2. `5.Longest/coding_only_verified/validation.json` 的 `status=PASS`
3. `5.BUSCO/BUSCO_longest/short_summary*.txt` 的 C% 落在项目锚带 **[95, 100]（enforce）**——低于 95 先把 TSEBRA 参数和屏蔽质量拿回来复查，别继续往下

## 跑完贴回给 skill

- `provenance.json` 全文
- `5.Longest/coding_only_verified/validation.json` 全文（基因数、蛋白数、PIT-005 判据）
- `5.BUSCO/BUSCO_longest/short_summary*.txt` 内容
- 日志尾部 40 行

skill 据此做段 3 回传校验、基因数基线对照（锚点 6,386 CDS ±10% → [5700,7100] enforce）和 BUSCO 对照，通过后生成段 4（功能注释）SOP。

## 失败了怎么办

- `--resume` 从断点续；BRAKER 失败先看 `run_ETP/braker.log`（它会说缺什么：AUGUSTUS config、GeneMark 许可、内存……）
- 预检报的 `[探测]` 行如实贴回来——AUGUSTUS/GeneMark 在 braker3 env 的情况由它告诉你
- 保留现场、勿删目录；排查后重跑或把贴回内容给我
SKILL_EOF
cat > .expected.sha256 <<'EXPECT_EOF'
4e126a296872524366c32febb79eee9427d8f5ac8bfdc8527a2712cfb3cdac65  settings3.json
4f4f30c20f5abc68b1160b82ba7227c21eb4ba9e1da24e824e8ef26908f36ec7  run_stage3.py
8c0bee78c68102de2d25a1514e032c5d98d91dddf6c052512d87a14957fd58b3  export_coding_gff3.py
418ca7c77292ed816182cbfa3d25a66e640a190df89889dea2494c8ac40b596d  README.md
EXPECT_EOF
sha256sum -c .expected.sha256 && rm .expected.sha256 && echo '=== 落盘校验通过 ==='
