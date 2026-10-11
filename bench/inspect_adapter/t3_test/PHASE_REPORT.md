# T3准备阶段汇报

本文件保留首轮准备阶段记录；2026-10-11后续Linux验收和AI审核状态见[验收与审核汇报](INTAKE_REVIEW_REPORT.md)。

2026-10-11。用户“可以”批准继续准备；本阶段没有模型费用，没有改变旧冻结答案/提示/统计。

1. **完成内容**：新增t3_packets.py、t3_task.py；14套cases（task、3个artifacts、meta、expected）、三份独立schema副本、私有真实SOURCE_SUBSETS、审核表、CASE_MANIFEST/VALIDATION、共用system/final、PLAN.draft、原生MOCK_RECEIPT、服务器reproduce_cases.py、小型reproduction_package.zip及Windows/PACKAGE回执。说明与导航同步更新在bench下。
2. **测试**：完整 `python -m pytest -q` 在Inspect虚拟环境中459 passed in277.26s；随后新增预算草稿保护检查，最终T3专项11 passed in10.22s。Inspect/tenacity的9条参数弃用警告不影响通过。真实旧脚本行为和449个既有测试全部通过。Windows分发包实际重建14题84文件、0差异；两次打包相同SHA。28条原生mock完成350工具回复、98次模拟生成，另3次模拟生成验证旧上限提前结束；0供应商调用。
3. **缺口与下一步**：Linux复现待用户执行包中脚本并回传固定bundle；候选答案待审核，独立专家真人盲审没有发生。guidance字段保留unassigned，冻结前登记口径；当前只比较信息访问条件，不做H1–H3。按顺序验收Linux → 审核候选答案 → 冻结新版本 → 刷新模型价格并批准新预算 → 真实运行。不自动消耗T1剩余额度。

题型分配为7正常、3protein_id不能接续、2Parent不能接续、2父子区间不满足；拟定变体均block，正常pass。消费者范围只允许判断可见文件连接/层级，不能推测原历史注释过程或全基因组生物学质量。算法先按完整闭包与规模筛选真实块，会造成选样偏好；没有按模型成绩筛选。

候选真实设计84槽位（14×2×3）、最多294请求、输入代理150万、输出申请279,552；初始输入均值正文4,855.1、工具索引1,622.1代理token，后续工具声明/回复另算。这些是未批准预算，不是实际调用数；费用未知，待价格复核。质量成绩目前不存在，不能把mock通过写成新来源准确率。

服务器命令与回传目录见[README](README.md#服务器复现与下一步)。所有候选答案及版本身份见[审核表](REVIEW_SHEET.csv)，可以在Linux复现时同步审核。
