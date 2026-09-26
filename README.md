# AssemblyGenomics Skill

**生信流程的可靠性决策系统**——它不只是生成"下一步运行什么"的命令，而是根据输入数据决定流程、在每个阶段检查结果，并判定：**继续、警告、还是回退修复**。

## 它解决什么问题

生信分析里最隐蔽的一类失败：**流程正常结束（exit 0），但结果已经不完整或不可靠**——数据库版本不合适、参数被默认值吞掉、RNA-seq 证据没有真正进入结构注释、功能注释最后只覆盖一小部分基因。这类失败零报错，却足以让整个后续分析建立在错误地基上；没有经验的人会直接拿结果往下做。

本项目把真实项目里的**失败模式、领域判断与 QC 标准**结构化，让 Agent 能够：

- 根据输入数据**决定流程**（路由 / 阻断 / 证据模式选择）
- 在每个阶段**检查结果**（9 条真实失败模式的陷阱库 + 文献基线锚点 + hash 绑定）
- 判定**继续 / 警告 / 回退修复**（检查点 + 失效传播 + 验证分层）

长期目标：把依赖个人经验的生信分析，逐渐变成一个**可复用、可检查、可验证的决策系统**——解决 Scientific Agent 的可靠性问题，而不仅仅是自动化问题。

对新手，它是手把手的护栏；对熟手，它是第二双眼睛——**静默缺口不挑人群**（本项目捕获的 TSEBRA 阈值事故就发生在一个已经跑通全流程的熟手项目里）。

## 为什么存在

组装/注释流水线最阴险的失败不是"报错"，而是**能跑通但不完整**（silent gap）：库版本过旧、参数被默认值吞掉、注释只覆盖了 4% 的基因——全程零报错，直到交付才发现。本 skill 把专家踩坑经验代码化，并用**文献基线锚点**回答新手最缺的问题："我这个数正常吗？"

## 它能帮你做什么

- **认数据**：随手丢一份文件清单，自动识别 WGS 短读 / Hi-C / RNA-seq / 已有组装；识别不了的 FASTQ 一律按 unknown 阻断待确认（不默认当 WGS），R1/R2 按样本前缀核对成对性（A_R1+B_R2 不算成对）；文件名线索（如 hap1/hap2）只提示候选交付目标，须显式确认后才路由
- **定路线**：根据数据与目标推荐流程——从原始读段组装、已有组装接续 Hi-C 挂载，到结构注释与功能注释
- **出 SOP**：生成可逐段执行的 SOP 包：每步含命令、资源预算、必须人工介入的检查点（如 Hi-C 的 Juicebox 校正）
- **预警坑**：每一步挂载真实踩坑库——9 条真实事故种子（Dfam 旧库、TSEBRA 阈值、单外显子过滤的物种依赖……），带可执行检查脚本，专抓"能跑通但不完整"
- **验结果**：阶段成果回传后自动校验——静默缺口检查 + 基线对照，通过就发下一段 SOP，不通过就给修复脚本
- **可复用**：全流程跑通后沉淀**毕业包**（冻结 settings + 检查点 + 基线锚点），换物种按同一套流程复用

## 工作流程

![工作流程总览](assets/workflow-overview.png)

## 快速开始

依赖：Python ≥3.9 + `jsonschema` + `PyYAML` + `pytest`。克隆仓库即可运行：

```bash
# 识别数据 → 路由 → 生成带坑位预警的分步 SOP（示例文件名；交付表示必须显式声明）
python scripts/skill_coach.py SM_WGS_1.fq.gz SM_WGS_2.fq.gz SM_hic_all_1.fq.gz SM_hic_all_2.fq.gz --repr primary_reference

# 静默缺口体检（9 条真实陷阱探测器）
python scripts/run_pitfall_checks.py

# 结果基线对照："这个数正常吗？"
python scripts/check_baselines.py --taxon actinopterygii protein_coding_gene_count=23864

# 全量回归（128 tests）
python -m pytest -q
```

完整玩法见 [SKILL.md](SKILL.md)。

## 安装为 Codex 技能

本技能包面向 **Codex CLI**：包内含 `AGENTS.md`（每次会话自动携带的方法论与硬约束）+
`commands/assembly-genomics.md`（按需触发的 slash 命令）+ 全部资产（scripts/knowledge/references…）。

1. **获取包**：克隆仓库（`git clone https://github.com/JunyangLian/AssemblyGenomics-Skill.git`），
   在仓库根运行 `python scripts/package_skill.py` 生成 `dist/assembly-genomics-<ver>.zip`（dist/ 不入库）；
2. **安装**（PowerShell / bash 均可）：

   ```powershell
   # 一键安装到 ~/.codex（AGENTS.md + commands/ + 资产）
   python scripts/package_skill.py --install
   # 或手动：解压 zip，将 AGENTS.md 放入 ~/.codex/AGENTS.md，
   #         commands/assembly-genomics.md 放入 ~/.codex/commands/，
   #         资产目录保留在 ~/.codex/assembly-genomics/
   ```

之后每个 codex 会话自动携带本方法论；输入 `/assembly-genomics`（或描述"基因组组装/注释"类任务）触发完整流程。`~/.codex/AGENTS.md` 已存在时会拒绝覆盖并提示手工合并。

## 目录结构

```text
SKILL.md                    # 入口文档（触发说明、硬约束、工作循环）
references/                 # 路由/表示/门控策略
schemas/ scripts/ templates/  # 校验器、路由、SOP 脚手架
knowledge/pitfalls/         # 9 条真实陷阱（含检查脚本）
knowledge/baselines/        # 类群兜底带（项目锚点优先）
sop/yeast_loop/             # 毕业包：四段 SOP + 冻结 settings + 检查点（酵母实证）
docs/                       # 决策记录、能力矩阵、用例实录、run_registry
tests/                      # 128 tests
```

## 路线图

- 三倍体葡萄（短读 + Hi-C、单倍型分套交付）：毕业包换物种复用的第一次实战
- GeneMark-ETP 缺陷修复后回归 ETP 模式，补齐蛋白证据
- 陷阱库与基线随每个真实案例持续扩充

## License

MIT License（Copyright (c) 2026 25jylian）· Hosted on GitHub：<https://github.com/JunyangLian/AssemblyGenomics-Skill>
