# 范围与路由

路由由 `scripts/plan.py` 判定表实现；本文是判定表的解释。LLM 可解释与提候选，但不得越过代码层硬约束。

## 支持的文库组合（plan.SUPPORTED_COMBOS）

| technology | library_type |
|---|---|
| illumina_wgs | wgs |
| illumina_wgs | rna_seq |
| illumina_hiseq_hic | hic |
| hifi | wgs |
| ont | wgs |

组合外即阻断，提示可用组合。technology 有值但缺 library_type 也阻断。

## 路由意图

| 意图 | 条件 |
|---|---|
| `assemble_and_scaffold` | 有可组装读段 + Hi-C |
| `assemble_only` | 有可组装读段，无 Hi-C |
| `existing_then_scaffold` | 有既有组装 + Hi-C |
| `existing_only_validate` | 只有既有组装，无 Hi-C |
| `blocked` | 有阻断项，或无任何组装源 |

"可组装读段"指 wgs 类文库（hifi/ont/illumina_wgs）；BAM 不视作组装源（BAM ≠ HiFi）。有 Hi-C 但无组装源时阻断并建议：补长读/二代 WGS，或提供 existing_assembly。

流程步派生：Hi-C 路线的 `hic_mapping` 步自带 `juicebox_review` 人工门，`scaffolding` 步带 `manual_approval` 门——这两道门不可由 LLM 或用户口头撤销。

## 硬阻断清单（代码直接拦）

1. `delivery.representation` 未定义或 `unresolved`——不擅自选择交付路线。
2. 缺 `proband` 角色文库——无法确定组装主体。
3. 文库类型不支持 / technology 与 library_type 不匹配 / 缺 library_type。
4. 双端 illumina 文库缺 R1 或 R2（按文件名 R1/R2 存在性判断）。
5. `sample.ploidy > 2`——多倍体组装路径未验证（冻结首例例外：走 use-case-001 的真实冻结流程，见 `docs/use-case-001.md`）。
6. `sample.mixed_sample=true`——混样路径未验证。
7. 只有 Hi-C 无可用组装源。

## plan 时依赖要求

`REQUIRED_TOOLS = {fastqc, fastp, hifiasm, nextflow}`——manifest 的 `software_versions` 缺任一记录即报"依赖不足"，明确报错而非无界重试。

## 冻结首例的路由口径

use-case-001（葡萄三倍体，短读+Hi-C）：步 1~9 用户已手工完成，skill 首试接管目标是**步 10 结构注释、步 11 功能注释**。接续输入起点为最终 .fa / hap 组装 / BUSCO 结果。该路线由真实脚本还原背书（SGE、手写 Juicer、DpnII、3D-DNA `-m haploid`），不走通用多倍体路由。
