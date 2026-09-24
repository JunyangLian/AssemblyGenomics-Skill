# 段 1：重复注释（新手版）

> 这个包属于酵母项目 `yeast_s288c_loop`（run_id=batch01）。跑通并验收后，它就是你的**毕业包第一块**——以后换物种/换服务器，改 `settings.json` 就能复用（D-020）。

## 这个阶段做什么、为什么

基因组里散布着大量重复序列（酵母主要是 TY 转座子，约 2-3%）。基因预测软件如果不管它们，会在重复区乱预测出假基因。所以注释第一步是**先识别重复、再"软屏蔽"**：把重复区碱基改成**小写**（`acgt`），碱基本身不丢——BRAKER 的 `--softmasking` 就是读这个标记。

三个必须知道的坑（完整条目见 skill 的 `knowledge/pitfalls/`）：

| 编号 | 坑 | 本包的防线 |
|---|---|---|
| PIT-006 | 拿成**硬屏蔽**（重复区变 N，碱基永久丢失）或干脆没屏蔽——无报错 | 只用 `-xsmall` 参数 + mask_qc 三重核验（ID/长度/忽略大小写序列一致 + 小写比例 ≥0.5%），不过就停 |
| PIT-001 | Dfam 库**版本过旧或缺失**，屏蔽量悄悄缩水——无报错 | 预检读取 famdb 版本（当前冻结：Dfam 3.9）并写进 provenance |
| PIT-007 | 线程**拉满**影响同机他人 | 驱动自带预算检查：`thread_budget`（你确认的 32）≥ 全机核数就拒绝启动 |

## 运行前检查单

1. 包落盘到服务器 `~/yeast_test/sop/yeast_loop/stage1_repeat/`（与 `0.Raw_Data/` 同级），目录结构：
   ```text
   ~/yeast_test/
   ├── 0.Raw_Data/genome/GCF_000146045.2_R64_genomic.fna.gz   # 已验证 md5（不动它）
   └── sop/yeast_loop/stage1_repeat/
       ├── settings.json      # genome_gz 用服务器绝对路径；工具路径系 preflight 冻结值
       ├── run_stage1.py      # 产物落在本目录下 runs/<run_id>/1.Repeat_Annotation/
       └── README.md
   ```
2. `settings.json` 里的绝对路径与你的环境一致（已按 2026-09-22 preflight 冻结，换机器必须重新核）。
3. 预算 32 线程是确认值；换服务器先重问配额再改。

## 怎么跑

```bash
cd ~/yeast_test/sop/yeast_loop/stage1_repeat
python3 run_stage1.py --check      # 先预检：文件/工具/预算，不启动计算
python3 run_stage1.py --execute    # 正式跑（酵母 12 Mb，预计 <1 小时）
# 断线安全：nohup python3 -u run_stage1.py --execute > stage1.nohup.log 2>&1 &
```

每个阶段完成会落 `.stages/<阶段名>.done`；中断后加 `--resume` 续跑，已完成阶段自动跳过。

## 怎么判断成功

1. `~/yeast_test/sop/yeast_loop/stage1_repeat/runs/batch01/1.Repeat_Annotation/COMPLETE.json` 出现且 `status=SUCCEEDED`；
2. 同目录 `mask_qc.json` 的 `status=PASS`；
3. `lowercase_pct` 在 **[1, 10]%**（酵母参考带，advisory——显著低于 1% 说明屏蔽没生效，高于 10% 要怀疑库污染）。

三者任一不满足 = 本阶段未通过，**不要**把产物送进 BRAKER。

## 跑完贴回给 skill 的东西

- `mask_qc.json` 全文
- `provenance.json` 全文
- `logs/stage1.log` 最后 50 行（在包目录下执行）：
  `tail -50 ~/yeast_test/sop/yeast_loop/stage1_repeat/runs/batch01/1.Repeat_Annotation/logs/stage1.log`

skill 据此做回传校验（hash 绑定）、PIT 复查和基线对照，然后生成段 2（RNA-seq 比对）。

## 失败了怎么办

- **保留现场**：失败目录、日志、`.attempt` 都不删——它们是定位证据；
- 驱动只在阶段成功时写检查点，失败会打印 `[失败] 原因` 并停在原地；
- 常见失败：RepeatModeler 找不到搜索引擎（env 配置问题，找 skill 排查）；磁盘满（本阶段 <2 GB，一般不会）；预算超限（驱动启动时就拒）；
- 想整体重来：把 `runs/batch01/1.Repeat_Annotation` 改名归档（如 `..._failed_日期`），再全新运行——**不要**在半成品目录里手工拼。
