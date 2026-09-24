# AssemblyGenomics Skill

**帮助新手搭建第一套属于自己的基因组组装/注释流水线**——把测序数据与交付目标，变成一条可执行、带坑位预警、人类审核不可绕过、且每步都过基线校验的路线；项目走完，交付一套**属于你自己的可复用 SOP 毕业包**（D-020）。

## 为什么存在

组装/注释流水线的经典失败模式不是“报错”，而是**能跑通但不完整**（silent gap）：库版本过旧、步骤产物断裂、参数被默认值吞掉、注释只覆盖 4% 的基因——全程零报错。本项目把“专家踩坑经验”代码化，并用**文献基线锚点**回答新手最缺的问题：“我这个数正常吗？”

- **陷阱库**：9 条真实种子（PIT-001~009），全部来自真实项目事故（Dfam 旧库、TSEBRA 阈值、FASTA 头 vs BAM 参考名、单外显子过滤的物种依赖……），带可执行检查脚本
- **基线双层**：intake 时选定同种/同属已发表注释作锚点（D-016），范围外报 GAP 并区分合法偏离（多倍化等）与流程问题（指向对应 PIT）
- **审核门控**：人类批准二要素、hash 绑定、编辑引用校验——LLM 无法代写“已审核”
- **状态机与失效传播**：磁盘结构化记录为准，不实重试、不伪造完成标记
- **毕业包**：流程跑通后沉淀为可复用的四段 SOP（settings 冻结 + 检查点 + 基线），换物种按 intake 流程复用

## 真实验证（酵母机制环，use-case-003）

2026-09-23~24，S. cerevisiae S288C（R64 参考组装）四段全链路经 skill 生成的 SOP 在真实服务器跑通并逐段回传校验：

| 段 | 内容 | 关键结果 |
|---|---|---|
| 1 重复注释 | RepeatModeler2 → RepeatMasker | 软屏蔽 6.333% 小写，mask_qc PASS |
| 2 RNA 比对 | HISAT2 × 2 样本 | 比对率 70.96% / 79.94% |
| 3 结构注释 | BRAKER ET → TSEBRA → AGAT | **5,384 基因 / BUSCO 99.0%**（基线拦截 3.1% → 单因素对照 → 修复） |
| 4 功能注释 | DIAMOND×5 + InterProScan | **Any-Annotated 99.96%**（五库真菌适配） |

过程中捕获并硬化的真实缺陷：PIT-008（BRAKER 输入头 vs BAM 参考名，两次事故后 driver 自动 id-only）、PIT-009（TSEBRA 单外显子过滤器在内含子贫乏物种上滤掉 95% 真基因）、InterProScan GO 多值解析、ETP 蛋白环版本缺陷（如实降级 ET 模式并记录）。

## 安装（Codex 优先）

本技能包面向 **Codex CLI**（默认格式）：包内含 `AGENTS.md`（每次会话自动携带的方法论与硬约束）+
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

   之后每个 codex 会话自动携带本方法论；输入 `/assembly-genomics`（或描述“基因组组装/注释”
   类任务）触发完整流程。`~/.codex/AGENTS.md` 已存在时会拒绝覆盖并提示手工合并。

**其他平台**：ZCode 用户可用 `python scripts/package_skill.py --format zcode` 生成
`<name>/SKILL.md` 形态包，放到 `~/.zcode/skills/` 或 `~/.agents/skills/`。

> 本仓库同时是**开发仓库**（tests/、docs/ 全量）与 **skill 安装源**；`dist/` 下的 zip
> 由 `package_skill.py` 本地生成（不入库；仓库未发布 Release zip）。实机路径已脱敏，settings 以 `templates/settings/` 为准。

## 快速开始

```bash
# 依赖：Python ≥3.9 + jsonschema + PyYAML + pytest
python -m pytest -q                    # 117 tests，全绿
python scripts/skill_coach.py SM_WGS_1.fq.gz SM_WGS_2.fq.gz SM_hic_all_1.fq.gz SM_hic_all_2.fq.gz
python scripts/check_baselines.py --taxon actinopterygii protein_coding_gene_count=23864
python scripts/run_pitfall_checks.py
```

新手旅程：`skill_coach.py` 识别数据 → 路由 → 分步 SOP（每步挂坑位）→ `validate_project` → 逐段执行/回传校验 → 基线对照 → 毕业包。完整玩法见 `SKILL.md`。

## 目录结构

```text
SKILL.md                    # 入口文档（触发说明、硬约束、工作循环）
references/                 # 路由/表示/门控策略
schemas/ scripts/ templates/  # 校验器、路由、SOP 脚手架
knowledge/pitfalls/         # 9 条真实陷阱（含检查脚本）
knowledge/baselines/        # 类群兜底带（项目锚点优先）
sop/yeast_loop/             # 毕业包：四段 SOP + 冻结 settings + 检查点（酵母实证）
docs/                       # 决策记录、能力矩阵、用例实录、run_registry
tests/                      # 117 tests
```

## 诚实的边界（发布口径）

- 已验证：**注释全流程**（重复→RNA→结构→功能）在单倍体酵母上端到端跑通+校验；配置/模拟层机制全部测试覆盖
- 未验证：**从原始读段组装**（酵母环输入为已发表组装；葡萄 #001 计划为真实组装案例）、ETP 蛋白环（GeneMark-ETP git 版缺陷，走 ET 模式并记录）、多倍体/分相交付、长读组装路线
- 全部工具版本/数据库路径以各阶段 settings 为准；发布仓库请用 `templates/settings/` 脱敏模板，勿提交实机绝对路径（用户账号/服务器布局信息）

## 路线图

1. 葡萄 #001（三倍体、单倍型分套）：毕业包换物种复用的第一次实战（换锚点/库/开关）
2. GeneMark-ETP 缺陷修复后回归 ETP 模式，补齐蛋白证据
3. 陷阱库/基线持续以真实案例扩充（每个新案例收割新种子）

## License

MIT License（Copyright (c) 2026 25jylian）· Hosted on GitHub：<https://github.com/JunyangLian/AssemblyGenomics-Skill>