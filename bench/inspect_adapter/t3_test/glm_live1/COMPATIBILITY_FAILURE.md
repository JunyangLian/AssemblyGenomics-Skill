# GLM 首轮协议兼容失败

2026-10-11。授权运行 `20261011T042202437916Z_glm_ccde308e438a` 已停止，没有自动续跑或重置预算。

实际43次请求均HTTP200，返回型号均为zai-org/GLM-5.3-Flash。正文42条全为finish_reason=length，content为空而reasoning_content非空；首条工具收集返回tool_calls，同时明确报告134 reasoning tokens，触发旧保护unexpected_reasoning_usage。正文42槽位记parse_error；工具42槽位记execution_error（只有首条实际发出，其余被停止保护拦住）。全部84槽位与原分母保留，0份合法QC决定。

这是协议失败，不能以0/14或0/84声称模型QC能力差、工具无效或根因不能识别。冻结答案和公开合同未改。详细计数在REPORT.md、RESULTS_PUBLIC.json，原始响应及Inspect日志仍在私有work目录，RUN_RECEIPT.json登记其SHA。

收到usage：输入254,230、输出86,235、合计340,465 token。按现有无缓存快照参考¥0.444842，实际账单可能有缓存折扣。HTTP预留43/294、输入代理231,593/1,500,000、输出申请86,528/279,552，均未超原上限。新运行47个审计文件的密钥格式扫描0匹配，不作为所有敏感信息的普遍保证。

适配缺陷在运行者：沿用DeepSeek enable_thinking=false，未先按GLM官方强制思考合同调整；响应保护只看usage的reasoning_tokens，在正文响应未提供该字段时遗漏reasoning_content，没有在首条响应停止。HTTP200与模型ID一致不证明思考/JSON参数生效。旧实现已冻结，保持字节不变供审计；新response_policy.py单独覆盖推理字段非空、usage缺失/零、最终content空等条件，未追改旧错误或分数。

[Z.AI官方思考说明](https://docs.z.ai/guides/capabilities/thinking-mode)及[Deep Thinking参数](https://docs.z.ai/guides/capabilities/thinking)明确GLM-5.3-FLASH不能关闭思考，支持low/high/max强度。SiliconFlow实际路由仍须兼容性验证；[其通用接口](https://docs.siliconflow.cn/docs/api/chat-completions-post)的“多数模型”参数不能据此推断此型号的具体支持。

下一步建议：另起glm_compat1，用同一冻结正常/ID故障题各一次inline/tools，共4槽位，只测协议；启用思考、尝试low强度，收集上限2048、最终上限8192，额外思考预算2048；每次按max_tokens+thinking_budget预留，最多14请求、10万输入代理、81,920输出总预留。新增费用参考约¥0.31；与本轮合计上限仍低于原累计294/150万/279,552。旧84失败槽位不替换，此小试跑不报告模型质量或泛化成绩。

该方案改变已冻结的思考和输出条件，需要单独确认；不从旧授权自动推导新模式，也不静默增加累计预算。计划草案见../glm_compat1/PLAN.draft.json。
