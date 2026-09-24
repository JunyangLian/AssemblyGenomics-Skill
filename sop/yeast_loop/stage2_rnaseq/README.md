# 段 2：RNA-seq 比对（新手版）

> 酵母项目 `yeast_s288c_loop`（run_id=batch01）第二段。绕过了段 1 后，这个包就是毕业包第二块。

## 这个阶段做什么、为什么

基因预测（段 3 的 BRAKER）不会凭空猜基因——它需要两条证据：**RNA-seq 比对**（转录证据，本段）和**蛋白证据**（Swiss-Prot，段 3 直接引用文件）。本段把两个 RNA-seq 样本比对回软屏蔽基因组：

```
hisat2-build 建索引 → hisat2 成对比对 | samtools sort → index + quickcheck → 比对率 QC
```

两个关键点（对应坑位）：

| 编号 | 坑 | 本包的防线 |
|---|---|---|
| PIT-007 | 线程超预算 | 预检检查 32 ≤ 全机核数；hisat2 16 + sort 4 的配比写死在 settings |
| 上游绑定 | 段 1 产物被改/被换 → 新证据对不上旧基因组 | **启动即核验 softmasked 基因组 sha256 = 段 1 冻结值**，不符直接停 |
| 比对率异常 | RNA-seq 质量差/样本错配 → 后续 BRAKER 证据质量差，无人报错 | 每样本解析 `overall alignment rate` 写入 qc.json；观测修正带 [70, 98]（2026-09-23 本数据集首观测 71/80；advisory），显著 <50% 先排查不硬闯 |

> 链特异性没有在数据里声明——**不猜**。BRAKER ETP 不依赖链特异信息，本段按未声明处理。

## 数据来源（skill 已核实）

| 样本 | SRR | 说明 |
|---|---|---|
| WT_Rep1 | SRR40431829 | S288c 野生型对数期，paired，rRNA-depleted（BioSample SAMN62802087，`/strain="S288c"`） |
| WT_Rep2 | SRR40431828 | 同上（研究 SRP732088 的 WT 对照） |

## 运行前检查单

1. 段 1 已完成且 `COMPLETE.json` 在（本段核验它的产物哈希）
2. 两个样本的 FASTQ 已下载并命名 `0.Raw_Data/rnaseq/WT_Rep{1,2}_{1,2}.fq.gz`（下载命令见 skill 会话）
3. `settings2.json` 路径核对无误（已按 preflight 冻结）

## 怎么跑

```bash
cd ~/yeast_test/sop/yeast_loop/stage2_rnaseq
python3 run_stage2.py --check      # 核验：工具/上游哈希/样本/budget
nohup python3 -u run_stage2.py --execute > stage2.nohup.log 2>&1 &
# 中断续跑：python3 run_stage2.py --execute --resume
```

酵母规模预计 10-20 分钟（两个样本各 ~1000 万 pairs）。

## 怎么判断成功

1. `runs/batch01/2.RNAseq/COMPLETE.json` = SUCCEEDED
2. 每个样本 `bam/<id>.qc.json` 的 `overall_alignment_rate_pct` 在 **[70, 98]** 区间（咨询性，观测修正）
3. `.sorted.bam` 与 `.bai` 都在，quickcheck 无输出（通过）

## 跑完贴回给 skill

- 两个 `bam/*.qc.json` 全文
- `logs/stage2.log` 最后 40 行

## 失败了怎么办

- `--resume` 从断点续；单样本失败会留下 `.hisat2.log`——它就是线索
- 比对率显著低于 50%：贴 `hisat2.log` 回来，先查 FASTQ 完整性（`gzip -t`）和样本与基因组的物种匹配，别急着往下走