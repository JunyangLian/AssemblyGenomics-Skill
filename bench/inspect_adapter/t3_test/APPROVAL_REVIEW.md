# 待确认的14题答案

2026-10-11。真实T3小子集与确定性格式变体，Windows/Linux84文件复现一致，匿名AI审核14/14决定一致；未获用户批准、未冻结，没有真实评测模型结果。

| 题号 | 候选verdict | 候选observed_defect | 候选root_cause | 审核依据 |
|---|---|---|---|---|
| t3_001、003、005、007、009、011、013 | pass | none | none | 完整Parent/区间合同满足；不同protein_id与FAA首token精确接续；多片段/partial/异构体允许 |
| t3_002、006、010 | block | gff_faa_link_missing | id_mismatch | GFF的CDS protein_id无法精确找到本题FAA序列；不能以Name或CDS ID兜底 |
| t3_004、008 | block | gff_reference_unresolved | gff_hierarchy_error | 完整特征块内mRNA的Parent没有对应gene |
| t3_012、014 | block | gff_hierarchy_inconsistent | gff_hierarchy_error | 一个CDS区间越过其mRNA父区间 |

题目审核待启动输入，无已完成的结果或旧版恢复任务，变体用block。原因只确认文件级问题，不推测上游历史事故；权威修复哪一侧需补可信来源。普通字面计数在成对题中一致，不能替代连接核验。

逐题来源、关键证据及候选标签见[审核表](REVIEW_SHEET.csv)，完整expected见cases目录。[AI原稿与对照](reviews/COMPARISON.json)保留模型来源、隔离边界和不确定性，不记为真人盲审。

拟确认范围：上述14份expected候选决定及既有关键证据，配套公开输入、draft-2公共类别定义和七字段schema；确认后登记人类授权并冻结SHA。此确认不授予新付费预算，真实运行另按PLAN中的明确上限确认。
