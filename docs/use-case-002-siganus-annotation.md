# 用例 #002：Siganus 结构 + 功能注释真实 SOP（冻结为注释阶段参考实现）

> 状态：**frozen（已冻结）**，2026-09-22 依据用户提供的真实全流程记录与 pipeline 代码整理。
> 定位：D-010 定下"注释（结构+功能）是 skill 首试接管目标"后，本用例提供**已在真实服务器完整跑通**的注释 SOP 基线。skill 生成的注释 SOP 以此为参考实现；陷阱库 PIT-002~006 的种子全部来自本用例。
> 物种：**黄斑蓝子鱼（Siganus canaliculatus / rabbitfish）**，染色体级基因组，服务于植食性泛基因组研究（三套组装：GCA048 / Nanhai / Zhuhai；功能注释在 Qatar 组装上完成）。
> 原始记录（逐命令级，存于 `docs/case-siganus/`）：结构注释 `Siganus_self_Structural_Annotation_Record.md`、功能注释 `Qatar_功能注释全流程记录.md` 与 `README_功能注释流程.md`、预检修复 `PREFLIGHT_FIX.md`。可运行 pipeline 代码在用户工作区 `D:\1_yanjiusheng\Siganus_self\{three_assemblies,annotation_qc}\`（磁盘版含 v3 修复，见下"已知问题"）。

## 一、执行事实与边界（先读这个）

- **由用户在服务器人工执行完成**，非 skill 执行。结论：SOP 本身是 `case_validated`（真实跑通）；**skill 接管执行仍为 planned**。
- 结构注释：self 组装全流程完成并交付（23,924 编码基因，蛋白 BUSCO 97.4%）。
- 功能注释：Qatar 组装 0~8 步全部完成，整合验证 `PASS`（86.09% 代表序列获至少一类注释）；第 9 步绘图脚本已交付、本地已验证，服务器最终运行报告未回传——不标记为已完成。
- 三套组装的批量 pipeline（three_assemblies v2/v3）是**准备好的运行代码**，按 README 明确声明"不是已完成的服务器任务"；Qatar 功能注释是已完成的正式运行。

## 二、结构注释 SOP（8 阶段，阶段级检查点）

| # | 阶段 | 工具与关键参数 | QC / 检查点 |
|---|---|---|---|
| 1 | 重复注释 | RepeatModeler2 独立建库（每套组装不共享库）；RepeatClassifier 需 FamDB/Dfam（真实环境补装 dfam40.0.h5，famdb 3.0.0）；RepeatMasker `-s -xsmall -lib` | **软屏蔽核验**：小写比例 + N 比例 + ID/长度/忽略大小写 SHA256 与输入一致（mask_qc.json），否则停止 → PIT-006 |
| 2 | RNA-seq 比对 | HISAT2 每套组装独立建索引；30 对 FASTQ 成对比对（`--dta --no-unal`，链特异性未确认不得猜测 `--rna-strandness`）；samtools sort/index | 两端退出码检查 + `samtools quickcheck`；映射率与参照案例对照 |
| 3 | 基因预测 | BRAKER3 3.0.8 ETP：`--softmasking --gff3 --threads=48 --AUGUSTUS_ab_initio`，BAM + `--prot_seq`（Vertebrata.fa，1939 万条） | 输入 FASTA 标题须与 BAM 参考名一致（v3 修复的教训）；保留原始 braker.gtf/aa 作对照 |
| 4 | TSEBRA 重合并 | 从实际 braker3.cfg 复制，仅改 `intron_support` 1.0→0.8（受控对照验证过的候选值）；保留 `--keep_gtf training.gtf`、`--filter_single_exon_genes` | **必须做 BUSCO 受控对照**（baseline vs 调参 vs 中间模型）→ PIT-002 |
| 5 | 最长转录本 | AGAT `agat_sp_keep_longest_isoform.pl`（用 AGAT 自己的 perl，清除 PERL5LIB 等）；gffread 提取 pep/cds | 蛋白 QC：内部 `*`/X/空序列/重复 ID 计数，如实记录不自动删除 |
| 6 | 编码 GFF3 导出 | export_coding_gff3.py（流式版）：按 CDS 关联保留编码转录本及其 gene | 图关系验证 + 重新提取逐 ID 比对蛋白/CDS 长度与 SHA256；导出前后序列必须完全不变 → PIT-005 |
| 7 | BUSCO 三方评估 | `-m proteins --offline -c 48`，同一 lineage，对 baseline / all_isoforms / longest 分别评估；不覆盖旧结果、不用 `-f` | genome 模式默认不跑（miniprot 字段问题）→ PIT-003 |
| 8 | 归档 | 软链接发布 all_isoforms 与 longest；provenance.json 记录参数、输入大小/mtime、脚本哈希 | all_isoforms 只有 GTF，不得改扩展名冒充 GFF3 |

**检查点与续跑规则**（three_assemblies 的实现，直接对应本项目状态机思想）：完成阶段写 `COMPLETE.json`；同输入/参数/脚本哈希 + 同 run-id 再启动时跳过；任一元数据变化拒绝混跑、须换 run-id；无标记但目录已存在视为失败/中断，拒绝覆盖、不自动删除、不伪造完成标记。

**资源**：默认总预算 48 线程（HISAT2 40 + sort 辅助 4）；RepeatMasker `-pa` 是并行任务数不是核数；90 份 BAM 的磁盘占用不能用组装 FASTA 大小估算。

## 三、结构注释真实结果（self 组装）

| 项目 | 默认参数最长集 | intron08 编码最长集 |
|---|---:|---:|
| 蛋白条数 | 22,435 | 23,924 |
| 完整 BUSCO | 3396（93.3%） | 3544（**97.4%**） |
| 缺失 BUSCO | 207 | 67 |

诊断路径（值得 skill 学习的方法论）：基因组 BUSCO 异常 → 分别评估 AUGUSTUS（97.6%）/GeneMark（97.7%）→ 定位损失在 TSEBRA 合并 → **单因素受控对照**（original / baseline / intron08 / no_single_filter 四组）→ 确认内含子阈值是主因（净增 150），单外显子过滤仅差 3 个 → 保留过滤、只调阈值。改进未重组装、未重跑屏蔽/比对/预测，只改变筛选与后处理。

## 四、功能注释 SOP（0~8 步 + 独立第 9 步绘图）

**模式：先小样本贯通测试，通过后晋级正式全量**（test-then-promote）——测试 100 条代表蛋白跑 0~8 步，`promote.sh` 核对测试状态与输出指纹后才生成正式脚本。对应本项目的 smoke → real 分级验证。

| 步 | 内容 | 关键规则 |
|---|---|---|
| 0 | 输入处理 | 统计单位 `gene_representative`（每基因最长蛋白代表，等长按 ID 字典序）；只移除一个末端 `*` 并记录，不碰内部终止符；蛋白↔基因映射失败即停止，不猜后缀、不去版本号 → PIT-004 |
| 1~5 | DIAMOND 比对 ×5 | NR 动物子集 / Swiss-Prot 真核 / KEGG 动物 / KOG / TrEMBL 真核；`--very-sensitive -e 1e-5 -k 25 --max-hsps 1`，17 列输出含覆盖度；`qcovhsp ≥ 50%` 后选最高 bitscore；保留 raw/filtered/best 三层命中 |
| 3/4 | KO/KOG 判定 | 只认最佳命中的配套注释记录；近最高分 5% 范围的不同 KO/KOG 标 `ambiguous_near_top`，不跳过最高分无 KO 去挑低分有 KO |
| 6 | InterProScan | 5.76-107.0 + Java 11（`java_home` 隔离注入）；`--goterms --iprlookup --disable-precalc`；成员签名命中 ≠ IPR 注释，分表统计 |
| 7 | GO 整理 | 只用本次 IPR `--goterms` 输出去重，不从描述文本猜 GO |
| 8 | 整合验证 | 七类 0/1 总表 + 覆盖率 + 重叠组合；validation.json PASS 指技术一致性，不证明功能推断正确 |
| 9 | 绘图 | 独立运行；Venn/UpSet 逐基因集合计算；GO/KEGG 分类资源下载后存 provenance |

**KOG 恢复案例**（正式运行真实故障）：25 个目标 ID 不在参考注释表 → 专用恢复程序复用原始比对，缺失保留为 `best_hit_unmapped`，**不改选低分命中、不编造编号、不修改共享库**，恢复后自动续跑 5~8 步。

**真实结果（Qatar，分母 26,467 条基因代表序列）**：Nr 84.92%、Swiss-Prot 72.85%、KEGG 72.85%、KOG 53.05%、TrEMBL 84.32%、InterPro 81.96%、GO 73.28%，**Any-Annotated 86.09%**（22,785 条）；七类均未注释 3,682 条。KEGG 是同源候选 KO，不等价 KofamScan/KAAS；未做富集分析。

## 五、已知问题与检查点（error 类经验，供 preflight/SOP 生成直接引用）

1. **BRAKER 输入 FASTA 标题**（v3 修复）：BAM 参考名 `CM109094.1` vs BRAKER 内部 FASTA 把整行描述下划线连接成 ID → GeneMark 无法提取转录本。修复版启动前生成 `genome.id_only.softmasked.fa`（仅保留首字段），校验 ID 唯一性/长度/软屏蔽未变，30 个 BAM 的参考名字典须与 FASTA 完全一致。
2. **AGAT 与 BRAKER 环境 Perl 冲突**：`Can't locate Bio/Tools/GFF.pm`（PERL5LIB 混入）→ 显式用 AGAT 自己的 perl 并 `env -u PERL5LIB -u PERLLIB ...`。
3. **工具路径不得硬编码**：`${SHARED}/env/braker3/bin/` 下实际没有 gffread → 动态 `type -P` 并记录。
4. **BRAKER 环境 Python 段错误**：`${SHARED}/env/braker3/bin/python` 连最小测试都段错误 → 用系统 Python `-I -u -X faulthandler`；解释器能打印版本 ≠ 环境验证通过。
5. **InterProScan 预检假失败**：无输入显示 help 后 exit 1，被误判命令失败 → 仅对显式 `--help` 探测兼容该行为，其余非零退出仍算失败并存完整日志。
6. **Java 版本**：base 环境 Java 25，InterProScan 5 要求 Java 11 → 只向 IPR 子进程注入 `JAVA_HOME`，不按目录名猜版本。
7. **共享数据库只能发现不能猜**：目录里多个 `.dmnd` 候选时停止并列出，绝不自动选择；目录名/文件名不证明版本与物种范围（`swissport` 拼写以服务器实际为准）。
8. **自有 AUGUSTUS GTF 做功能注释的 ID 映射**（prepare_self_gtf.py）：CDS-based 映射、蛋白↔transcript 精确匹配、后缀不去除不猜测、gene/transcript ID 冲突即失败、输出 QC JSON 带 SHA256。

## 六、与用例 #001（葡萄）的衔接

use-case-001 的接管目标正是步 10（结构注释）与步 11（功能注释），本 SOP 即其参考实现，但须按物种适配：

| 项 | Siganus（本用例） | Grape #001 待采用时 |
|---|---|---|
| BUSCO lineage | actinopterygii_odb10（3640 组，2024-01-08） | eudicotyledons_odb12.2（保持与历史评估一致） |
| 蛋白证据 | Vertebrata.fa | 需选合适范围并记录来源版本 |
| 组装特点 | 单套染色体级 | 三倍体 hap1/hap2 分套，单倍型交付 |
| 调度 | 服务器直接 nohup（48 线程预算） | SGE（qsub，沿用 #001 环境） |

## 七、验证边界（引用时不得升级）

| 已证明 | 未证明 |
|---|---|
| 该 SOP 在真实服务器人工跑通（self 结构 + Qatar 功能） | skill 自动生成/接管执行过该流程（planned） |
| 三套组装批量 pipeline 通过本地 21 项单元测试 | pipeline 的真实端到端运行（README 明示未启动） |
| intron_support 0.8 对本数据有效（受控对照） | 0.8 对所有物种最优；新增模型的假阳性风险 |
| 功能注释 technical PASS + 86.09% 覆盖率 | 每个功能推断的生物学正确性；KEGG 候选 KO = 功能确认 |
| 第 9 步绘图本地验证 | 服务器第 9 步最终运行报告 |
