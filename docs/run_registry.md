# 运行注册表

记录每次 run 的 ID、配置、输入输出、状态与耗时。当前处于 M1 配置/状态测试阶段，尚无真实组装 run；下表为登记结构。

| run_id | 阶段 | 配置摘要 | 输入 | 输出 | 状态 | 耗时 |
|---|---|---|---|---|---|---|
| batch01 | stage1_repeat | 32 线程；RM 2.0.7/RMasker 4.2.2/Dfam 3.9；driver v2 修正版 | GCF_000146045.2_R64 (12,157,105 bp) | `genome.softmasked.fa` + `repeat_library.final.fa` + `mask_qc.json`（PASS，lowercase 6.333%） | SUCCEEDED | ≈17 min |
| batch01 | stage2_rnaseq | hisat2 2.2.1/samtools；上游 softhash 绑定通过 | WT_Rep1(70.96%)/WT_Rep2(79.94%) | bam/*.sorted.bam(+bai) + qc.json | SUCCEEDED | ≈6 min |

首次失败批次（driver -dir 臆造参数）归档于 `_archive_failed_batch01_20260922/`，保留不删。

状态词表：`PENDING -> READY -> RUNNING -> SUCCEEDED`；`RUNNING -> FAILED / WAITING_REVIEW / BLOCKED`；`WAITING_REVIEW -> READY / REJECTED`；常驻 `SKIPPED_NOT_APPLICABLE`、`STALE`。| batch01 | stage3_braker | ET 模式（RNA 证据）；TSEBRA 无单外显子过滤；上游 hash 绑定全过 | softmasked + 2 BAM + Swiss-Prot(绑) → 基因预测 | 5,384 最长蛋白；BUSCO 99.0%[S96.9/D2.2/F0.2/M0.8]；基线 enforce 双达标 | SUCCEEDED（回传层基线拦截后对照确认） | BRAKER 46min + 后处理 |
| batch01 | stage4_functional | 五库真菌适配；IPR 5.76+Java11；GO 解析修复后 | 5,384 蛋白 → 功能注释 | Any 99.96%；Seven 类分布如 use-case-003 §14 | SUCCEEDED（GO=0 复现→修复→4,517 验证链） | 约 3h（IPR 占大头） |
