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