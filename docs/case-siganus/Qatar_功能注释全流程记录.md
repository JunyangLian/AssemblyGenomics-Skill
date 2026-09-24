# Qatar 黄斑蓝子鱼基因功能注释全流程记录

整理日期：2026-09-08  
项目目录名：`Siganus_qatar`  
记录依据：服务器运行日志、用户反馈的正式统计与验证报告，以及本项目交付的注释、恢复和绘图脚本。

> 当前已确认：100 条代表蛋白测试通过；26,467 条代表蛋白的正式 0–8 步完成，整合验证为 `PASS`。独立第 9 步绘图脚本已交付，本地已按正式汇总生成注释覆盖率图；尚未收到服务器第 9 步的最终运行报告，因此本记录不将全部 Venn/分类图标记为已完成。
>
> 本文兼作操作记录和复现说明。已经完成的注释不需要为了整理文档重新运行。文中的数据库日期/版本目录名按实际路径记录，不能替代数据库提供方的正式 release 记录。

## 1. 服务器位置与目录约定

服务器项目的**绝对路径**：

```text
${HOME}/Siganus_annotation/Siganus_qatar
```

登录用户 `USER` 下可简写为 `~/Siganus_annotation/Siganus_qatar`。软件安装路径中另有 `${SHARED}/`，这是服务器上的实际共享软件位置，不能替换成 `${HOME}/`。

本文后续命令默认先进入项目目录：

```bash
cd ${HOME}/Siganus_annotation/Siganus_qatar
```

目录组织如下；第 9 步为新增绘图目录：

```text
Siganus_qatar/
├── 0.Raw_Data/                 原始输入、正式 query、蛋白与基因对应清单
├── 1.NR/                       NR 动物子集同源注释
├── 2.Swissprot/                Swiss-Prot 真核子集同源注释
├── 3.KEGG/                     KEGG 动物子集比对与候选 KO
├── 4.KOG/                      KOG 比对、编号/类别及恢复审计
├── 5.TrEMBL/                   TrEMBL 真核子集同源注释
├── 6.Interpro/                 InterProScan、IPR 和 GO 原始证据
├── 7.GO/                       蛋白/基因到 GO 的去重映射
├── 8.Integration/              七类注释总表、统计及验证
├── 9.Figures/                  绘图结果、数表、分类资源及审计
├── scripts/                    正式配置、0–8 步总控、KOG 恢复、独立第 9 步
├── test/
│   ├── scripts/                测试配置、0–8 步脚本及正式脚本生成器
│   ├── 0.Raw_Data/ … 8.Integration/
│   ├── run_manifest.json
│   └── run_all.log
├── run_manifest.json           正式运行的配置、输入指纹和软件/数据库信息
├── full_annotation.log         正式第一次总控日志，记录 KOG 中止
├── kog_recovery.log            KOG 恢复及后续 5–8 步日志
└── figures.log                 第 9 步绘图日志（启动后产生）
```

## 2. 原始数据与统计单位

所有原始文件均位于：

```text
${HOME}/Siganus_annotation/Siganus_qatar/0.Raw_Data/
```

| 文件 | 用途 |
|---|---|
| `protein.faa` | 功能注释的蛋白序列输入，共 38,462 条 |
| `genomic.gff` | 将蛋白追溯至基因，并选择代表蛋白 |
| `GCA_053572195.1_QU_Sigcan_1.0_genomic.fna` | 基因组序列；本次蛋白功能注释不直接对它运行 blastp |
| `GCA_053572195.1_QU_Sigcan_1.0_genomic.fna.fai` | 基因组 FASTA 索引 |
| `cds_from_genomic.fna` | CDS 序列；保留供其他分析使用 |
| `genomic.gff_db` | 已有 GFF 数据库文件；本流程读取原始 GFF 建立映射 |

本次统计单位为 **`gene_representative`**，即每个基因的一条最长蛋白代表序列。等长时按蛋白 ID 字典序选择。蛋白 ID 的版本号保留，不直接去掉 `.1` 等后缀。

| 输入处理指标 | 正式结果 |
|---|---:|
| 输入蛋白数 `input_proteins` | 38,462 |
| 可选代表基因数 `eligible_units` | 26,467 |
| 正式 query 数 `selected_queries` | 26,467 |
| 正式样本参数 `requested_sample_size` | 0，表示全部 |
| 抽样随机种子 `seed` | 20260907 |
| 移除末端终止符次数 `terminal_stop_edits` | 0 |

正式第 0 步生成的关键文件：

| 服务器绝对路径 | 内容 |
|---|---|
| `${HOME}/Siganus_annotation/Siganus_qatar/0.Raw_Data/query.faa` | 全部数据库统一使用的 26,467 条 query |
| `${HOME}/Siganus_annotation/Siganus_qatar/0.Raw_Data/protein_manifest.tsv` | 全量蛋白、基因对应及代表/选中状态 |
| `${HOME}/Siganus_annotation/Siganus_qatar/0.Raw_Data/query_manifest.tsv` | 本轮选中 query 清单及基因对应 |
| `${HOME}/Siganus_annotation/Siganus_qatar/0.Raw_Data/sequence_edits.tsv` | 序列修改记录 |
| `${HOME}/Siganus_annotation/Siganus_qatar/0.Raw_Data/qc.json` | 输入处理统计 |

因此本文“基因注释率”严格指上述代表序列的覆盖率，不是所有异构体功能的并集，也不包括没有输入蛋白的非编码基因。

## 3. 软件与数据库位置

### 3.1 软件

| 软件/配置 | 服务器位置或要求 |
|---|---|
| DIAMOND，正式日志实际调用 | `${SHARED}/.conda/envs/braker3/bin/diamond` |
| InterProScan，正式日志实际调用 | `${SHARED}/ann/interproscan-5.76-107.0/interproscan.sh` |
| Python 注释入口 | `${HOME}/Siganus_annotation/Siganus_qatar/scripts/pipeline.py`；Python ≥3.9，注释代码使用标准库 |
| 正式配置 | `${HOME}/Siganus_annotation/Siganus_qatar/scripts/config.json` |
| 测试配置 | `${HOME}/Siganus_annotation/Siganus_qatar/test/scripts/config.json` |
| Java | 使用适配该 InterProScan 5 安装的 Java 11；通过配置 `java_home` 给子进程设置 |
| 绘图 Python | 建议独立 Conda 环境 `siganus_figures`，包含 matplotlib、numpy、scipy |

服务器 base 曾显示 Java 25；不能以 base 的 `java -version` 推断 InterProScan 实际使用的 Java。当前会话未提供最终 Java 11 的绝对安装路径，需从服务器正式配置读取，本文不猜测。

```bash
python3 - <<'PY'
import json
from pathlib import Path
c = json.loads(Path('scripts/config.json').read_text())
for key in ('diamond', 'interproscan', 'java_home', 'threads', 'sample_size'):
    print(f'{key}: {c.get(key)}')
PY
```

### 3.2 比对库及配套注释表

下列 `.dmnd` 路径与正式比对日志一致。Swiss-Prot/TrEMBL 描述表路径来自已交付配置，最终归档以服务器 `scripts/config.json` 和 `run_manifest.json` 为准。

| 数据库 | DIAMOND 数据库绝对路径 |
|---|---|
| NR 动物子集 | `${DB}/nr_20240416_diamond_v2.1.9.163/animal.fa.dmnd` |
| Swiss-Prot 真核子集 | `${DB}/swissport/diamond/uniprot_sprot.Eukaryota.fasta.simple.dmnd` |
| KEGG 动物子集 | `${DB}/kegg/101.0/animal.fa.dmnd` |
| KOG | `${DB}/kog/20090331/kog_clean.fa.dmnd` |
| TrEMBL 真核子集 | `${DB}/trembl/uniprot_trembl.Eukaryota.fasta.simple.dmnd` |

| 数据库 | 配套描述/功能映射来源 |
|---|---|
| NR | DIAMOND 输出 `stitle`；不能用其他物种范围的描述表替代 |
| Swiss-Prot | `${DB}/swissport/uniprot_sprot.Eukaryota.id.annot.xls` |
| KEGG | `${DB}/kegg/101.0/animal.id.annot.xls` |
| KOG | `${DB}/kog/20090331/kog_clean.fa.id` |
| TrEMBL | `${DB}/trembl/uniprot_trembl.Eukaryota.fasta.simple.ann.tsv` |

`swissport` 是服务器实际目录拼写，不能改写成 `swissprot`。带 `.xls` 后缀的配套表在本流程中按文本 TSV 使用。

### 3.3 绘图新增的分类资源

这两项服务于第 9 步分类，不改变已完成的比对和功能赋值：

| 默认服务器保存路径 | 来源与用途 |
|---|---|
| `${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/mapping/go-basic.obo` | `https://current.geneontology.org/ontology/go-basic.obo`；GO 名称、BP/CC/MF 和祖先关系 |
| `${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/mapping/ko00001.json` | `https://rest.kegg.jp/get/br:ko00001/json`；KO 到 KEGG 通路分类 |

资源在下载后产生同名 `.provenance.json`，记录 URL、时间与 SHA256。新下载的分类版本不自动等于原 KEGG 101.0 或 InterProScan 所带 GO 的版本。若要保持历史版本一致，应指定配套历史文件。当前尚未收到服务器实际使用这两个资源的报告。

## 4. 注释参数与判定规则

正式日志中的 DIAMOND 参数：

```text
blastp
--evalue 1e-5
--max-target-seqs 25
--max-hsps 1
--very-sensitive
--threads 32
--block-size 2.0
--index-chunks 4
--outfmt 6 qseqid sseqid pident length mismatch gapopen qstart qend
           sstart send evalue bitscore qlen slen qcovhsp scovhsp stitle
```

每个数据库先保存原始命中，再由 Python 进行过滤和最佳命中选择。交付配置中查询覆盖度阈值为 `qcovhsp ≥ 50%`；不额外限制 identity 或 subject coverage（对应配置均为 0）。正式使用值应以服务器归档配置为准。

最佳命中首先按 bitscore 排序，并用 E-value、查询覆盖度及 subject ID 处理并列。近最高 bitscore 的 5% 范围用于检查 KO/KOG 候选冲突。覆盖度为单 HSP 覆盖度；这些阈值是本分析规则，不是功能正确性的通用保证。

原先只保留一个命中的 NR m8 不作为本次正式整合的输入。新流程已重跑 NR，保留 25 个候选及覆盖度等证据。旧文件可留作历史对照：

```text
${HOME}/Siganus_annotation/Siganus_qatar/1.NR/Siganus_qatar_NR.m8
${HOME}/Siganus_annotation/Siganus_qatar/1.NR/Siganus_NR.log
```

七类标记的定义：

| 标记 | 计入条件 |
|---|---|
| `Nr-Annotated` | 有通过过滤的 NR 命中 |
| `Swissprot-Annotated` | 有通过过滤的 Swiss-Prot 命中 |
| `KEGG-Annotated` | 最佳命中的注释含候选 KO；序列命中另记 `KEGG_sequence_hit` |
| `KOG-Annotated` | 最佳命中的注释含 KOG 编号；序列命中另记 `KOG_sequence_hit` |
| `TrEMBL-Annotated` | 有通过过滤的 TrEMBL 命中 |
| `Interpro-Annotated` | 至少一个合法 IPR 编号，成员库签名命中不直接等于 IPR 注释 |
| `GO-Annotated` | 本次 InterProScan 输出至少一个 GO 编号 |
| `Any-Annotated` | 上述七类的并集，不能将七类数量相加 |

## 5. 第一步：100 条代表蛋白贯通测试

测试脚本位于 `${HOME}/Siganus_annotation/Siganus_qatar/test/scripts/`。

```bash
# 以下为初次测试时的启动方式；已完成的项目无须重新启动。
cd ${HOME}/Siganus_annotation/Siganus_qatar
if bash test/scripts/check.sh; then
    nohup bash test/scripts/run_all.sh > test/run_all.log 2>&1 &
fi
```

预检查会检查可执行程序、数据库、注释表及 InterProScan 参数。数据库目录出现多个候选时必须在配置中明确指定，不自动猜选或建库。

测试使用种子 `20260907` 从 26,467 条代表序列中选取 100 条，0–8 步全部完成。测试统计依次为：NR 88、Swiss-Prot 79、KEGG 75、KOG 66、TrEMBL 88、InterPro 89、GO 84，七类并集 90。

关键验收位置：

```text
${HOME}/Siganus_annotation/Siganus_qatar/test/0.Raw_Data/qc.json
${HOME}/Siganus_annotation/Siganus_qatar/test/8.Integration/annotation_statistics.tsv
${HOME}/Siganus_annotation/Siganus_qatar/test/8.Integration/validation.json
${HOME}/Siganus_annotation/Siganus_qatar/test/run_all.log
${HOME}/Siganus_annotation/Siganus_qatar/test/run_manifest.json
```

测试验证为 `PASS`，保留 KEGG 近最高分赋值冲突告警。小样本通过只证明该测试集成功贯通，不保证全量数据没有新的缺失参考条目。

## 6. 第二步：生成正式脚本并启动 0–8 步

测试通过后执行过的正式晋级与启动方式：

```bash
cd ${HOME}/Siganus_annotation/Siganus_qatar
bash test/scripts/promote.sh
nohup bash scripts/run_all.sh > full_annotation.log 2>&1 &
```

晋级程序校验真实测试状态和输出指纹后生成外层正式脚本，正式样本数改为 0，表示全量。已有同名脚本先备份。不要为新增绘图再次运行晋级，也不要用本地旧测试配置覆盖服务器已验证的正式配置。

所有下表脚本的完整前缀均为 `${HOME}/Siganus_annotation/Siganus_qatar/scripts/`；输出目录的完整前缀均为 `${HOME}/Siganus_annotation/Siganus_qatar/`。

| 顺序 | SH 脚本 | 输出目录 | 工作内容 |
|---:|---|---|---|
| 0 | `0.Raw_Data.sh` | `0.Raw_Data/` | 验证输入、最长代表蛋白、统一 query |
| 1 | `1.NR.sh` | `1.NR/` | NR 比对与描述 |
| 2 | `2.Swissprot.sh` | `2.Swissprot/` | Swiss-Prot 比对与描述 |
| 3 | `3.KEGG.sh` | `3.KEGG/` | KEGG 比对、候选 KO 与冲突检查 |
| 4 | `4.KOG.sh` | `4.KOG/` | KOG 编号、类别与冲突检查 |
| 5 | `5.TrEMBL.sh` | `5.TrEMBL/` | TrEMBL 比对与描述 |
| 6 | `6.Interpro.sh` | `6.Interpro/` | 结构域/家族成员签名、IPR、GO 证据 |
| 7 | `7.GO.sh` | `7.GO/` | GO 去重及蛋白/基因映射 |
| 8 | `8.Integration.sh` | `8.Integration/` | 总表、覆盖率、重叠组合和验证 |

`scripts/run_all.sh` 是 0–8 步总控，按依赖顺序串行运行，每个比对任务使用 32 线程。第 9 步独立启动，不会被这个旧总控自动执行。

## 7. 第三步：正式 KOG 中止与保守恢复

正式运行在 NR、Swiss-Prot、KEGG 完成后于 KOG 停止，错误为 25 个通过过滤的目标 ID 不在当前注释表中。

原始失败诊断目录的**确定路径**：

```text
${HOME}/Siganus_annotation/Siganus_qatar/4.KOG/.attempt-j3clqkt2/
```

其中 `raw_hits.tsv` 是已完成的原始比对，`unmapped_subjects.tsv` 保存缺失 ID。该目录应保留。

实际诊断发现：

- 缺失目标 25 个，影响至少一个候选的查询 33 个。
- 最佳命中缺失参考记录的查询 11 个。
- 原始数据库标题只有 ID，不能从标题补出 KOG 编号。
- 配套表 `${DB}/kog/20090331/kog_clean.fa.id` 中也没有这些 ID 的对应文本。

恢复程序的服务器位置：

```text
${HOME}/Siganus_annotation/Siganus_qatar/scripts/recover_kog_missing.py
${HOME}/Siganus_annotation/Siganus_qatar/scripts/kog_reviewed_diagnostic.json
```

当时使用的恢复命令如下，**已经成功完成，仅作为运行记录**：

```bash
cd ${HOME}/Siganus_annotation/Siganus_qatar
nohup python3 scripts/recover_kog_missing.py \
  --attempt 4.KOG/.attempt-j3clqkt2 \
  > kog_recovery.log 2>&1 &
```

恢复方式：验证配置、输入与前序结果指纹，复用 KOG 原始比对；缺失参考条目保留为空，标记 `best_hit_unmapped`，不改选低分命中、不编造编号、不修改共享数据库。恢复后自动继续 5–8 步，日志最终出现 `COMPLETE`。

关键恢复审计文件：

```text
${HOME}/Siganus_annotation/Siganus_qatar/4.KOG/unmapped_subjects.tsv
${HOME}/Siganus_annotation/Siganus_qatar/4.KOG/unresolved_queries.tsv
${HOME}/Siganus_annotation/Siganus_qatar/4.KOG/qc.json
${HOME}/Siganus_annotation/Siganus_qatar/4.KOG/recovery_provenance.json
${HOME}/Siganus_annotation/Siganus_qatar/4.KOG/recovery_implementation.py
${HOME}/Siganus_annotation/Siganus_qatar/4.KOG/state.json
${HOME}/Siganus_annotation/Siganus_qatar/kog_recovery.log
```

最终 KOG QC：

| 指标 | 数值 |
|---|---:|
| query 总数 | 26,467 |
| 原始有命中 query | 17,845 |
| 过滤后有命中 query | 15,854 |
| 原始命中行数 | 297,949 |
| 过滤后命中行数 | 173,221 |
| 缺失参考目标 ID | 25 |
| 有缺失候选的 query | 33 |
| 最佳命中缺失参考/描述的 query | 11 |
| 最佳命中含 KOG 编号的 query | 14,042 |
| 近最高分赋值冲突 query | 34 |

15,854 与 14,042 的差额为 1,812，不能全部解释为那 11 个缺失最佳命中。其余 1,801 个最佳命中未形成 KOG 编号赋值，可能包含仅有 LSE 等记录，具体应查 `best_hits.tsv`。缺少 KOG 编号不表示没有生物学功能。

## 8. 第四步：InterProScan、GO 和最终整合

正式 InterProScan 日志调用参数如下，临时目录后缀是当次运行标识：

```bash
${SHARED}/ann/interproscan-5.76-107.0/interproscan.sh \
  --input ${HOME}/Siganus_annotation/Siganus_qatar/0.Raw_Data/query.faa \
  --seqtype p --formats TSV \
  --outfile ${HOME}/Siganus_annotation/Siganus_qatar/6.Interpro/.attempt-m043jwev/interproscan.tsv \
  --cpu 32 --goterms --iprlookup \
  --tempdir ${HOME}/Siganus_annotation/Siganus_qatar/6.Interpro/.attempt-m043jwev/tmp \
  --disable-precalc
```

该命令为历史记录，不需要单独重跑。默认使用该安装启用的成员分析；帮助输出中已停用的 SignalP/Phobius/TMHMM 等不能写成实际运行的成员库。

| 服务器绝对路径 | 内容 |
|---|---|
| `${HOME}/Siganus_annotation/Siganus_qatar/6.Interpro/interproscan.tsv` | 正式发布的 InterProScan TSV 输出 |
| `${HOME}/Siganus_annotation/Siganus_qatar/6.Interpro/signatures.tsv` | 成员库签名、位置、IPR 编号与名称 |
| `${HOME}/Siganus_annotation/Siganus_qatar/6.Interpro/protein_interpro.tsv` | 蛋白到 IPR 的去重映射 |
| `${HOME}/Siganus_annotation/Siganus_qatar/6.Interpro/go_evidence.tsv` | GO 与成员库/签名来源证据 |
| `${HOME}/Siganus_annotation/Siganus_qatar/7.GO/protein2go.tsv` | 蛋白到 GO 映射 |
| `${HOME}/Siganus_annotation/Siganus_qatar/7.GO/gene2go.tsv` | 基因到 GO 映射 |
| `${HOME}/Siganus_annotation/Siganus_qatar/7.GO/annotations.tsv` | GO、蛋白/基因和来源汇总 |

本次 GO 注释来自 InterProScan `--goterms`，没有从 NR/TrEMBL 描述自由文本猜测 GO。第 7 步只做去重与对应；名称、方面和祖先分类在独立第 9 步完成。

## 9. 正式结果与验证结论

### 9.1 最重要的交付文件

| 服务器绝对路径 | 建议用途 |
|---|---|
| `${HOME}/Siganus_annotation/Siganus_qatar/8.Integration/functional_annotation.tsv` | **主结果表**；每条代表蛋白一行，包括未注释基因、标记、KO/KOG/IPR/GO 与比对证据 |
| `${HOME}/Siganus_annotation/Siganus_qatar/8.Integration/annotation_statistics.tsv` | 七类覆盖率及并集统计 |
| `${HOME}/Siganus_annotation/Siganus_qatar/8.Integration/annotation_overlap.tsv` | 七类成员关系组合及数量 |
| `${HOME}/Siganus_annotation/Siganus_qatar/8.Integration/validation.json` | 技术验证和告警 |
| `${HOME}/Siganus_annotation/Siganus_qatar/run_manifest.json` | 正式配置、输入 SHA256、程序指纹、软件/数据库信息 |

`1.NR/` 至 `5.TrEMBL/` 各目录的通用结果为：`raw_hits.tsv`（17 列无表头）、`raw_hit_columns.tsv`（列定义）、`filtered_hits.tsv`、`best_hits.tsv`、`unmapped_subjects.tsv`、`qc.json` 和 `state.json`。例如 KOG 最佳命中表位于 `${HOME}/Siganus_annotation/Siganus_qatar/4.KOG/best_hits.tsv`。

### 9.2 正式注释统计

统一分母：**26,467 个基因代表序列**。

| 类别 | 注释数 | 比例 |
|---|---:|---:|
| Nr-Annotated | 22,476 | 84.92% |
| Swissprot-Annotated | 19,280 | 72.85% |
| KEGG-Annotated | 19,282 | 72.85% |
| KOG-Annotated | 14,042 | 53.05% |
| TrEMBL-Annotated | 22,317 | 84.32% |
| Interpro-Annotated | 21,693 | 81.96% |
| GO-Annotated | 19,395 | 73.28% |
| Any-Annotated | **22,785** | **86.09%** |
| 七类均未注释 | 3,682 | 13.91% |
| KEGG_sequence_hit，辅助指标 | 19,282 | 72.85% |
| KOG_sequence_hit，辅助指标 | 15,854 | 59.90% |

### 9.3 验证与剩余告警

正式 `validation.json` 为 `PASS`，检查通过：保留全部 query，包括未注释 query；每个 query 一行；七类注释齐全；全部 query 进入分母；上游成功状态和输出 SHA256 一致。

保留三项告警：

1. KEGG：近最高分候选赋值冲突，具体功能结论前需复核。
2. KOG：部分最佳命中没有描述。
3. KOG：近最高分候选赋值冲突，具体功能结论前需复核。

`PASS` 表示流程与文件的技术一致性，不证明所有功能赋值正确。KEGG 是同源比对所得候选 KO，不是已经完成 KofamScan/KAAS 或实验验证；本项目未运行富集分析。

## 10. 第五步：独立第 9 步绘图

### 10.1 部署和启动

将 `Siganus_annotation_figures.zip` 上传至项目根目录并解压。新增脚本位置：

```text
${HOME}/Siganus_annotation/Siganus_qatar/scripts/9.Figures.sh
${HOME}/Siganus_annotation/Siganus_qatar/scripts/plot_annotation.py
${HOME}/Siganus_annotation/Siganus_qatar/scripts/requirements_figures.txt
```

```bash
cd ${HOME}/Siganus_annotation/Siganus_qatar
unzip Siganus_annotation_figures.zip

# 独立环境仅需创建一次；已有合适环境可直接激活。
conda create -n siganus_figures -c conda-forge \
  python=3.11 matplotlib numpy scipy -y
conda activate siganus_figures

nohup bash scripts/9.Figures.sh --fetch-mappings --tiff \
  > figures.log 2>&1 &
```

绘图只读取正式注释文件，不重跑 DIAMOND/InterProScan，也不修改 0–8 步状态。

### 10.2 输出图清单

全部图的服务器目录为：

```text
${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/
```

| 文件主名 | 图的内容 |
|---|---|
| `01_annotation_coverage` | 七类注释与并集覆盖率 |
| `02_annotation_venn5` | NR、Swiss-Prot、KEGG、KOG、InterPro 五集合 Venn，按照用户示例样式 |
| `03_annotation_upset7_p*` | 全部七类注释的非零互斥交集，分页展示 |
| `04_KOG_functional_categories*` | KOG 功能类别统计 |
| `05_GO_aspects` | GO 的 BP、CC、MF 三方面统计 |
| `06_GO_biological_process*` | Biological process 分类 |
| `06_GO_cellular_component*` | Cellular component 分类 |
| `06_GO_molecular_function*` | Molecular function 分类 |
| `07_KEGG_level1` | KEGG 一级功能分类 |
| `08_KEGG_level2*` | KEGG 二级功能分类 |
| `09_InterPro_top20` | 最常见前 20 个 InterPro 条目 |

图文件格式：PDF、SVG、300 dpi PNG；使用 `--tiff` 时另导出 600 dpi TIFF。类别多或名称长时分页，后缀为 `_p01` 等。

关键辅助文件：

```text
${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/source_data/
${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/source_data/venn5_exclusive_regions.tsv
${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/source_data/upset7_all_intersections.tsv
${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/source_data/KEGG_pathway_counts.tsv
${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/source_data/InterPro_all_entry_counts.tsv
${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/figure_captions.md
${HOME}/Siganus_annotation/Siganus_qatar/9.Figures/figure_audit.json
```

Venn 数字由逐基因集合计算，31 个区域为互斥交集，椭圆面积不表示基因数。五集合外的数量不等于七类均未注释的 3,682。七类全部交集由 UpSet 补充展示。

GO 分类使用各根节点的直接子项，沿 `is_a` 和 `part_of` 传播；不是 GO-slim，也不是在 GO DAG 中人为固定所有条目的统一深度。KEGG 分类使用候选 KO 对应的 `[PATH:ko...]` 通路分支。同一基因在同一类别只计一次，但可属于多个类别。KOG 分类只计有 KOG 编号的代表基因，不用序列命中数代替。各分类图均为描述统计，不是富集图。

### 10.3 GO 下载失败时

当前本地网络访问 GO 官方 OBO 返回 403；服务器网络未确认。若下载失败，已完成的其他图保留，审计状态为 `INCOMPLETE_CLASSIFICATIONS`，不能据此声称所有图已完成。

查找服务器已有文件：

```bash
find ${SHARED}/ann /mnt/Database/DNA_Database -maxdepth 8 -type f \
  \( -name 'go-basic.obo' -o -name 'go.obo' \) -print 2>/dev/null
```

找到后替换实际路径，仅重跑绘图：

```bash
bash scripts/9.Figures.sh \
  --go-obo /实际路径/go-basic.obo \
  --fetch-mappings --tiff > figures.log 2>&1
```

也可将完整本体放到默认 `9.Figures/mapping/go-basic.obo`。KEGG 可用 `--kegg-json /实际路径/ko00001.json` 指定。原 `animal.id.annot.xls` 或 `ko_map.tab` 不能直接作为该 JSON 参数输入。

## 11. 验收、故障定位与归档

### 11.1 常用只读查看命令

```bash
cd ${HOME}/Siganus_annotation/Siganus_qatar
cat 0.Raw_Data/qc.json
cat 8.Integration/annotation_statistics.tsv
cat 8.Integration/validation.json
cat 4.KOG/qc.json
tail -n 30 kog_recovery.log

# 第 9 步启动后检查
tail -n 30 figures.log
cat 9.Figures/figure_audit.json
```

注释完成的证据为 `8.Integration/validation.json` 的 `PASS` 以及成功状态/校验；绘图全部完成的证据为 `9.Figures/figure_audit.json` 的 `COMPLETE`，并实际检查图面和未映射记录。

### 11.2 本项目遇到的问题及处理

| 问题 | 实际处理 |
|---|---|
| 找不到 `interproscan.sh` | 在配置中指定明确安装版本的绝对路径 |
| Swiss-Prot 库找不到 | 使用实际 `swissport/diamond/` 目录 |
| KEGG/TrEMBL 有多个 `.dmnd` 候选 | 显式固定上文的动物/真核子集库及配套表 |
| InterProScan help 非零退出导致预检查中止 | 使用项目交付的预检查修复；不把所有非零退出一律忽略 |
| base Java 25 | 配置独立 Java 11，具体路径以服务器 `java_home` 为准 |
| 全量 KOG 出现 25 个未映射目标 | 专用恢复程序保留缺失标记，复用原比对并继续下游 |
| 绘图 GO 网络下载失败 | 使用完整本地 OBO；未完成时保留明确审计状态 |

完成状态存于各步的 `state.json`，不能仅凭目录或 TSV 存在判断成功。主脚本、配置、输入或数据库指纹变化可能触发重算，因此归档时应原样保留服务器实际运行版本，不用新的本地版本覆盖它。失败 `.attempt-*` 和恢复审计有追溯价值，不在本记录中安排删除。

### 11.3 建议保留的文件

完整复现应保留原始 FASTA/GFF、服务器实际 `scripts/` 与 `test/scripts/`、`run_manifest.json`、各步结果和状态、KOG 原失败目录与恢复证据、测试/正式日志，以及第 9 步资源及结果。共享大库记录其路径、管理员版本说明和可用 checksum；不必为整理报告重新复制整个共享数据库。

用于汇报和图件交接的轻量结果包可在全部绘图完成后生成：

```bash
cd ${HOME}/Siganus_annotation/Siganus_qatar
tar -czf Qatar_annotation_results_and_figures.tar.gz \
  scripts run_manifest.json \
  0.Raw_Data/query_manifest.tsv 0.Raw_Data/qc.json \
  8.Integration 9.Figures \
  4.KOG/qc.json 4.KOG/unmapped_subjects.tsv \
  4.KOG/unresolved_queries.tsv 4.KOG/recovery_provenance.json \
  full_annotation.log kog_recovery.log figures.log
```

该轻量包用于交接，不包含完整原始输入、所有比对或共享数据库，不能代替完整复现归档。

## 12. 可用于方法记录的简述

根据配套 GFF 将输入蛋白映射至基因，每个基因选择最长蛋白作为代表，得到 26,467 条代表序列。使用 DIAMOND blastp 将代表序列分别与 NR 动物子集、Swiss-Prot 真核子集、KEGG 动物子集、KOG 和 TrEMBL 真核子集比对，采用 very-sensitive 模式、E-value 1e-5、最多 25 个目标及每目标一个 HSP。按配置的查询覆盖度筛选后选取最佳命中，并记录近最高分 KO/KOG 冲突。使用 InterProScan 5.76-107.0 产生成员库签名、InterPro 和 GO 注释。对 KOG 参考表缺失条目保留未解析状态，不使用低分命中补充最佳命中的功能。最终以全部基因代表序列为分母统计七类注释及其并集，共 22,785 条代表序列获得至少一类注释，覆盖率为 86.09%。

上述文字描述已确认完成的注释部分。正式论文还应根据归档配置填写实际过滤值、DIAMOND 软件版本、各数据库 release/范围及成员分析范围；待第 9 步完成后，再依据分类资源版本记录补充绘图方法。不得将候选同源功能写成实验验证功能。
