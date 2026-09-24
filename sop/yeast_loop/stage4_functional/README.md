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