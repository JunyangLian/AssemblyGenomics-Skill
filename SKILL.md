---
name: assembly-genomics
description: 基因组组装/注释自适应流程 Copilot。当用户提到基因组组装、Hi-C 挂载、scaffolding、Juicebox 调图、BUSCO 评估、单倍型/hap1/hap2、purge_dups、污染或细胞器分离、重复屏蔽、结构/功能注释（MAKER/InterProScan/eggnog）、或有 fastq/fasta/gfa/bam 测序数据想组装、评估、注释时使用——即使用户没有明确说"组装"或"skill"。核心价值：LLM 自适应路线 + 代码层硬约束 + 强制人类审核门控 + 静默缺口（silent gap）检测。
---

# AssemblyGenomics Skill

**目标用户：第一次独立搭建基因组组装/注释的新手。** 把用户的测序数据与交付目标，转成一条**可执行、带坑位预警、人类审核不可绕过**的组装/注释路线，手把手走到交付。skill 的价值不是"代码一次写对"，而是**捕获"能跑通但不完整"（silent gap）**：库版本过旧、步骤间结果未接续、参数被默认值吞掉——这些命令返回 0 却埋雷的情形。项目终点除结果外，还交付一套**属于用户自己的可复用流程 SOP 包**（冻结 settings/版本/检查点），此后用户可脱离 skill 自行复用。

## 不可逾越的硬约束

这些约束由代码层（schema/校验/路由）强制，LLM 只能解释和提候选，**不得绕过**：

1. **交付表示必须显式声明**。`delivery.representation` 未填或为 `unresolved` 时阻断澄清，不静默假定；primary 不冒充分相结果，phased 交付需专门证据（D-003）。
2. **人类批准二要素缺一不可**：`approval.approved_by_human=true` 且 `submission_action` 非空。LLM 不能写出"已审核"状态，也不能复用旧版 hash 的批准。
3. **状态以磁盘结构化记录为准，不以聊天历史为准**。状态词表与迁移见 `references/qc-and-review-policy.md`。
4. **硬阻断场景直接停**：缺 R2、错误文库类型、样本角色冲突、多倍体路径未验证、混样、只有 Hi-C 无组装源。告知用户缺什么、能做什么，而不是降级猜测。
5. **失败/缺失如实报告**。指标缺失、工具失败不得包装成正常通过；显示"未评估/不适用/执行失败"。
6. **不臆断环境**。本机探测不到的能力（如 bash 存根不可用）标记"需人工/需服务器"，不宣称已验证。
7. **资源预算必须显式向用户确认**（PIT-007）。线程/内存/磁盘写入 project.yaml 前先问"这台服务器你安全可用多少"——服务器可能公用或多用途，不得沿用默认值、示例命令或上一项目的预算（如 48 线程）；执行中同样不得超预算。

## 入口与用户旅程

所有用户都走**同一条新手旅程**（D-020），不设专家并行通道。旅程入口是 `skill_coach.py`：新手把数据文件名放进来，skill 判断有哪些数据、定路由、输出带坑位预警的分步 SOP：

```bash
python scripts/skill_coach.py SM_WGS_1.fq.gz SM_WGS_2.fq.gz SM_hic_all_1.fq.gz SM_hic_all_2.fq.gz --repr primary_reference
```

输出 JSON 含：识别出的数据类型与警告、路由意图与阻断原因、每个流程步的 `pitfalls`（来自 `knowledge/pitfalls/` 陷阱库）。把阻断原因和坑位预警**原样转述**给用户，不要软化。随后走标准链路 `validate_project → plan → SOP 包 → 执行 → validate_review → summarize_results`（下节）。`validate_project`/`plan` 等脚本是旅程的内部机械，不是另一类用户的独立入口。

## 工作循环（backend A：SOP 包模式）

skill 本地生成 SOP 包 → 用户在服务器自行运行 → 回传 logs/产物 hash/run 明细 → skill 校验后生成下一段 SOP：

1. **环境预检** `preflight.py`：探测调度器（目标环境是 SGE，不是 SLURM）、conda env、工具与数据库版本。缺失工具列为 blocker。
2. **配置校验** `validate_project.py`：校验 `templates/project.yaml`（schema、路径、样本角色、表示必填）。阻断时给出字段路径与原因。**intake 同步动作**：确定数据来源时一并选定最近的已发表同类写入 `baselines` 节（同种/同属注释或组装，带 accession/doi）——这是结果合理性对照的锚点（D-016），与选 BUSCO lineage 同一优先级。
3. **路由与方案** `plan.py`：判定路由意图（`assemble_and_scaffold` / `assemble_only` / `existing_then_scaffold` / `existing_only_validate` / `blocked`），生成流程步。Hi-C 步自带 `juicebox_review` 人工门。
4. **SOP 包生成**：按流程步产出脚本与说明，每步附陷阱库预警。**生成前先向用户确认线程/内存/磁盘预算**（PIT-007），SOP 内所有并发参数以确认后的预算为上限。**参数纪律（error_log 实证教训）**：SOP 中每个工具的 CLI 选项必须经目标版本 `-h/--help` 实测或官方文档核对，凭记忆拼参数会导致产物落错位置这类静默事故；不确定的选项宁可省略并在 provenance 记录。**指令纪律**：给用户/写进 SOP 的兜底分支（`|| { ... }`）不得与管道同用——管道退出码取自末级命令，`cmd | tail || fallback` 的 fallback 永远不会触发（两次事故，已入 error_log）。**危险指令纪律（D-022）**：任何用户指令中禁止出现裸 `rm -f`/`rm -rf` + 通配符——需要清理时先 `ls` 展示现状、点名到确切文件、或交由用户自查后自行删除（2026-09-23 因此类指令误删 2.7 GB 数据）。**交付规程（D-021）**：每个 SOP 包必须附带落盘指令——目录创建命令（`mkdir -p` **必须出现在每条落盘/校验指令块开头，即使假定目录已存在**——已两次因省略被用户点名）、文件传输方式（优先复用用户已有传输习惯，不默认假设通道存在）、以及带期望 sha256 的完整性校验命令；包内路径一律服务器绝对路径，产物目录在包内自包含。
5. **回传校验**：用户跑完回传后，核对产物 hash 与 run 明细（`state_registry.py` 状态机），失败后须显式经 READY 才能重调度，禁止无界重试。
6. **审核门控** `validate_review.py`：post-review 产物进入下一阶段前，校验人类批准、hash 绑定、编辑引用合法性、liftover 归属。
7. **汇总报告** `summarize_results.py`：从结构化产物确定性提取指标，缺失/失败如实标注。
8. **陷阱检查** `run_pitfall_checks.py`：跑 `knowledge/pitfalls/` 的自动检查，输出静默缺口警告。判定逻辑区分"真缺口"与"环境不支持/执行失败"，不误报。
9. **基线对照** `check_baselines.py --project <project.yaml>`：关键指标对照 intake 选定的项目文献锚点（权威），未覆盖指标退回 `knowledge/baselines/` 类群兜底带（advisory）——回答"这个数正常吗"，范围外报警并区分合法偏离（多倍化）与流程问题（指向对应 PIT 条目）。未选锚时输出明示"仅类群兜底带"，报告须如实标注。
10. **毕业包**：全部阶段完成后，把本轮实际跑通的流程固化为一套**可复用 SOP 包**（settings 绝对路径/版本、阶段化 Python 驱动、检查点与续跑规则、坑位预警），交付用户自行复用——这是"帮助新手搭起第一套"的终点形态（D-020）。

## 脚本速查

| 命令 | 用途 |
|---|---|
| `python scripts/skill_coach.py <files...> [--repr X] [--ploidy N]` | 新手入口：数据识别+路由+分步 SOP 带坑位预警 |
| `python scripts/preflight.py --data-root <dir> [--manifest m.json] [--json]` | 服务器环境预检（SGE/conda/工具版本） |
| `python scripts/validate_project.py <project.yaml>` | 配置校验，阻断时给字段路径 |
| `python scripts/plan.py <project.yaml>` | 路由判定；`--root <dir>` 用于失效传播 |
| `python scripts/state_registry.py register/transition/recover --root <dir> --project <id> ...` | run 状态机（磁盘持久化、原子写入） |
| `python scripts/validate_review.py <review_pkg.json>` | 审核门槛校验（通过 exit 0，阻断 exit 1） |
| `python scripts/summarize_results.py --project p.json --products prod.json [--markdown]` | 汇总报告，缺失如实标注 |
| `python scripts/run_pitfall_checks.py [--dir knowledge/pitfalls] [--json]` | 静默缺口检查 |
| `python scripts/check_baselines.py --taxon <类群> metric=value ...` | 文献基线对照（"这个数正常吗"） |

## 深入阅读（按需加载）

- `references/scope-and-routing.md` — 支持矩阵、路由意图判定表、硬阻断清单
- `references/assembly-representations.md` — 交付表示枚举、默认立场、phased 证据要求
- `references/qc-and-review-policy.md` — 状态词表、审核门控规则、失效传播语义
- `docs/use-case-001.md` — 冻结首例（葡萄三倍体）：真实数据形态识别教训、流程 DAG、手写 Juicer 流程还原（SGE/DpnII/`-m haploid`）
- `docs/use-case-002-siganus-annotation.md` — **注释阶段参考实现（冻结）**：结构注释（BRAKER3+TSEBRA+AGAT+BUSCO）与功能注释（DIAMOND×5+InterProScan）真实跑通的 SOP、参数、QC 与检查点；生成注释 SOP 前必读
- `docs/capability_matrix.md` — 能力等级（引用前先看，不得夸大）
- `knowledge/pitfalls/README.md` — 陷阱库条目格式与索引（PIT-001~006 均为真实踩坑且经真实数据校准）；新坑按此追加
- `knowledge/baselines/README.md` — 文献基线条目格式与指标名；结果合理性对照的扩充流程（升 enforce 须 ≥2 篇 doi）
- `docs/decisions.md` — 全部关键决策（D-001~D-012）

## 能力现状（如实声明，引用时不得升级）

- 配置/模拟层：117 tests 全绿（路由、审核门槛、状态机、报告、陷阱库机制、基线对照、新手向导）。
- **真实数据端到端（酵母机制环 use-case-003，2026-09-24）**：注释全流程四段（重复注释 → RNA 比对 → 结构注释 → 功能注释）经 skill 生成 SOP 跑通并逐段回传校验——5,384 基因 / BUSCO 99.0% / Any-Annotated 99.96%；毕业包沉淀于 `sop/yeast_loop/`。
- 未验证（诚实边界）：从原始读段组装（葡萄 #001 计划为真实组装案例）、ETP 蛋白环（GeneMark-ETP git 版缺陷，走 ET 模式并如实记录）、多倍体/分相交付、长读路线。
- 引用能力结论时必须声明属于哪一层（配置/模拟、真实案例）。详细等级见 `docs/capability_matrix.md`。
