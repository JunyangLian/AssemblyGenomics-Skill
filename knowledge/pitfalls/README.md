# 陷阱库（Pitfall Registry）

这个目录记录**"能跑通但不完整 / 不正确 / 缺前提"**（silent gap）类的坑，与"报错修复"（error）正交。

`scripts/run_pitfall_checks.py` 会遍历这里的每个 YAML 条目，尝试执行其定义了自动检查的探测脚本，并输出一份"静默缺口"警告报告。

## 核心思路

- **报错（error）**：命令返回非零 / 文件缺失 → 已有状态机与 preflight 负责阻断。
- **静默缺口（silent gap）**：命令返回 0、进程跑完、但有隐性问题（库版本太旧、步骤之间结果未接续、参数被默认值吞掉等）。
  本目录与 `run_pitfall_checks.py` 专门负责这一类。

## 条目格式（YAML）

```yaml
id: PIT-001           # 唯一编号
title: Dfam 库版本过旧         # 人类可读标题
phase: annotation     # 所属阶段
step: 10              # 冻结流程 DAG 步号
commands:             # 触发/受影响的命令（用于一键定位）
  - RepeatMasker
  - "..."
severity: warning     # info / warning / critical
symptom: >            # 「看起来成功了但…」描述
  RepeatMasker 跑通了，但因为只下到 dfam0 旧库，屏蔽少了很多。
root_cause: >         # 为什么会出现且不报错
  运行前只下载了 Dfam 0.x 版库，未同步最新 Dfam 数据库。
check:                # 一段可执行脚本（shell），返回非零或无输出则判定为缺口
  language: shell
  source: |
    echo "检测 Dfam 库版本…示例占位"
```

## 已收录

| 条目 | 主题 | 来源 |
|---|---|---|
| PIT-001 | Dfam 重复库版本过旧，屏蔽不完整 | 用户真实踩坑（grape 注释） |
| PIT-002 | TSEBRA intron_support 默认 1.0 过严，合并阶段丢完整基因（93.3%→97.4%） | Siganus 结构注释（受控对照定位） |
| PIT-003 | BUSCO genome 模式 --miniprot 误读停止密码子字段，E 值不可信 | Siganus 结构注释（PAF 逐字段核对） |
| PIT-004 | 蛋白 FASTA 内部 `.`/`*` 悄悄污染下游注释与分母 | Siganus 功能注释准备（2 条真实隔离） |
| PIT-005 | GFF3 残留无编码 gene/transcript，基因数虚高约一倍 | Siganus 结构注释（47,848 vs 23,924） |
| PIT-006 | "软屏蔽"FASTA 实为硬屏蔽/未屏蔽，BRAKER 拿不到重复信息 | Siganus 结构注释（11.98% lowercase 核验） |
| PIT-007 | 共享服务器线程/资源预算未经确认即拉满 | 用户 2026-09-22 指出（yeast SOP 规划中沿用了 48 线程默认） |
| PIT-008 | BRAKER 输入 FASTA 头含描述 → ETP 参考名与 BAM 不匹配，GeneMark 失败且提示误导 | Siganus GCA048（v3 HEADER_FIX）+ 酵母 2026-09-23 两度实跑 |
| PIT-009 | TSEBRA 单外显子过滤器是物种内含子含量依赖的——内含子贫乏物种上滤掉 ~95% 真基因（酵母 221 vs 5384，BUSCO 3.1% vs 99.0%） | 酵母 2026-09-24 单因素对照实证 |

PIT-001~006 来自 Siganus 真实注释全流程（见 `docs/use-case-002-siganus-annotation.md` 与 `docs/case-siganus/` 原始记录）；PIT-007 为服务器礼仪类（跨阶段，phase=general）。后续条目按需追加——可信度来自真实种子，不预先堆投机条目。