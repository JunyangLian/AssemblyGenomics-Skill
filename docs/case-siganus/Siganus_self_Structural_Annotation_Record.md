# Siganus canaliculatus self 数据结构注释全流程记录

> 项目：Siganus canaliculatus 染色体级基因组注释，服务于植食性泛基因组研究。  
> 记录日期：2026-09-06。  
> 计算平台：Ubuntu，账户 `user`。  
> 服务器项目根目录：`${SHARED}/USER/Siganus_self`。  
> 记录依据：项目初始说明、实际服务器日志和本次逐步诊断输出。本文在本地整理，未直接登录服务器重新核验全部文件。

## 1. 当前结论与结果使用范围

本项目已完成重复序列建库与屏蔽、30 个 RNA-seq 样本比对、BRAKER3 ETP 基因预测、TSEBRA 参数对照、最长编码转录本筛选、GFF3 编码层级整理及蛋白 BUSCO 评估。

初始最长转录本蛋白集 BUSCO 为 **93.3%**。通过局部对照定位，主要完整度损失发生在 **TSEBRA 最终筛选阶段**：原配置 `intron_support 1.0` 对本数据过严。仅将其降低至 `0.8`，其余配置不变并继续启用单外显子过滤，重新合并已有 AUGUSTUS/GeneMark 预测；再保留最长编码转录本，最终得到 **23,924 个编码基因、23,924 条蛋白，BUSCO 97.4%**。

这次优化没有重新组装，也没有重跑 RepeatModeler2、RepeatMasker、RNA-seq mapping、GeneMark-ETP 或 AUGUSTUS 全基因组预测。改变的是已有预测的筛选与后处理。

| 项目 | 原最长转录本集 | 改进后的编码最长转录本集 |
|---|---:|---:|
| 蛋白条数 | 22,435 | 23,924 |
| 完整 BUSCO | 3396，93.3% | 3544，97.4% |
| 单拷贝完整 BUSCO | 3359 | 3510 |
| 重复完整 BUSCO | 37 | 34 |
| 碎片化 BUSCO | 37 | 29 |
| 缺失 BUSCO | 207 | 67 |
| 重复蛋白 ID | 0 | 0 |
| 空蛋白序列 | 0 | 0 |
| 含内部终止符的蛋白 | 0 | 0 |
| 含 X 的蛋白 | 0 | 0 |
| 蛋白长度中位数，aa | 395 | 418 |

净增加 148 个完整 BUSCO，按整数计算提高约 4.07 个百分点；最终蛋白数净增 1489，但不能把数量差直接解释成 1489 个已确认的新基因位点，需要模型匹配。

**状态边界：** 97.4% 的蛋白 BUSCO 与编码 GFF3/FASTA 一致性已验证。新增模型的 RNA/蛋白证据、假阳性风险及泛基因组跨样本一致性尚需检查。`intron_support=0.8` 是本次验证有效的候选参数，不是证明适用于所有物种的最优阈值。

## 2. 路径约定与目录结构

本文 Bash 命令中的路径变量统一定义如下；命令块是操作记录或复现模板，不是建议把全文从头执行一遍。

```bash
ROOT=${SHARED}/USER/Siganus_self
WORK="$ROOT/4.BRAKER3/run_ETP"
GENOME="$ROOT/4.BRAKER3/input/S_canaliculatus.softmasked.fa"
LINEAGE=${SHARED}/busco_downloads/lineages/actinopterygii_odb10
STAGES="$ROOT/5.QC/BUSCO_stages_20260906_080019"
DIAG="$ROOT/5.QC/TSEBRA_diagnosis_20260906_162323"
ALL="$DIAG/intron08"
CANDIDATE="$ROOT/5.QC/intron08_longest_20260906_170025"
VERIFIED="$CANDIDATE/coding_only_verified"
DELIVERY="$ROOT/6.Structural_Annotation"
```

下文路径表中以 `$ROOT` 等变量开头的路径，均按上面定义展开成服务器绝对路径。**数据库实际使用的是 `${SHARED}/busco_downloads/...`，不是项目根目录后来列出的 `busco_downloads/`，两者不能混淆。**

```text
${SHARED}/USER/Siganus_self/
├── 0.Raw_Data/                         # 目录存在；原始 genome 实际文件路径待补
├── 1.Repeat_Annotation/
│   ├── RepeatModeler2/
│   └── RepeatMasker_Final/
├── 2.RNAseq/
│   ├── hisat2_index/
│   ├── bam/
│   └── logs/
├── 3.Protein_Evidence/
├── 4.BRAKER3/
│   ├── input/
│   ├── run_ETP/
│   └── run_braker3_ETP.sh
├── 5.QC/
│   ├── BUSCO/                         # 原 braker.aa，93.4%
│   ├── BUSCO_longest/                 # 原最长转录本，93.3%
│   ├── BUSCO_genome/                  # Miniprot 组装评估，待修复复核
│   ├── BUSCO_stages_20260906_080019/
│   ├── TSEBRA_diagnosis_20260906_162323/
│   ├── intron08_longest_20260906_170025/
│   │   └── coding_only_verified/      # 验证后的编码 GFF3/蛋白/CDS
│   └── logs/
├── 6.Structural_Annotation/
│   ├── all_isoforms/                  # 计划链接 intron08 GTF/蛋白及 BUSCO
│   └── longest/                       # 用户已确认硬链接编码最长转录本结果
├── 7.Functional_Annotation/           # 目录存在；本记录不含功能注释执行结果
└── export_coding_gff3.py              # 本次编码层级检查与导出脚本
```

初始说明曾使用 `0.Raw_Data/genome/`；实际 `find` 返回该子目录不存在。后续已确认 `0.Raw_Data/` 本身存在。不能把说明中的 `genome.fa` 当成已核实的原始文件路径。

## 3. 软件、环境与依赖

| 工具/用途 | 环境或路径 | 已知版本/状态 |
|---|---|---|
| RepeatModeler2、RepeatMasker | Conda 环境 `repeat_annotation` | 确切版本待补 |
| FamDB | `$CONDA_PREFIX/share/famdb-3.0.0` | 当时使用的安装目录 |
| Dfam | FamDB 数据目录 | 4.0 |
| HISAT2、samtools | 原 mapping 环境未完整记录 | 确切版本待补 |
| BRAKER | `${SHARED}/env/braker3/bin/braker.pl` | 3.0.8 |
| AUGUSTUS | `${SHARED}/env/braker3/bin`；配置在同环境 `config/` | 确切版本待补 |
| GeneMark-ETP | BRAKER 调用 | 确切版本待补 |
| TSEBRA | `${SHARED}/env/braker3/bin/tsebra.py` | 版本/commit 待补 |
| TSEBRA 配置 | `${SHARED}/env/braker3/config/braker3.cfg` | 实际内容见第 8 节 |
| AGAT | `${SHARED}/miniconda3/envs/agat` | AGAT 版本待补；模块目录显示 Perl 5.26.2 |
| AGAT Perl | `${SHARED}/miniconda3/envs/agat/bin/perl` | 已验证可加载 `Bio::Tools::GFF` |
| BUSCO | `${SHARED}/env/braker3/bin/busco` | 6.1.0，蛋白模式成功完成 |
| HMMER | BUSCO 依赖摘要 | `hmmsearch: 3.1`，这是 BUSCO 报告值，未补核实际完整版本 |
| Miniprot | BUSCO 组装模式 | 0.18-r281，存在 BUSCO 字段解析兼容问题 |
| gffread | 由 `type -P gffread` 查得 | 实际绝对路径、版本尚未回传；成功提取过序列 |
| 系统 Python | `/usr/bin/python3` | traceback 显示 Python 3.10；成功完成导出 |
| BRAKER 环境 Python | `${SHARED}/env/braker3/bin/python` | 先前可用，后期最小测试也发生段错误，原因未解决 |

`${SHARED}/env/busco` 在项目初始说明中标为坏环境，本次 BUSCO 评估未使用它。

**环境使用经验：** 不能仅凭某工具曾在 `PATH` 中运行成功，就推断它在 `${SHARED}/env/braker3/bin/` 下。后期实际发现该目录下没有 `gffread`，应动态查找并记录。

## 4. 重复序列注释

### 4.1 RepeatModeler2 de novo 建库

```bash
conda activate repeat_annotation
which RepeatModeler
```

历史报告输出目录名：`RM_1727882.WedSep20733472026/`，包含：

- `consensi.fa`
- `consensi.fa.classified`

统计命令：

```bash
grep -c '^>' consensi.fa.classified
# 1200
```

结果为 **1200 个 repeat families**。本次未提供完整 BuildDatabase/RepeatModeler 命令、数据库前缀、线程参数及该 RM 目录的实际绝对位置，不能补写成已执行事实。最终重复序列库名为 `SCan_repeat_library.final.fa`，其构建/合并细节和绝对路径待补。

### 4.2 RepeatClassifier / Dfam 问题修复

历史错误：`Could not determine FamDB version`，处理为补齐 FamDB 数据。记录中的操作：

```bash
conda activate repeat_annotation
FAMDBPKG="$CONDA_PREFIX/share/famdb-3.0.0"
mkdir -p "$FAMDBPKG/Libraries/famdb"
python "$FAMDBPKG/utils/download_dfam.py" \
  -o "$FAMDBPKG/Libraries/famdb"
python "$FAMDBPKG/famdb.py" info
```

报告下载文件为 `dfam40.0.h5`、`dfam40.curated.consensus.0.h5`；`famdb.py info` 报告数据库 Dfam、版本 4.0。下载脚本和路径为当时环境记录，不保证其他安装布局相同。

### 4.3 RepeatMasker

初始说明中的简略命令为：

```bash
RepeatMasker -pa 48 -s \
  -lib SCan_repeat_library.final.fa \
  -dir RepeatMasker_Final genome.fa
```

该简略命令没有 `-xsmall`，所以排查之初怀疑误用硬屏蔽。实际文件统计随后排除了这个疑点：**传给 BRAKER 的文件有 11.98% 小写碱基，不是把这部分碱基替换为 N。** 历史完整命令或后续软屏蔽生成操作尚未提供，不能反推其一定包含 `-xsmall`。

若需要复现软屏蔽，下面是参数示意，不代表历史原命令：

```bash
# RAW_GENOME 和 REPEAT_LIBRARY 必须先指向经确认的实际输入文件。
RepeatMasker -pa 48 -s -xsmall \
  -lib "$REPEAT_LIBRARY" \
  -dir "$REPEAT_OUTPUT_NEW" "$RAW_GENOME"
```

| 参数 | 含义 |
|---|---|
| `-pa 48` | 设置 RepeatMasker 并行任务参数；实际进程/线程使用需按安装版本和搜索引擎理解 |
| `-s` | 敏感搜索模式，不是软屏蔽开关 |
| `-lib` | 自定义重复序列库 |
| `-xsmall` | 输出重复区域为小写碱基 |
| `-dir` | 结果输出目录 |

参数语义参考 [RepeatMasker 官方帮助](https://github.com/Dfam-consortium/RepeatMasker/blob/master/repeatmasker.help)。

实际核实的关键路径：

| 文件 | 用途 |
|---|---|
| `$ROOT/1.Repeat_Annotation/RepeatMasker_Final/S_canaliculatus.fa.masked` | RepeatMasker 屏蔽后基因组 |
| `$ROOT/4.BRAKER3/input/S_canaliculatus.softmasked.fa` | BRAKER 及后续提取使用的基因组 |
| `$ROOT/1.Repeat_Annotation/RepeatMasker_Final/S_canaliculatus.fa.tbl` | 初始说明中的统计文件，未逐行复核 |

两个 FASTA 分别统计均为：

```text
Total bases       512514567
Lowercase bases    61391355  (11.98%)
N bases               30000  (约 0.006%；两位小数显示 0.01%)
```

复核命令：

```bash
awk '
/^>/ {next}
{
  gsub(/[[:space:]]/, "")
  total += length($0)
  lower += gsub(/[acgt]/, "&")
  ns += gsub(/[Nn]/, "&")
}
END {
  if(total) printf "Total=%d Lowercase=%d (%.3f%%) N=%d (%.3f%%)\n",
    total, lower, 100*lower/total, ns, 100*ns/total
}' "$GENOME"
```

初始报告的类别占比：LTR 1.30%、LINE 1.44%、DNA 2.92%、RC 0.73%、Unknown 5.44%。这些类别不是完整 `.tbl` 的全部行，不要求其和精确等于总屏蔽比例。软屏蔽格式正确，也不等于重复序列边界或分类全部准确。

## 5. RNA-seq 比对与蛋白证据

### 5.1 HISAT2 索引和 30 个 BAM

历史 mapping 参数示例：

```bash
hisat2-build genome.fa SCan

hisat2 -p 48 \
  -x hisat2_index/SCan \
  -1 sample_R1.fq.gz -2 sample_R2.fq.gz \
  | samtools sort -o sample.sorted.bam

samtools index sample.sorted.bam
samtools quickcheck -v *.bam
```

这里 `genome.fa`、`sample_R1.fq.gz` 等为初始记录的示例名。实际 FASTQ 清单、样本组织/批次/链特异性、索引参考的校验值及完整批处理脚本尚未提供。

| 路径 | 内容 |
|---|---|
| `$ROOT/2.RNAseq/hisat2_index/` | `SCan.1.ht2` 至 `SCan.8.ht2`，按初始说明 |
| `$ROOT/2.RNAseq/bam/` | 30 个坐标排序 BAM 及 30 个 BAI |
| `$ROOT/2.RNAseq/logs/` | mapping 日志目录 |

HISAT2 `-p 48` 指定比对线程；`-x` 是索引前缀；`-1/-2` 指定配对 reads。排序参数未显式给 samtools 线程，不能把 HISAT2 的 `-p` 视作整条管道线程限制。初始报告 mapping rate 为 **74–93%**。`quickcheck` 的通过主要说明文件基本完整，不验证所有比对、剪接位点或基因覆盖质量。

### 5.2 蛋白证据

文件：`$ROOT/3.Protein_Evidence/Vertebrata.fa`。

```bash
grep -c '^>' "$ROOT/3.Protein_Evidence/Vertebrata.fa"
# 19393872
```

报告包含 **19,393,872 条蛋白**。具体下载来源 URL、数据库发布版本、下载日期、文件 SHA256 尚未提供；不能仅凭 `Vertebrata.fa` 文件名认定其来源或版本。该文件用于 BRAKER `--prot_seq`。

## 6. BRAKER3 ETP 初次预测

### 6.1 环境和输入

```bash
export PATH=${SHARED}/env/braker3/bin:$PATH
export AUGUSTUS_CONFIG_PATH=${SHARED}/env/braker3/config
export AUGUSTUS_BIN_PATH=${SHARED}/env/braker3/bin
export AUGUSTUS_SCRIPTS_PATH=${SHARED}/env/braker3/bin
braker.pl --version
# 3.0.8
```

输入为软屏蔽基因组、30 个 sorted BAM、`Vertebrata.fa`。`$BAMS` 应是实际 BAM 路径的逗号分隔列表，历史具体列表尚未收录。

### 6.2 核心命令和参数

脚本位置：`$ROOT/4.BRAKER3/run_braker3_ETP.sh`。

```bash
braker.pl \
  --species=Siganus_canaliculatus_self \
  --genome="$GENOME" \
  --bam="$BAMS" \
  --prot_seq="$ROOT/3.Protein_Evidence/Vertebrata.fa" \
  --softmasking --gff3 --threads=48 \
  --workingdir="$WORK" \
  --AUGUSTUS_ab_initio
```

| 参数 | 本项目用途 |
|---|---|
| `--species` | AUGUSTUS 训练参数集名称 |
| `--genome` | 输入基因组路径 |
| `--bam` + `--prot_seq` | 同时提供 RNA-seq 和蛋白证据，运行 ETP 流程 |
| `--softmasking` | 按小写标记使用重复区域；不会恢复硬屏蔽丢失的碱基 |
| `--gff3` | 输出 GFF3 |
| `--threads=48` | BRAKER 工作线程设置 |
| `--workingdir` | 工作目录 |
| `--AUGUSTUS_ab_initio` | 历史脚本中的额外 ab initio 输出选项；本次比较使用 hints 输出 |

历史后台启动方式：`nohup ./run_braker3_ETP.sh > logs/run_braker3_ETP.nohup.log 2>&1 &`。这个日志相对路径取决于当时启动目录，不能只凭该命令确定其绝对位置。

官方流程说明：[BRAKER 3.0.8 README](https://github.com/Gaius-Augustus/BRAKER/blob/v3.0.8/README.md)。

### 6.3 输出和实际后处理日志

| 路径 | 内容 |
|---|---|
| `$WORK/braker.log` | 主流程日志 |
| `$WORK/braker.gtf` | TSEBRA 合并、后处理后的最终 GTF |
| `$WORK/braker.gff3` | 原始最终 GFF3，22,435 个 gene |
| `$WORK/braker.aa` | 原始最终蛋白，32,427 条，含 isoforms |
| `$WORK/braker.cds` | 初始说明报告的 CDS 文件名；实际未再次列出确认 |
| `$WORK/Augustus/augustus.hints.gtf` | 后来定位到的 AUGUSTUS hints 模型 |
| `$WORK/Augustus/augustus.hints.aa` | 已评估的 AUGUSTUS 蛋白 |
| `$WORK/Augustus/augustus.ab_initio.gtf`、`.aa` | 额外 ab initio 输出，未在本次做 BUSCO 对照 |
| `$WORK/GeneMark-ETP/genemark.gtf` | 本次使用的 GeneMark 中间模型 |
| `$WORK/GeneMark-ETP/genemark_supported.gtf` | supported 子集，未替代本次 GeneMark 输入 |
| `$WORK/GeneMark-ETP/training.gtf` | TSEBRA 强制保留的训练模型 |
| `$WORK/hintsfile.gff` | TSEBRA 使用的外部证据 |
| `$WORK/genome.fa` | BRAKER 日志中实际用于提取的参考路径 |

`GeneMark-ETP/proteins.fa/` 下也发现同名 GTF；本次对照明确使用顶层 `GeneMark-ETP/genemark.gtf`，未任意替换为嵌套目录文件。

日志在 2026-09-05 记录：修正 AUGUSTUS in-frame stop 模型、调用 `getAnnoFastaFromJoingenes.py` 提取 AUGUSTUS 蛋白、TSEBRA 合并、重命名/最终输出、再次提取 `braker.aa`、GTF 转 GFF3。空 stderr 后来由 BRAKER 清理，不应把相应日志不存在等同于曾有报错。日志时间与 `ls` 时间显示有差异，未校准时区，不据此推断文件异常。

历史 TSEBRA 输入写在根目录 `run_ETP/augustus.hints.gtf`；之后实际存在的是 `run_ETP/Augustus/augustus.hints.gtf`。使用现存子目录文件重合并后复现原 BUSCO 汇总，支持其可用于此次对照，但不能用汇总相同代替全部文件内容相同。

已回传的 GTF SHA256：

```text
45f2b65e0ac9987d7023788d8445ac8f178e229d20a87db0ad95522e4043ec6e  Augustus/augustus.hints.gtf
b737c8b8dc10d41ac85d4f344e58aae2bb0ea6b445eb52b6a144ea244ba26c85  braker.gtf
```

## 7. 原始最长转录本与 BUSCO 基线

### 7.1 AGAT 初次去冗余

历史命令：

```bash
agat_sp_keep_longest_isoform.pl \
  -gff "$WORK/braker.gff3" \
  -o "$ROOT/5.QC/Siganus.longest.gff3"

gffread "$ROOT/5.QC/Siganus.longest.gff3" \
  -g "$GENOME" \
  -y "$ROOT/5.QC/Siganus.longest.pep.fa" \
  -x "$ROOT/5.QC/Siganus.longest.cds.fa"
```

初始提取记录中的参考写作 `genome.fa`；上面按后续已验证可用的 `$GENOME` 展示复现路径。初次 AGAT 报告删除 9992 个 isoforms，`32427 - 9992 = 22435`。

AGAT 的最长规则对有 CDS 的位点优先保留最长 CDS 转录本；不只是按 mRNA 首尾跨度选择。[AGAT 官方工具说明](https://agat.readthedocs.io/en/latest/tools/agat_sp_keep_longest_isoform.html)

### 7.2 BUSCO 版本、数据集和原始结果

```text
BUSCO: 6.1.0
Mode: proteins
Lineage: actinopterygii_odb10
Dataset creation date: 2024-01-08
Reference genomes: 26
BUSCO groups: 3640
```

统一命令结构：

```bash
export PATH=${SHARED}/env/braker3/bin:$PATH
${SHARED}/env/braker3/bin/busco \
  -i "$PROTEIN_FASTA" -l "$LINEAGE" -m proteins \
  --offline -c 48 -o "$RUN_NAME" --out_path "$OUTPUT_PARENT"
```

历史原最长转录本运行使用 `-c 64`、`-f`，输出路径如下；后续对照采用 `-c 48`、`--offline` 和新目录，不覆盖旧结果。`-f` 会强制覆盖，不应用于保留结果的复现对照。`PATH` 必须能找到 `hmmsearch`。[BUSCO 文档](https://busco.ezlab.org/busco_userguide)

| 输入 | 结果目录 | C/S/D/F/M 整数 |
|---|---|---|
| `braker.aa` | `$ROOT/5.QC/BUSCO/Siganus_canaliculatus_BUSCO/` | 3398 / 2514 / 884 / 37 / 205 |
| 原 `Siganus.longest.pep.fa` | `$ROOT/5.QC/BUSCO_longest/Siganus_longest_BUSCO/` | 3396 / 3359 / 37 / 37 / 207 |

这里 C=S+D；表中 S、D 已包含在 C 中，不能再次相加计算总数。

各 BUSCO 目录中：

- `short_summary.specific.actinopterygii_odb10.<运行名>.txt`：版本、模式和结果摘要。
- `run_actinopterygii_odb10/full_table.tsv`：逐 BUSCO ID 的状态和命中明细。
- `run_actinopterygii_odb10/busco_sequences/`：BUSCO 导出序列。

按 BUSCO ID 比较发现，原 AGAT 去冗余/提取后只有两个完整 BUSCO 丢失：`71390at7898`、`78658at7898`，均从 Duplicated 变为 Missing；没有新增完整 BUSCO。主要缺口早于 AGAT。

## 8. 从 93.3% 定位到 TSEBRA 阈值问题

### 8.1 基因组层面的对照与独立软件问题

曾使用同一软屏蔽基因组运行：

```bash
${SHARED}/env/braker3/bin/busco \
  -i "$GENOME" -l "$LINEAGE" -m genome \
  --miniprot --offline -c 48 \
  -o Siganus_genome_BUSCO_20260906_074252 \
  --out_path "$ROOT/5.QC/BUSCO_genome"
```

结果目录：`$ROOT/5.QC/BUSCO_genome/Siganus_genome_BUSCO_20260906_074252/`。

原始摘要为 `C:99.8%[S:99.3%,D:0.4%],F:0.0%,M:0.2%,n:3640,E:6.9%`：3631 个 Complete，9 个 Missing，并报告 252 个完整 BUSCO 含内部终止密码子。组装统计为 37 scaffolds、97 contigs、总长 512,514,567 bp、scaffold N50 22 Mbp、contig N50 20 Mbp、gap 0.006%。N50 是程序摘要显示的舍入值。

但是，实际服务器源码和 PAF 字段核对发现：

```python
# 安装的 BUSCO miniprot.py 中的错误读取方式
stop_codon_count = int(fields[17].strip().split(":")[2])
```

```text
PAF_index=12 AS:i:563
PAF_index=13 ms:i:593
PAF_index=14 np:i:159
PAF_index=15 fs:i:0
PAF_index=16 st:i:0
PAF_index=17 da:i:0
PAF_index=18 do:i:87
```

BUSCO 按固定索引把 `da:i`（起始密码子距离）误当成 `st:i`（终止密码子计数）。**E:6.9% 和 252 不能作为真实内部终止统计。组装 C/S/D 也应在修复后复核，因为标记可能影响命中选择。** 此问题已定位但尚未完成隔离修复和复跑，不能写成已解决。

FASTA 检查实际找到 63 个完整 BUSCO 的导出蛋白含内部 `*`；这个口径不同，不能直接替换 E。组装 Complete、原版最长转录本蛋白集（93.3%）不完整的候选共有 238 个：201 个 Missing、37 个 Fragmented。这里比较对象不是含所有 isoforms 的 `braker.aa`。其中 16 个候选的导出拷贝均检出内部 `*`，222 个未检测到内部 `*`。这些记录来自尚待复核的 genome-mode 输出，只作定位线索，不是直接补基因清单。

后续所有关键阈值比较均使用 **proteins 模式**，不经过 Miniprot，因此不受该字段错误直接影响。

### 8.2 分别评估 AUGUSTUS 与 GeneMark

运行目录：`$STAGES`。

```bash
gffread "$WORK/GeneMark-ETP/genemark.gtf" \
  -g "$GENOME" -y "$STAGES/GeneMark.pep.fa"

# 对下面两套蛋白分别使用第 7 节 BUSCO proteins 命令，-c 48。
# AUGUSTUS 输入：$WORK/Augustus/augustus.hints.aa
# GeneMark 输入：$STAGES/GeneMark.pep.fa
# 输出目录分别为：$STAGES/Augustus/ 和 $STAGES/GeneMark/
```

| 集合 | C | S | D | F | M | C% |
|---|---:|---:|---:|---:|---:|---:|
| AUGUSTUS hints | 3554 | 3131 | 423 | 41 | 45 | 97.6 |
| GeneMark | 3555 | 2909 | 646 | 31 | 54 | 97.7 |
| 原 BRAKER | 3398 | 2514 | 884 | 37 | 205 | 93.4 |

逐 ID 集合对照：

| 对照 | BUSCO 数量 |
|---|---:|
| AUGUSTUS 完整、BRAKER 不完整 | 178 |
| GeneMark 完整、BRAKER 不完整 | 184 |
| 两个中间集均完整、BRAKER 不完整 | 156 |
| 至少一个中间集完整、BRAKER 不完整 | 206 |
| BRAKER 完整、两个中间集均不完整 | 0 |
| AUGUSTUS/GeneMark 完整 BUSCO ID 并集 | 3604 |

3604/3640 约 99.0% 是 **BUSCO ID 并集覆盖率**，不是已生成的合格合并注释完整度；不能简单拼接两个蛋白集作为最终模型。

### 8.3 实际 TSEBRA 配置和调用

原配置 `${SHARED}/env/braker3/config/braker3.cfg`：

```text
P 1
E 20
C 1
M 1
intron_support 1.0
stasto_support 2
e_1 0.1
e_2 0.5
e_3 0.05
e_4 0.2
```

原日志命令的关键参数：

```bash
${SHARED}/env/braker3/bin/tsebra.py \
  --gtf "$WORK/augustus.hints.gtf,$WORK/GeneMark-ETP/genemark.gtf" \
  --keep_gtf "$WORK/GeneMark-ETP/training.gtf" \
  --hintfiles "$WORK/hintsfile.gff" \
  --filter_single_exon_genes \
  --cfg ${SHARED}/env/braker3/config/braker3.cfg \
  --out "$WORK/braker.gtf" -q
```

| 项目 | 解释 |
|---|---|
| `intron_support 1.0` | 普通模型需达到完全内含子证据支持，才能从该支持门槛通过 |
| `stasto_support 2` | 起止支持比例通常在 0–1，该值使这一路不能单独通过门槛；是官方配置值，不是本次认定的笔误 |
| `P/E/C/M` | hints 来源权重，E 为 RNA-seq；这里保持原值 |
| `e_1`–`e_4` | 重叠模型比较阈值，这里未调整 |
| `--keep_gtf` | 训练模型强制保留机制 |
| `--filter_single_exon_genes` | 过滤没有起始/终止 hint 支持的单外显子模型，不是删除所有单外显子基因 |
| `--score_tab` | 本次重跑额外输出模型证据评分，便于后续审查 |

因此不能把规则简化成“任何低于阈值的模型都被删”，还存在强制保留和模型比较。配置含义参考 [TSEBRA 文档](https://github.com/Gaius-Augustus/TSEBRA) 和 [官方 braker3.cfg](https://github.com/Gaius-Augustus/TSEBRA/blob/main/config/braker3.cfg)。

### 8.4 四组局部对照

实际运行目录：`$DIAG`。保存 `original.cfg` 及 `intron08.cfg`，未修改安装环境中的全局配置。

```bash
cp ${SHARED}/env/braker3/config/braker3.cfg "$DIAG/original.cfg"
awk '$1=="intron_support" {$2="0.8"} {print}' \
  "$DIAG/original.cfg" > "$DIAG/intron08.cfg"
```

| 组别 | 唯一变化 | C | S | D | F | M | C% |
|---|---|---:|---:|---:|---:|---:|---:|
| `original_extract` | 不重合并，从已有 braker.gtf 重新提取 | 3398 | 2514 | 884 | 37 | 205 | 93.4 |
| `baseline` | 原配置重新合并 | 3398 | 2514 | 884 | 37 | 205 | 93.4 |
| `intron08` | 仅将 intron_support 改成 0.8 | 3548 | 2485 | 1063 | 29 | 63 | 97.5 |
| `no_single_filter` | 原配置，仅去掉单外显子过滤 | 3401 | 2517 | 884 | 38 | 201 | 93.4 |

原 GTF 重新提取和原配置重合并均复现初始汇总；降低内含子阈值净增 **150 个 Complete**，约 4.12 个百分点；单独关闭单外显子过滤仅净增 3 个 Complete。结论是内含子阈值为主要因素，继续保留单外显子过滤。

`original_extract` 和 `baseline` 的整数汇总一致，但本记录没有将其夸大为逐序列或逐 BUSCO ID 完全一致。`intron08` 的净增 150 也不是已核对“恢复 150、丢失 0”的逐 ID 结论。

本次采用的 `intron08` 重合并核心命令：

```bash
${SHARED}/env/braker3/bin/tsebra.py \
  --gtf "$WORK/Augustus/augustus.hints.gtf,$WORK/GeneMark-ETP/genemark.gtf" \
  --keep_gtf "$WORK/GeneMark-ETP/training.gtf" \
  --hintfiles "$WORK/hintsfile.gff" \
  --cfg "$DIAG/intron08.cfg" \
  --filter_single_exon_genes \
  --score_tab "$ALL/scores.tsv" \
  --out "$ALL/models.gtf" \
  > "$ALL/tsebra.stdout.log" 2> "$ALL/tsebra.stderr.log"

gffread "$ALL/models.gtf" -g "$GENOME" -y "$ALL/proteins.fa" \
  > "$ALL/gffread.stdout.log" 2> "$ALL/gffread.stderr.log"

${SHARED}/env/braker3/bin/busco \
  -i "$ALL/proteins.fa" -l "$LINEAGE" -m proteins \
  --offline -c 48 -o BUSCO --out_path "$ALL" \
  > "$ALL/busco.log" 2>&1
```

上述输出路径已经存在，作为历史关键命令记录，不要不加区分直接覆盖运行。

## 9. intron08 最长编码转录本与质量验证

### 9.1 AGAT 环境冲突及解决

初次尝试 `conda run -p ${SHARED}/miniconda3/envs/agat ...` 失败：

```text
Can't locate Bio/Tools/GFF.pm in @INC
@INC 指向 ${SHARED}/env/braker3/lib/perl5/...
```

脚本被找到，但 Perl/模块路径混入 BRAKER 环境。locale 警告不是致命原因。成功方式是显式调用 AGAT 的 Perl，并清除继承的 Perl 环境变量：

```bash
AGAT=${SHARED}/miniconda3/envs/agat
agat_perl() {
  env -u PERL5LIB -u PERLLIB -u PERL5OPT \
    -u PERL_LOCAL_LIB_ROOT -u PERL_MB_OPT -u PERL_MM_OPT \
    LC_ALL=C LANG=C PATH="$AGAT/bin:$PATH" \
    "$AGAT/bin/perl" "$@"
}

agat_perl -MBio::Tools::GFF \
  -e 'print "$^X\n", $INC{"Bio/Tools/GFF.pm"}, "\n";'
# ${SHARED}/miniconda3/envs/agat/bin/perl
# ${SHARED}/miniconda3/envs/agat/lib/site_perl/5.26.2/Bio/Tools/GFF.pm

PREFIX="$CANDIDATE/Siganus.intron08.longest"
agat_perl "$AGAT/bin/agat_sp_keep_longest_isoform.pl" \
  -gff "$ALL/models.gtf" -o "$PREFIX.gff3" \
  > "$CANDIDATE/agat.resume.log" 2>&1

gffread "$PREFIX.gff3" -g "$GENOME" \
  -y "$PREFIX.pep.fa" -x "$PREFIX.cds.fa" \
  > "$CANDIDATE/gffread.stdout.log" \
  2> "$CANDIDATE/gffread.stderr.log"
```

成功后蛋白数为 23,924，内部 `*`、X、空序列和重复 ID 均为 0。内部终止统计使用 `"*" in sequence[:-1]`，排除常规末尾终止符；它不是对基因组移码、错误剪接或假阳性的全面验证。

### 9.2 最长转录本 BUSCO

```bash
${SHARED}/env/braker3/bin/busco \
  -i "$CANDIDATE/Siganus.intron08.longest.pep.fa" \
  -l "$LINEAGE" -m proteins --offline -c 48 \
  -o BUSCO --out_path "$CANDIDATE" \
  > "$CANDIDATE/busco.log" 2>&1
```

实际结果：

```text
C:97.4%[S:96.4%,D:0.9%],F:0.8%,M:1.8%,n:3640
Complete                 3544
Single-copy              3510
Duplicated                 34
Fragmented                 29
Missing                    67
```

各百分比分别四舍五入，S%+D% 可能与显示的 C% 差 0.1，不是计数错误。从 all_isoforms 的 3548 到最长集 3544 为净减少 4 个 Complete，具体新增丢失 ID 尚未在记录中列出。

## 10. GFF3 额外层级的诊断与编码子集导出

### 10.1 发现的问题

虽然只提取出 23,924 条蛋白，AGAT 输出却有 47,848 条 `gene`。进一步检查确认不是重复 ID，也不是缺少 Parent：

| Feature | 原候选 GFF3 记录数 |
|---|---:|
| gene | 47,848 |
| mRNA | 23,924 |
| transcript | 28,596 |
| exon | 243,169 |
| CDS | 243,169 |
| intron | 219,245 |
| start_codon | 23,913 |
| stop_codon | 23,915 |

47,848 个 gene ID 均唯一；全部 mRNA/transcript 的 Parent 均存在。最终筛查发现被排除的 28,596 个转录本 **既无 CDS，也无 exon**，所以单看“gene 有直接子节点”不能发现这些无编码内容的分支。其具体产生机制未追溯到 AGAT/TSEBRA 的哪一行代码，不把它写成某软件已证实的缺陷。

### 10.2 自定义导出脚本

服务器脚本：`$ROOT/export_coding_gff3.py`，最终成功版本标记 `streaming-v2`。

本地维护副本：

- `D:/1_yanjiusheng/Siganus_self/annotation_qc/export_coding_gff3.py`
- `D:/1_yanjiusheng/Siganus_self/annotation_qc/test_export_coding_gff3.py`

脚本按 `ID/Parent` 解析，保留 CDS 关联转录本、其 gene 以及相关 exon/CDS/intron/start/stop 记录；共享子特征只移除已排除的 Parent 引用。它不会按行号或名称前缀任意去重，不重写保留的基因组坐标、phase 或 ID。

验证包括：一个编码基因一个编码转录本、父子关系闭合、源蛋白和 CDS ID 与编码转录本一致、重新提取后的每条蛋白/CDS 长度及 SHA256 完全一致。序列比较忽略 FASTA 换行/描述差异，但不放宽碱基/氨基酸大小写或末尾终止符差异。只有全部通过，才把临时目录改名为 `coding_only_verified/`；失败临时目录留作检查，源文件不覆盖。

这属于编码子集导出，并非通用的完整 GFF3 规范验证器。排除无 CDS 的记录不意味着证明其为真实非编码基因。规范依据：[Sequence Ontology GFF3 规范](https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md)。

### 10.3 运行故障和最终成功命令

遇到并处理的故障：

1. `${SHARED}/env/braker3/bin/python` 报 `Segmentation fault`，连 `-I -X faulthandler -c 'import sys; ...'` 最小测试也失败。转用系统 Python 后完成任务。原环境段错误原因仍未确定，不能直接归因于内存不足。
2. 原脚本整表驻留内存，不适合大量 GFF3 记录；更新为逐行读写和阶段日志，本地 9 项测试通过。这个改善本身不等于已证明段错误根因。
3. 硬编码 `${SHARED}/env/braker3/bin/gffread` 触发 `FileNotFoundError`。改用 `type -P gffread` 查实际可执行文件后成功。实际路径没有在回传日志中保存，需要补录。

成功运行方式：

```bash
cd "$ROOT"
export PATH=${SHARED}/env/braker3/bin:$PATH
GFFREAD=$(type -P gffread)

/usr/bin/python3 -I -u -X faulthandler \
  "$ROOT/export_coding_gff3.py" \
  --candidate "$CANDIDATE" \
  --genome "$GENOME" \
  --gffread "$GFFREAD"
```

`-I` 使用 Python 隔离模式，`-u` 即时刷新日志，`-X faulthandler` 辅助定位解释器崩溃。此脚本只依赖 Python 标准库及外部 gffread，不要求系统 Python 安装 Biopython。

最终成功日志：`$CANDIDATE/export_coding_20260906_175348.log`。

```text
Source gene records: 47848
Coding genes: 23924
Coding transcripts: 23924
Excluded genes without coding transcripts: 23924
Excluded transcripts without CDS: 28596
Excluded transcripts with exons: 0
Protein IDs and sequences: UNCHANGED
CDS IDs and sequences: UNCHANGED
VERIFIED OUTPUT: .../coding_only_verified
```

**由于蛋白 ID 和序列完全不变，清理后的编码蛋白集沿用第 9 节 BUSCO 97.4%，无需为这次结构整理重复评估。** gene/transcript 层级冗余与蛋白 BUSCO 的 D 是不同概念，不能混为一谈。

## 11. 关键成果文件与 BUSCO 对应表

### 11.1 all_isoforms：降低阈值后、最长筛选前

| 文件 | 已确认的来源路径 |
|---|---|
| 所有保留转录本的模型 | `$ALL/models.gtf` |
| 对应蛋白 | `$ALL/proteins.fa` |
| 模型证据评分 | `$ALL/scores.tsv` |
| 实际降低阈值配置 | `$DIAG/intron08.cfg` |
| BUSCO 目录，97.5% | `$ALL/BUSCO/` |
| BUSCO 摘要 | `$ALL/BUSCO/short_summary.specific.actinopterygii_odb10.BUSCO.txt` |
| BUSCO 明细 | `$ALL/BUSCO/run_actinopterygii_odb10/full_table.tsv` |
| 重合并日志 | `$ALL/tsebra.stdout.log`、`$ALL/tsebra.stderr.log` |

本次 all_isoforms 流程只生成了 GTF 和蛋白，**未记录对应 CDS 或 GFF3 的生成**。不要把 GTF 改扩展名伪装成 GFF3，不要用 longest CDS 充当 all_isoforms CDS。all_isoforms 总蛋白数本记录未获得最终确切计数，不从 AGAT 的临时修复计数推算。

### 11.2 longest：已经验证的编码最长转录本集

| 文件 | 来源路径 |
|---|---|
| GFF3 | `$VERIFIED/Siganus.intron08.longest.gff3` |
| 蛋白 | `$VERIFIED/Siganus.intron08.longest.pep.fa` |
| CDS | `$VERIFIED/Siganus.intron08.longest.cds.fa` |
| 验证报告 | `$VERIFIED/validation.json` |
| 导出提取日志 | `$VERIFIED/gffread.log`，用户列出为 0 bytes |
| BUSCO 目录，97.4% | `$CANDIDATE/BUSCO/` |
| BUSCO 摘要 | `$CANDIDATE/BUSCO/short_summary.specific.actinopterygii_odb10.BUSCO.txt` |
| BUSCO 明细 | `$CANDIDATE/BUSCO/run_actinopterygii_odb10/full_table.tsv` |
| AGAT 成功日志 | `$CANDIDATE/agat.resume.log` |
| 蛋白质量对照 | `$CANDIDATE/protein_qc.txt` |
| AGAT/提取/BUSCO 总日志 | `$CANDIDATE/pipeline.resume.log` |

完整交付源目录为：

```text
${SHARED}/USER/Siganus_self/5.QC/intron08_longest_20260906_170025/coding_only_verified/
```

### 11.3 6.Structural_Annotation 归档

用户已回传并确认以下 longest 文件在归档目录存在，`ls -l` 显示硬链接数为 2：

```text
6.Structural_Annotation/longest/
├── Siganus.intron08.longest.gff3
├── Siganus.intron08.longest.pep.fa
├── Siganus.intron08.longest.cds.fa
├── validation.json
└── gffread.log
```

随后提出并提供了以下链接方案，但截至本记录写作，**尚未收到这些新增链接的执行验证输出**：

| 计划归档目标 | 对应源 |
|---|---|
| `$DELIVERY/all_isoforms/Siganus.intron08.all_isoforms.gtf` | `$ALL/models.gtf` |
| `$DELIVERY/all_isoforms/Siganus.intron08.all_isoforms.pep.fa` | `$ALL/proteins.fa` |
| `$DELIVERY/all_isoforms/BUSCO` | `$ALL/BUSCO` |
| `$DELIVERY/longest/BUSCO` | `$CANDIDATE/BUSCO` |

关键链接命令，需先定义第 2 节变量：

```bash
mkdir -p "$DELIVERY/all_isoforms" "$DELIVERY/longest"

link_safe() {
  test -e "$1" || { printf 'Source missing: %s\n' "$1"; return 1; }
  if [ -e "$2" ] || [ -L "$2" ]; then
    test "$1" -ef "$2" || {
      printf 'Destination differs; refusing overwrite: %s\n' "$2"
      return 1
    }
  else
    ln -sT -- "$1" "$2"
  fi
}

link_safe "$ALL/models.gtf" "$DELIVERY/all_isoforms/Siganus.intron08.all_isoforms.gtf"
link_safe "$ALL/proteins.fa" "$DELIVERY/all_isoforms/Siganus.intron08.all_isoforms.pep.fa"
link_safe "$ALL/BUSCO" "$DELIVERY/all_isoforms/BUSCO"
link_safe "$CANDIDATE/BUSCO" "$DELIVERY/longest/BUSCO"
```

软链接不复制文件；源目录改名或删除会影响访问。已有 longest 硬链接共享同一 inode，原位编辑任一硬链接会影响同一份内容，应把归档产物视为只读。BUSCO 目录使用软链接，不对目录做硬链接。

## 12. 结果复核、后续工作与待补信息

### 12.1 最简复核命令

```bash
# 使用编码清理后的文件；gene 数期望 23924。
awk -F '\t' '$0 !~ /^#/ && $3=="gene"{n++} END{print n+0}' \
  "$VERIFIED/Siganus.intron08.longest.gff3"
grep -c '^>' "$VERIFIED/Siganus.intron08.longest.pep.fa"
grep -c '^>' "$VERIFIED/Siganus.intron08.longest.cds.fa"
cat "$VERIFIED/validation.json"

# 两份摘要必须分别对应 all_isoforms 与 longest，不能混用。
cat "$ALL/BUSCO/short_summary.specific.actinopterygii_odb10.BUSCO.txt"
cat "$CANDIDATE/BUSCO/short_summary.specific.actinopterygii_odb10.BUSCO.txt"

# 已有摘要/配置只读检查。
cat "$DIAG/intron08.cfg"
type -P gffread
gffread --version
```

建议补做并保存最终交付文件 SHA256 清单；当前尚未回传该清单，不能把它写成已完成验证。相同序列指纹已由 `validation.json` 相关验证过程检查，不代表全部 GFF3 文件已有完整规范认证。

### 12.2 未完成事项

- 原始未屏蔽基因组真实路径、FASTA 校验值和组装版本；HISAT2 索引与 BRAKER 输入的参考一致性元数据。
- RepeatModeler2 完整命令、最终重复库整合步骤、原始 RepeatMasker 全命令、确切软件版本。
- 30 个 RNA-seq 样本表、组织信息、测序/链特异性、FASTQ 路径及 mapping 日志汇总。
- `Vertebrata.fa` 下载来源、数据库版本和校验值。
- AUGUSTUS、GeneMark、TSEBRA、AGAT、gffread 完整版本及 gffread 实际可执行路径。
- 新增/改变模型的 RNA 与蛋白支持、模型冲突、单外显子/多外显子分布、TE 相关假阳性和部分模型检查。蛋白无内部终止不等于所有模型结构正确。
- intron08 最长筛选前后净减少 4 个 Complete 的逐 ID 检查；原最长集与候选最长集的逐位点模型对应。
- BUSCO–Miniprot 固定列误读在独立副本中的修复与 genome-mode 复评。拟采用按 PAF 标签名 `st` 解析的方式，尚未实际修复完成；保留原报告，不悄悄覆盖。
- BRAKER 环境 Python 段错误的根因诊断；导出成功使用系统 Python不代表原环境恢复正常。
- `all_isoforms` 和两套 BUSCO 归档软链接的实际验证；若需要 all_isoforms CDS/GFF3，应单独生成并核验。

这些事项不会推翻本次 proteins 模式受控对照中“降低 TSEBRA 内含子支持阈值显著提高完整度”的结果，但决定这套候选注释能否作为泛基因组比较的稳定输入。

## 13. 可用于方法描述的事实性草稿

使用 RepeatModeler2 构建 de novo 重复序列库，并通过 RepeatMasker 获得软屏蔽基因组；屏蔽区域为 61,391,355 bp，占 512,514,567 bp 组装的 11.98%。将 30 个 RNA-seq 样本通过 HISAT2 比对至参考基因组，生成排序、索引的 BAM 文件。使用 BRAKER 3.0.8 的 ETP 流程，结合 RNA-seq 和 Vertebrata 蛋白证据，获得 GeneMark-ETP 与 AUGUSTUS 基因模型。针对默认合并结果的完整度损失，采用单因素对照评估 TSEBRA 筛选参数，并将内含子支持阈值由 1.0 调整至 0.8，同时保留原单外显子过滤及其他配置。随后使用 AGAT 保留每个编码位点的最长 CDS 转录本，使用 gffread 提取 CDS 和蛋白。按 CDS 关联关系导出编码 GFF3 子集，验证导出前后蛋白与 CDS 的 ID 和序列完全一致。最终获得 23,924 个编码基因；BUSCO 6.1.0、actinopterygii_odb10（2024-01-08，3640 组）蛋白模式评估为 C:97.4%[S:96.4%,D:0.9%],F:0.8%,M:1.8%。

该段落尚需补齐未记录的版本、数据库来源和方法细节后用于投稿；本项目未证明 0.8 为全局最优参数，也未把 genome-mode 原始 99.8% 作为修复后的正式结论。

## 14. 参考文档

- [BRAKER 3.0.8 官方说明](https://github.com/Gaius-Augustus/BRAKER/blob/v3.0.8/README.md)
- [TSEBRA 官方说明](https://github.com/Gaius-Augustus/TSEBRA)
- [TSEBRA braker3.cfg](https://github.com/Gaius-Augustus/TSEBRA/blob/main/config/braker3.cfg)
- [TSEBRA 模型筛选实现](https://github.com/Gaius-Augustus/TSEBRA/blob/main/bin/overlap_graph.py)
- [BUSCO 官方用户指南](https://busco.ezlab.org/busco_userguide)
- [BUSCO 6.1.0 Miniprot 解析代码](https://gitlab.com/ezlab/busco/-/blob/6.1.0/src/busco/busco_tools/miniprot.py)
- [Miniprot 0.18 输出实现](https://github.com/lh3/miniprot/blob/v0.18/format.c)
- [RepeatMasker 官方帮助](https://github.com/Dfam-consortium/RepeatMasker/blob/master/repeatmasker.help)
- [AGAT 最长转录本工具](https://agat.readthedocs.io/en/latest/tools/agat_sp_keep_longest_isoform.html)
- [GFF3 格式规范](https://github.com/The-Sequence-Ontology/Specifications/blob/master/gff3.md)

在线说明可能随版本更新；项目执行事实以本文记录的服务器日志、配置副本、版本和文件为准。
