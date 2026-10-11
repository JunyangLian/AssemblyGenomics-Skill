# AssemblyGenomics × Inspect AI：离线接入

本目录是第一条完整接入链路：公开题面 → Inspect Dataset → 离线 replay Solver → 领域 Scorer → Inspect 日志 → 旧评分一致性核验。使用 Inspect AI 0.3.277；v1/v2 的题目、答案、提示和评分器不改动。

当前统一入口见 [交付导航](DELIVERY.md)、[无密钥复现与学习](REPRODUCE.md)，完成范围及求职表述见 [PROJECT_STATUS.md](PROJECT_STATUS.md)，面试讲解见 [INTERVIEW.md](INTERVIEW.md)。

2026-10-10 用户批准进一步覆盖已有T1题目：新增 [T1工具回归准备](t1_regression/README.md)，20候选中19题适合原只读工具，两个条件×三次重复的114条mock观测通过；尚无新API调用或新质量成绩。回归不标成held-out，T3七新来源另行测试。

2026-10-10 按用户最新要求，学习主线改为 [复现官方原始示例，再接入生信](official/README.md)。先运行固定版本、未修改的官方 Task/工具/评分器，再与现有领域 Task 并排对照；旧题审计归档，不继续作为扩展主线。已完成官方12样本真实小规模复现：两工具任务2/2、Theory of Mind官方同模型评分9/10，两轮累计26次请求；失败与预算内恢复保留。见 [真实结果与简历判断](official/REPORT.md)，本轮不继续100题。

## 从这里开始学

先运行 `example.py`：一个明确标为教学用途的样例，使用 Inspect 的 `Sample`、`generate()`、`match()` 和本地 mock。它不属于真实来源题库。随后运行 `replay.py`，观察同样的链路如何接入真实历史观测。

在仓库根目录执行（Windows PowerShell）：

```powershell
python -m venv bench/inspect_adapter/.venv
bench/inspect_adapter/.venv/Scripts/python.exe -m pip install --index-url https://pypi.org/simple -r bench/inspect_adapter/requirements.lock.txt
bench/inspect_adapter/.venv/Scripts/python.exe -m bench.inspect_adapter.example
bench/inspect_adapter/.venv/Scripts/python.exe -m bench.inspect_adapter.replay
```

Linux 对应使用 `.venv/bin/python`。本轮已实际验证 Windows Python 3.10.1；Linux 尚未运行本适配。依赖锁来自本轮 Windows 环境，其他平台可能需要按 `requirements.txt` 解析并登记自己的锁文件。

| 组件 | 本项目里做什么 | 阅读位置 |
|---|---|---|
| Dataset / Sample | 保存原公开消息、题号与重复编号；答案只作为评分 target | `bridge.py:make_task` |
| Solver | 从归档取出最后一次已解析回答，写入 `state.output`；不调用 generate | `bridge.py:replay_final_observation` |
| Scorer | 严格校验回答，再计算判定、根因、共同成功和有效输出四项 | `bridge.py:genomic_qc_labels` |
| Log | 保存输入、回放输出、评分与历史状态，供查看和追溯 | `work/v2_replay/logs/` |
| 汇总核验 | 从 Inspect 日志重新取出回答，调用原 v2 汇总函数并与归档比较 | `replay.py:verify_parity` |

框架使用资料：[任务](https://inspect.aisi.org.uk/tasks.html)、[自定义评分器](https://inspect.aisi.org.uk/custom-scorers.html)、[评分工作流](https://inspect.aisi.org.uk/scoring-workflow.html)。本例的组件布局参考这些官方接口，未声称复制了一个完整官方 benchmark。

## 怎么判断迁移成功

来源固定为 `bench/v2/reports/v2-run-10_four-models_human-reviewed/results.json`，按其发布 manifest 校验报告身份，并核对冻结答案；不重扫原始基因组源文件。

- 24 道历史题、四个保留模型的 B/C2、A 规则组，共 648 条最终观测全部进入 Inspect。
- API 错误、解析错误、中断和规则未覆盖均保留，不能从分母中删除或补写 pass。
- 逐观测 Scorer、216 个组×题结果、全部分层面板、跨层配对、人类 action 编码诊断和逐模型假设结果都要一致；任何不一致直接失败。
- 每题三次重复依然按原 v2 的两个独立多数值处理：verdict 和 root 各至少 2/3。Inspect 的样本平均值只展示观测层指标，不能代替题层结果，也不能把重复看成独立题。

输出为 `work/v2_replay/PARITY.json` 和真实 Inspect 日志。Inspect 初始汇总混合了这些模型和组，仅用于检查观测级链路；比较模型请阅读原报告的分组面板，不能把混合均值当成模型准确率。日志含评分 target / 标准答案，属于分析产物，不能再作为模型输入。日志、虚拟环境与工作目录不提交。

2026-10-11补充：[19题T1真实回归](t1_regression/live1/REPORT.md)已完成114条观测，既有题库通过Inspect原生正文/工具两条件执行；[失败解释](t1_regression/live1/ERROR_NOTES.md)区分旧标签匹配、处置分歧及三条消息上限终止。未混入历史B/C或H1–H3。

随后准备[T3七来源14题草稿](t3_test/README.md)：真实完整特征块和蛋白、确定性连接/Parent/区间变体，28条原生mock和跨平台复现通过；取消旧16消息上限并用生成轮数控制。答案仍待用户确认，新真实预算尚未批准，没有T3模型质量结果。

后续[Linux验收与匿名AI审核](t3_test/INTAKE_REVIEW_REPORT.md)已完成：14题84文件跨平台一致，AI决定与候选14/14一致。运行前公共合同draft-2明确跨文件ID与GFF内部层级类别，原题/答案字节及独立稿不改；用户答案确认、冻结与真实调用批准仍未完成。

## 目前完成到哪里

已完成离线组件示例、归档最终解析结果回放、评分一致性核验、AI 开发题盲审、四题原生工具循环的只读 mock 原型，以及批准后的两次 SiliconFlow 四题真实开发试跑。第一次真实模型进行了 29 次工具调用，四题最终输出都未通过冻结的 JSON 格式要求，严格计分为 0/4；详见 [首次报告](PILOT_REPORT.md) 和 [运行摘要](PILOT_RECEIPT.json)。第二次使用分阶段输出，格式 4/4、决定联合匹配 3/4，仍有引用与行动问题，详见 [第二次报告](pilot2/REPORT.md)。首次代理失败和恢复、两次开发试跑分别保留。尚未实现新的在线 B/C 比较、原规则的 Inspect 在线执行或新测试集评测。

这次回放的输入是**最后一次已解析观测**，不会重新解析原 HTTP 原文，也不会恢复供应商思考内容、重试轨迹、耗时和 token 信息。这些仍以原始日志和报告为准。Inspect 的原生 `inspect score` 处理 Inspect 日志，不能直接读取我们原来的 JSONL，因此本目录显式提供回放适配。

汇总复用原评分函数，证明的是适配未改变旧口径，不能宣称获得独立评分实现或新的模型性能证据。历史真人 action 编码仍为历史真人编码；本轮 agent 的四题审核明确标为 AI，见 `reviews/`。v3 标准答案未自动改成“已批准”或“真人已审核”。

## 下一步的收敛范围

四道开发题已接入不可变公开字节的只读工具，不提供任意 shell，也不是容器沙箱。先用 `TOOL_LESSON.md` 学懂工具循环。后续真实模型小试验需固定答案和条件，以及模型、参数、调用和 token 上限；不立即重跑六个模型或扩大题库。

后续决策与审核身份规则见 `WORKFLOW.md`；离线回放验证记录见 `VALIDATION.md`，当前试跑准备验证见 `PILOT_VALIDATION.md`。

第一轮真实结果之后的改进方案见 [pilot 2](pilot2/README.md)：共同工具指导、限定证据收集回合、关闭工具后请求 JSON object 最终输出。原答案与严格评分保持一致，独立版本明确登记开发调优。经批准实际完成 16 次请求和 25 次工具调用，格式 4/4、决定联合匹配 3/4；仍有证据引用错误，证据语义/action 不自动算通过。详见 [第二次真实报告](pilot2/REPORT.md)。这是同四题的开发调试，没有独立 held-out 或新在线 B/C 比较。

随后完成 [离线证据与行动诊断](audit/pilot2/README.md)：保存四条原回答、24 条引用及 10 次实际计算摘录，无密钥核验身份与算术；作者 AI 逐条记录引用错位/范围不足和复核条件缺陷。正式分数与审核身份不改，本目录不作为模型输入。
