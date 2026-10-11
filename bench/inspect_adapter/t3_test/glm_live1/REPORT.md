# T3 GLM 七来源测试

**本轮是协议兼容失败，0份有效QC决定。下表零分属于端到端运行失败，不能解释为GLM基因组QC能力差或工具访问无效。**

2026-10-11。原生 Inspect、冻结14题、inline/tools两条件、每题三次。

运行 `20261011T042202437916Z_glm_ccde308e438a`，模型 `zai-org/GLM-5.3-Flash`。HTTP预留 43/294，输入代理 231,593/1,500,000，输出申请 86,528/279,552。

HTTP状态：{'200': 43}；停止原因：unexpected_reasoning_usage。自动重试0，未补跑、未改答案。

收到 43 份usage，输入 254,230、输出 86,235、合计 340,465 token。按无缓存价格快照参考¥0.4448，不是账单；无usage请求的成本未知。

## 按题的主结果

联合正确要求三次中至少两次完整可接受决定匹配，不能从不同错误答案拼接verdict/缺陷/根因。失败和缺失保留分母。

| 条件 | 判定正确 | 观测缺陷正确 | 文件级根因正确 | 联合正确 | 同源题对成功 |
|---|---|---|---|---|---|
| inline | 0/14 (0.0%) | 0/14 (0.0%) | 0/14 (0.0%) | 0/14 (0.0%) | 0/7 (0.0%) |
| tools | 0/14 (0.0%) | 0/14 (0.0%) | 0/14 (0.0%) | 0/14 (0.0%) | 0/7 (0.0%) |

| 条件 | 故障检出（题） | 正常误报（题） | 判定不一致 | 重复不完整 |
|---|---|---|---|---|
| inline | 0/7 (0.0%) | 0/7 (0.0%) | 0/14 (0.0%) | 14/14 (100.0%) |
| tools | 0/7 (0.0%) | 0/7 (0.0%) | 0/14 (0.0%) | 14/14 (100.0%) |

检出只统计合法非pass决定，错误/缺失不算检出。误报只统计正常题的合法非pass决定；格式/执行错误另列，不能由低误报推导可用性。判定不一致使用合法重复，重复不完整单列。

## 次要结果与来源拆分

| 条件 | 合法输出 | 联合正确观测 | 实际工具回复 / 工具错误 | 状态 |
|---|---|---|---|---|
| inline | 0/42 (0.0%) | 0/42 (0.0%) | 0 / 0 | {'parse_error': 42} |
| tools | 0/42 (0.0%) | 0/42 (0.0%) | 0 / 0 | {'execution_error': 42} |

| 条件 | 故障检出（观测） | 正常误报（观测） |
|---|---|---|
| inline | 0/21 (0.0%) | 0/21 (0.0%) |
| tools | 0/21 (0.0%) | 0/21 (0.0%) |

| 来源组 | inline 联合正确 | tools 联合正确 |
|---|---|---|
| GCF_001040885.1 | 0/2 (0.0%) | 0/2 (0.0%) |
| GCF_004115215.2 | 0/2 (0.0%) | 0/2 (0.0%) |
| GCF_016699485.2 | 0/2 (0.0%) | 0/2 (0.0%) |
| GCF_036370985.1 | 0/2 (0.0%) | 0/2 (0.0%) |
| GCF_054855325.1 | 0/2 (0.0%) | 0/2 (0.0%) |
| GCF_943734735.2 | 0/2 (0.0%) | 0/2 (0.0%) |
| GCF_960531495.2 | 0/2 (0.0%) | 0/2 (0.0%) |

| 条件 | 平均实际输入 token / 已有usage请求 | 平均输入代理 / 请求 | 累计输入代理 |
|---|---|---|---|
| inline | 6010.142857142857 | 5450.285714285715 | 228,912 |
| tools | 1804.0 | 2681.0 | 2,681 |

工具条件可能多轮读取；每次请求平均与每题累计成本不是同一单位，不把访问方式效果归因于Skill。

## 逐题输出

保留全部观测，包括错误/缺失。下表引用模型原文；证据语义和action安全尚未独立复核。

| 题 / 条件 / 重复 | 状态 | 模型决定 | 冻结决定 | 引用证据 | action |
|---|---|---|---|---|---|
| t3_001 / inline / 1 | parse_error | —/—/— | pass/none/none |  | None |
| t3_001 / inline / 2 | parse_error | —/—/— | pass/none/none |  | None |
| t3_001 / inline / 3 | parse_error | —/—/— | pass/none/none |  | None |
| t3_002 / inline / 1 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_002 / inline / 2 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_002 / inline / 3 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_003 / inline / 1 | parse_error | —/—/— | pass/none/none |  | None |
| t3_003 / inline / 2 | parse_error | —/—/— | pass/none/none |  | None |
| t3_003 / inline / 3 | parse_error | —/—/— | pass/none/none |  | None |
| t3_004 / inline / 1 | parse_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | None |
| t3_004 / inline / 2 | parse_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | None |
| t3_004 / inline / 3 | parse_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | None |
| t3_005 / inline / 1 | parse_error | —/—/— | pass/none/none |  | None |
| t3_005 / inline / 2 | parse_error | —/—/— | pass/none/none |  | None |
| t3_005 / inline / 3 | parse_error | —/—/— | pass/none/none |  | None |
| t3_006 / inline / 1 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_006 / inline / 2 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_006 / inline / 3 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_007 / inline / 1 | parse_error | —/—/— | pass/none/none |  | None |
| t3_007 / inline / 2 | parse_error | —/—/— | pass/none/none |  | None |
| t3_007 / inline / 3 | parse_error | —/—/— | pass/none/none |  | None |
| t3_008 / inline / 1 | parse_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | None |
| t3_008 / inline / 2 | parse_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | None |
| t3_008 / inline / 3 | parse_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | None |
| t3_009 / inline / 1 | parse_error | —/—/— | pass/none/none |  | None |
| t3_009 / inline / 2 | parse_error | —/—/— | pass/none/none |  | None |
| t3_009 / inline / 3 | parse_error | —/—/— | pass/none/none |  | None |
| t3_010 / inline / 1 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_010 / inline / 2 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_010 / inline / 3 | parse_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | None |
| t3_011 / inline / 1 | parse_error | —/—/— | pass/none/none |  | None |
| t3_011 / inline / 2 | parse_error | —/—/— | pass/none/none |  | None |
| t3_011 / inline / 3 | parse_error | —/—/— | pass/none/none |  | None |
| t3_012 / inline / 1 | parse_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | None |
| t3_012 / inline / 2 | parse_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | None |
| t3_012 / inline / 3 | parse_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | None |
| t3_013 / inline / 1 | parse_error | —/—/— | pass/none/none |  | None |
| t3_013 / inline / 2 | parse_error | —/—/— | pass/none/none |  | None |
| t3_013 / inline / 3 | parse_error | —/—/— | pass/none/none |  | None |
| t3_014 / inline / 1 | parse_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | None |
| t3_014 / inline / 2 | parse_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | None |
| t3_014 / inline / 3 | parse_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | None |
| t3_001 / tools / 1 | execution_error | —/—/— | pass/none/none |  | ValueError('unexpected_reasoning_usage') |
| t3_001 / tools / 2 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_001 / tools / 3 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_002 / tools / 1 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_002 / tools / 2 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_002 / tools / 3 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_003 / tools / 1 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_003 / tools / 2 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_003 / tools / 3 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_004 / tools / 1 | execution_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_004 / tools / 2 | execution_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_004 / tools / 3 | execution_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_005 / tools / 1 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_005 / tools / 2 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_005 / tools / 3 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_006 / tools / 1 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_006 / tools / 2 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_006 / tools / 3 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_007 / tools / 1 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_007 / tools / 2 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_007 / tools / 3 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_008 / tools / 1 | execution_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_008 / tools / 2 | execution_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_008 / tools / 3 | execution_error | —/—/— | block/gff_reference_unresolved/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_009 / tools / 1 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_009 / tools / 2 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_009 / tools / 3 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_010 / tools / 1 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_010 / tools / 2 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_010 / tools / 3 | execution_error | —/—/— | block/gff_faa_link_missing/id_mismatch |  | ValueError('pilot stopped before further requests') |
| t3_011 / tools / 1 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_011 / tools / 2 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_011 / tools / 3 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_012 / tools / 1 | execution_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_012 / tools / 2 | execution_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_012 / tools / 3 | execution_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_013 / tools / 1 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_013 / tools / 2 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_013 / tools / 3 | execution_error | —/—/— | pass/none/none |  | ValueError('pilot stopped before further requests') |
| t3_014 / tools / 1 | execution_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_014 / tools / 2 | execution_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |
| t3_014 / tools / 3 | execution_error | —/—/— | block/gff_hierarchy_inconsistent/gff_hierarchy_error |  | ValueError('pilot stopped before further requests') |

## 边界

作者候选金标准经匿名AI核查与用户确认，不是独立真人专家盲审。独立来源只有7个，每来源两套小型编码gene块；重复和同源题对不视作独立来源，不能泛化到整基因组注释质量。

允许partial、异构体和多片段；根因只代表公开文件级缺陷，不确证上游历史事故，也不证明某一侧修复方案正确。自动引用存在检查不验证其语义，建议安全和自报危险布尔字段需要单独复核。

没有Skill知识注入，暴露轴不适用，不检验旧H1–H3，不与T1旧合同成绩合并。两条件输入量与工具调用次数不同；readonly函数仅操作运输公开子集，没有shell/网络或可变文件能力。

API错误、超预算或缺失槽位保留，不能以剩余额度自动补跑。真实用量与输入代理不同，无缓存费用参考不等于实际账单。
