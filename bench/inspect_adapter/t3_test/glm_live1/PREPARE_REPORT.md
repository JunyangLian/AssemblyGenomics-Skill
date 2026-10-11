# GLM 运行前检查

2026-10-11 用户明确批准检查通过后直接运行；授权原话、累计预算和运行实现已封存，不再次征询确认。

完成文件：t3_live.py、tests/test_t3_live.py、glm_live1下PLAN.draft/json、IMPLEMENTATION.draft.json、FIXTURE_RECEIPT.json、APPROVAL.json、FROZEN.md/json、README及本报告。原T3金标准与公共合同全部保持冻结字节。

完整pytest：486 passed，9个Inspect/tenacity弃用警告，267.83秒；新增15项专项全部通过。git差异检查及LF校验通过。本检查阶段外部API调用0。

原生OpenAI wire fixture覆盖84槽位、294模拟物理预留、1,050实际Python工具回复、84合法最终JSON。调用仅使用公开题目，不读取target生成回答；脚本恒定答案不算模型质量成绩。长回复压力fixture累计280次预留后拦截下一请求，输入代理1,493,992，保留84槽位和3执行错误，证明上限生效；最大token保护可能导致真实槽位未完成，不自动加额。

适配时发现Task.name只读、eval_async不接收display；均在离线阶段修复，最初初始化失败为0请求。Windows控制面AF_UNIX警告仅影响Inspect控制界面，离线原生日志与评分正常；没有改第三方库或旧版本行为。

本轮按一次性运行锁执行GLM-5.3-Flash，84槽位、294请求/150万输入代理/279,552输出申请上限，关闭推理和自动重试。预算/HTTP错误/传输失败/型号或推理用量不符停止后续请求。供应商实际参数兼容尚待第一批已计预算请求核对，无额外付费探测。

密钥只临时进入本地执行进程环境，不写文件或持久配置、不上传服务器；原响应在Inspect处理前脱敏。费用参考约¥1.98，实际以账单为准。真实结果后续单独登记；不把此离线测试当作GLM正确率或真人专家审核。
