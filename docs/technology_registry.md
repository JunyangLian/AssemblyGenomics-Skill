# 技术注册表

记录本项目实际使用或依赖的核心技术、模型/数据库、版本与用途。版本在正式接入前需重新核验。

## 依赖库（开发侧）
- Python 3.10.11（工作环境）
- jsonschema（校验 schema，基础校验）
- PyYAML（解析 project.yaml / manifest）
- pytest 9.1.1（测试）

## 组装相关：候选，未安装
以下为本项目拟复用的官方工具/工作流，属于 `planned` 状态，未安装、未验证。接入时固定版本并补验。

- Nextflow：计算执行框架（D-004）
- Juicer + 3D-DNA / Juicebox：Hi-C 人工调图路线一
- YaHS + JBAT：Hi-C 人工调图路线二
- hifiasm / Flye：长读长组装
- FCS（FCS-adaptor / FCS-GX）：接头与外源污染筛查
- QUAST / BUSCO：组装评估（辅助，非门控唯一依据）

所有上述工具的实际执行验证归入 M2 之后；当前仅用于定义数据契约与适配器接口。

## 冻结流程 #001（use-case-001）软件需求

> 来源：主流程反推（见 use-case-001.md 第六节 DAG）+ **真实脚本还原（第七节，2026-09-21 确认）**。**required** = 首条流程必经，preflight 会探测；**optional** = 可降级。
> 版本为候选，接入时固定并核验。**已按真实环境修正**：调度为 SGE（非 SLURM）、Juicer 为手写流程（非官方一键）、酶切为 DpnII。

| 环节 | 软件 | 状态 | 版本(候选) | 说明 |
|---|---|---|---|---|
| 短读质控 | fastp | required | ≥0.23 | 接头/质量过滤，R1/R2 配对 |
| hap contig 组装 | (历史已有) | required(已有) | — | 用既有 hap1/hap2 contig，不重跑 |
| Hi-C 比对 | Juicer（手写流程） | required | 手写 bwa+samtools+awk | **真实流程非官方 juicer.sh**：bwa mem -t 32 / samtools sort -n / changReadName.py / chimeric_blacklist.awk / fragment.pl |
| 酶切位点 | DpnII | required | — | 切点 GATCGATC（真实） |
| Hi-C 挂载 | 3D-DNA | required | 180922+ | `run-asm-pipeline.sh -m haploid -r 0 --build-gapped-map` |
| 调度器 | SGE | required | qsub-sge.pl | **非 SLURM**；`--queue bc.q`，bwa: 32核/54G，3ddna: 20核/25G |
| 人工调图 | Juicebox | required(门控) | 1.11+ | **硬性人工闸口，不可自动化代替** |
| 对参考标准化 | postreview_standardization | required(已有) | — | 一一对准染色体，须 review 批准 |
| 单倍型验证/去冗余 | purge_dups(待确认) | optional | 1.2 | 未确认是否用于真实流程 |
| 细胞器/污染分离 | contamination_screen | required(待补) | — | 未跑，待接入 |
| 评估 | BUSCO | required | eudicotyledons_odb12.2 | 双子叶库，复现保持一致 |
| 评估(辅助) | QUAST | optional | ≥5 | N50、contig 统计 |
| 比对/深度 | bwa + samtools | required | 0.7.17 / 1.x | conda env 提供（${SHARED}/.conda/envs/） |

**未在本流程使用**：SOAPdenovo2（真实流程未用其重组装，contig 已有）、hifiasm/Flye（无长读）、YaHS（真实命名指向 3D-DNA），均保持 planned。

## 注释阶段（步 10~11：结构 + 功能，skill 接管目标）

> 阶段真实进度：组装+评估已完成，注释未跑。**参考实现已冻结 = use-case-002（Siganus 真实 SOP，2026-09-22）**：下表"真实已验证"列的版本在 Siganus 服务器人工跑通过；grape #001 采用时按物种适配（lineage、蛋白证据、调度换 SGE）。

### 结构注释（BRAKER3 路线，真实已验证）

| 环节 | 软件 | 状态 | 真实版本 | 说明 |
|---|---|---|---|---|
| repeat 建库 | RepeatModeler2 | 真实已验证 | 待补（env `repeat_annotation`） | 每套组装独立建库；`-threads` 参数按安装版本核对 |
| repeat 屏蔽 | RepeatMasker | 真实已验证 | 待补 | `-s -xsmall -lib`；软屏蔽核验见 PIT-006 |
| repeat 数据库 | Dfam / FamDB | 真实已验证 | Dfam 4.0（famdb 3.0.0） | PIT-001（过旧）+ "Could not determine FamDB version"（缺失）两类坑 |
| RNA 比对 | HISAT2 + samtools | 真实已验证 | 待补 | 每套组装独立索引；`--dta --no-unal`（链特异性未确认） |
| 基因预测 | BRAKER3（GeneMark-ETP + AUGUSTUS） | 真实已验证 | **3.0.8** | ETP：`--softmasking --gff3 --threads=48 --AUGUSTUS_ab_initio` |
| 模型合并 | TSEBRA | 真实已验证 | 待补（/env/braker3/bin） | `intron_support` 默认 1.0 过严 → PIT-002 |
| 最长转录本 | AGAT | 真实已验证 | Perl 5.26.2 env | 独立 perl + 清 PERL5LIB；残留非编码记录 → PIT-005 |
| 序列提取 | gffread | 真实已验证 | 待补 | 路径动态 `type -P`，不硬编码 |
| 评估 | BUSCO | 真实已验证 | **6.1.0** + actinopterygii_odb10（2024-01-08，3640 组） | proteins 模式；genome 模式 miniprot 问题 → PIT-003（Miniprot 0.18-r281、HMMER 3.1） |
| 编码导出 | export_coding_gff3.py（自有，标准库） | 真实已验证 | streaming-v2 | 逐 ID 验证蛋白/CDS 不变 |

### 功能注释（DIAMOND + InterProScan 路线，真实已验证）

| 环节 | 软件 | 状态 | 真实版本 | 说明 |
|---|---|---|---|---|
| 同源比对 ×5 | DIAMOND | 真实已验证 | 2.x（`--block-size 2.0`） | `--very-sensitive -e 1e-5 -k 25 --max-hsps 1`，17 列含覆盖度 |
| 结构域/GO | InterProScan | 真实已验证 | **5.76-107.0**（Java 11 隔离注入） | `--goterms --iprlookup --disable-precalc`；预检 help 假失败见 PREFLIGHT_FIX |
| 库 | NR(动物)/Swiss-Prot(真核)/KEGG(101.0 动物)/KOG(20090331)/TrEMBL(真核) | 真实已验证（服务器 `${DB}/`） | 按路径记录 | 目录名不证明版本；多候选不自动猜选 |
| 集成/验证 | pipeline.py（自有，标准库） | 真实已验证 | — | test-then-promote 模式；KOG 缺失保留 unmapped 不改选低分 |

### 未采用但保留为候选

- MAKER / MAKER2 + Augustus/SNAP：另一条结构注释路线（本 SOP 用 BRAKER3 路线替代）；eggnog-mapper / Blast2GO：功能注释备选。均保持 planned。

### 真实环境部署线索（供 preflight 复用）
- conda env：`${SHARED}/.conda/envs/{bwa,samtools,java8}/`；3D-DNA `${HOME}/env/3D-DNA/`；Juicer 脚本 `${HOME}/env/Juicer/`。
- 辅助脚本：`local_scripts/{fastaDeal.pl, changReadName.py, wrap_fasta.py}`、`workflow_snapshot/local_scripts/`。
- 注释工具：若服务器已有 conda `bioconda` 通道，推荐安装（MAKER/Augustus/InterProScan/repeatmasker 均提供 bioconda 包）。