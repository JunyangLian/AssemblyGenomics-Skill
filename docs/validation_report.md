# 验证报告（M1）

> 编写：2026-09-21
> 验收口径：**M1 只完成第一类验证（配置/模拟）**：路由、审核门槛、状态转换、错误提示。不证明真实组装可运行，也不解除与生物学质量相关的任何断言。

## 结论

M1 全部测试通过（当前全量回归 **96 passed**，含后续补充的 preflight/adapter、陷阱库与新手向导）。但必须明确区分证明与不证明：

| 验证类型 | 是否做 | 证明什么 | 不证明什么 |
|---|---|---|---|
| 配置/模拟 | 已做（本阶段全部） | 路由、审核门槛、状态转换、错误提示的判定正确 | 工具真实运行与生物学质量 |
| 小样本 smoke test | 未做 | — | 接口兼容、命令产物链路 |
| 真实案例 | 未做 | — | 指定数据/版本/目标下的表现 |

阶段状态：**未执行任何真实组装**。`capability_matrix.md` 中组装相关路线保持 `planned`，不因配置测试通过而升级。

## 测试统计（pytest）

- 段 1 配置校验：`test_validate_project.py` — 7 passed
- 段 2 状态持久化：`test_state_registry.py` — 27 passed
- 段 3 路由与失效：`test_routing.py`（9）+ `test_invalidation.py`（8）— 17 passed
- 段 4 审核门槛：`test_review_gate.py` — 12 passed
- 段 5 报告如实：`test_reporting.py` — 9 passed
- 冻结 #001 补充：preflight（8）+ adapter smoke（5）= 13 passed
- 陷阱库（D-011）：`test_pitfalls.py` — 8 passed
- 新手向导（D-012）：`test_skill_coach.py` — 9 passed
- 全量回归：96 passed

## 阻断用例覆盖面

每个阻断均给出可定位的字段路径与原因：

- `validate_project.py`：交付表示未声明/unresolved、资源上限缺失、样本角色冲突、亲本缺失、远程上传未保持 false。
- `plan.py` 路由：缺 R2、错误文库类型、未解析交付表示、多倍体路径未验证、混样、只有 Hi-C 无组装源。
- `validate_review.py`：人类批准动作缺失（二者缺一）、旧版 hash 绑定复用、非法坐标/片段、重复坐标、hap 与 liftover 串用、rejected/undetermined 状态。
- `summarize_results.py`：运行前交付表示未定、工具失败/指标缺失不被包装为通过、污染候选未经批准删除被标记、primary 冒充分相被警告。

## 状态机与失效传播

- 状态词表与迁移在磁盘结构化记录上验证（`RunRegistry`），原子写入单文件。
- 禁止同一活跃项目重复提交；失败后需显式经 READY 才可重调度（无界重试被规则阻止）。
- 上游 FASTA/参数变化后下游 SUCCEEDED 等节点标 STALE，历史版本保留。

## 明确不在 M1 范围

- 无真实工具执行、无真实数据、无 Juicer/YaHS/3D-DNA 验证。
- Nextflow 仅 `workflows/nextflow.config` 落 failsafe 与资源占位；`workflows/adapters/` 只留输入/输出通道契约。
- `preflight.py` 尚未实现（依赖真实服务器信息）。

---

## 冻结流程 #001：preflight + adapter 通道契约（本阶段补充）

- **用例**：`docs/use-case-001.md`（真实数据 Grape-001，grape 三倍体，短读+Hi-C，复现+完整交付）。
- **新增测试**：`preflight.py`（+8）+ `smoke_adapter.py`（+5）= **79 passed 全量**。
- **新增产物**：`scripts/preflight.py`（服务器环境预检）、`workflows/adapters/juicer_3ddna/{adapter.nf,versions.json}`（通道契约+版本锁+人工门控声明）、`pytest.ini`（注册 smoke marker）、`use-case-001.md` 第六节流程 DAG、`technology_registry.md` 冻结软件表。

### 本阶段的验证边界（须如实区分）

| 验证类型 | 覆盖 | 不覆盖 |
|---|---|---|
| preflight（探测逻辑） | 缺失工具列为 blocker、R1/R2 配对完整性、资源探测不崩溃 | 不判定真实组装可运行 |
| adapter 通道契约（smoke,mock 工具） | 编排/产物捕获/人工门控声明、数据识别教训（Hi-C read≠矩阵） | Juicer/3D-DNA/BUSCO 真实执行与生物学正确性（须服务器完成） |

### 关键认知（供后续真实验证）

- 真实数据**无 HiFi/ONT 长读**，历史产物命名指向 **Juicer+3D-DNA** 主干线；本流程冻结为短读(de Bruijn) + Hi-C。
- **数据识别教训**：`.hic_1/2.fq.gz` 是 Hi-C 读段非矩阵；`Gracilaria_*` 参考 ≠ 目标物种 grape；`*.paf` 是比对非长读源。
- **脚本内容缺失**：上传清单仅有文件名/大小，不含 `.sh` 内容；因此冻结的是"主流可复现参考流程"并对齐**产物形态**（hap1/hap2、脚手架 gfa），未逐参数复刻旧脚本。
- 真实 smoke/真实验证需在**有这些工具的服务器**上完成，是本项目下一阶段（小样本 smoke）的硬依赖。

---

## 静默缺口陷阱库（D-011，本阶段补充）

**新增产物**：`knowledge/pitfalls/{README.md, 01-dfam.yaml}`、`scripts/run_pitfall_checks.py`、`tests/test_pitfalls.py`（+8，累计 **87 passed**）。

**机制**：检测"能跑通但不完整（silent gap）"，与报错修复（preflight/error）正交。判定逻辑抽为纯函数 `_decide_gap`——仅在检查脚本**明确宣告"缺口/GAP"**时判 gap，把"环境不支持/执行失败"与"真缺口"区分，杜绝误报。

**首条真实种子**：PIT-001 Dfam 重复库版本过旧（用户真实踩坑）。

### 验证边界

| 覆盖 | 不覆盖 |
|---|---|
| YAML 结构校验（缺字段/非法 severity/step 类型） | 真实服务器上 Dfam 库的自动探测（本机 bash 存根不可用 → 需人工，不臆断） |
| `_decide_gap` 关键词判定 | 真实基因组 repeat 屏蔽比例的生物学正确性 |

**关键认知**：本方向的本质是**持续把专家踩坑经验灌入陷阱库**，而非追求代码一次写完美。首条用 Dfam 打通机制，其余条目待用户/专家经验追加。

---

## 新手向导雏形（D-012，本阶段补充）

**新增产物**：`scripts/skill_coach.py`、`tests/test_skill_coach.py`（+9，累计 **96 passed**）。

**机制**：新手主入口。`skill_coach.py <files...>` 串联三件事——文件名数据识别（区分 wgs/Hi-C/RNA 读段、组装产物、无法识别的文件并警告，含真实 `SM-4_hic_all_1.fq.gz` 样式用例）→ plan 路由（复用同一套硬约束与阻断）→ 输出分步 SOP（JSON），每步附 `pitfalls` 坑位预警；陷阱库含 annotation 条目时追加 SUGGESTED 注释步，让 Dfam 类坑有挂靠点。

**验证边界**：

| 覆盖 | 不覆盖 |
|---|---|
| 文件名启发式识别、双端缺 R2 检测、路由阻断透传、每步 pitfalls 字段非空 | 真实文件内容识别（仅文件名级）、真实执行与服务器环境 |

---

## 陷阱库真实数据校准（2026-09-22，用户服务器回传）

**方法**：对 Siganus_self 项目的真实产物（已知标准答案）逐条运行探测器，比对"应报警/应沉默"。零新计算，全部只读命令。

**结果：6/6 全部符合预期**——3 个真阳性（PIT-002 original.cfg、PIT-003、PIT-005 AGAT 原始 GFF3）、4 个真阴性（PIT-001 Dfam 4.0、PIT-002 intron08.cfg、PIT-005 verified、PIT-006 11.978% 小写）、PIT-004 阴阳两面均验证（37,113 条蛋白中恰好命中 2 条阳性记录，ID 与内部点数与独立诊断的 EXPECTED 完全一致：`anno1.g17431.t2`×4、`anno2.427_t`×1；longest 集合 0 条）。

| 证据 | 数值 |
|---|---|
| BUSCO 版本 | 6.1.0（→ PIT-003 报警） |
| TSEBRA 配置 | original.cfg=1.0 / intron08.cfg=0.8 |
| FamDB | Dfam 4.0（2026-05-22），famdb-3.0.0 |
| 软屏蔽 | total=512,514,567, lowercase=11.978%, N=0.006% |
| all_isoforms 蛋白 | 37,113 条；2 条内部歧义（g17431.t2=4 点、427_t=1 点） |
| GFF3 | AGAT 原始 47848 gene / 23924 coding；verified 23924/23924 |

**结论**：陷阱库探测器从"合成测试通过"升级为"**真实数据校准通过**"（阳性命中 + 阴性不误报）。仍不覆盖：其他物种/其他 pipeline 产物上的表现（PIT-005 的 1.05 阈值在含大量 ncRNA 的注释上可能误报，待更多真实案例收紧）。

**过程记录**：会话中发给用户的 PIT-005 单行 awk 曾丢失右括号导致服务器语法错误（仓库 YAML 版本本身正确）；已记入 error_log.md，教训：给用户的命令必须从已测试源提取，不得手打改写。

---

## 酵母机制环端到端验证（2026-09-23~24，use-case-003，D-023）

本报告正文的 M1 结论（96 passed、真实案例未做）写于 2026-09-21，其后以分段补充推进；**当前状态以本节与 `capability_matrix.md` 为准**。

- **验证类型首次升级到真实案例层**：skill 生成的四段 SOP（重复注释 → RNA 比对 → 结构注释 → 功能注释）在真实服务器执行并逐段回传校验，四段全部通过，毕业包沉淀于 `sop/yeast_loop/`。
- **关键结果**：软屏蔽 6.333%（mask_qc PASS）；HISAT2 比对率 70.96% / 79.94%；结构注释 5,384 基因 / BUSCO 99.0%（TSEBRA 单外显子过滤被基线首次真实拦截，单因素对照定位，PIT-009）；功能注释 Any-Annotated 99.96%。
- **全量回归：117 passed**（较正文 96 新增：基线双层与 enforce 门槛、preflight 注释工具、多 proband 规则修正等）。
- **仍不证明**：从原始读段组装（酵母环输入为已发表组装）、多倍体/分相交付、长读路线；ETP 蛋白环因 GeneMark-ETP git 版缺陷降级 ET 模式，如实记录。