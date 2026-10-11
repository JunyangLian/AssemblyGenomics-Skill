# GLM 真实运行与兼容诊断阶段汇报

2026-10-11。

1. 完成：用户授权后用冻结实现执行GLM，保留全部84槽位；新增t3_report.py及测试、REPORT.md、RESULTS_PUBLIC.json、RUN_RECEIPT.json、COMPATIBILITY_DIAGNOSIS.json、COMPATIBILITY_FAILURE.md、LOCAL_LOG_AUDIT.json及本报告。response_policy.py和其测试单独修复未来版本响应检查，不改历史冻结代码。glm_compat1/PLAN.draft.json与README提出下一版小型兼容检查，未授权、未调用。
2. pytest：运行前486 passed/267.83秒；初版报告后487 passed/276.68秒；新增响应保护后最终490 passed/262.20秒，9个第三方弃用警告。新响应保护及报告专项4/4通过，所有既有测试通过。
3. 真实结果：43 HTTP200，42正文length且最终content空，仅推理；首条工具请求报告推理tokens，停止后续请求。42 parse_error +42 execution_error，0合法QC决定。原分母保留，但这是协议失败，不能解释为模型QC能力差或工具效果差。
4. 成本与安全：实收输入254,230/输出86,235/合计340,465 token，快照无缓存参考¥0.444842；预留43请求、231,593输入代理、86,528输出申请。47份私有审计文件密钥格式扫描0匹配；密钥只临时进入本地执行环境，无新API调用或自动补跑。
5. 缺口与建议：GLM-5.3-FLASH官方强制思考，原关闭思考配置不相容；旧usage-only保护遗漏正文reasoning_content。新保护已离线验证。建议另版4槽位、14请求/10万输入代理/81,920总输出申请、启用思考/low、最终8192token；新增参考¥0.31，仍不增加原累计上限。由于思考和输出条件改变，按WORKFLOW关键步骤待用户确认；新版原生适配与离线检查完成前不调用。

该阶段没有修改任何expected、公开题面、原冻结规则或旧模型分数。下一版不能覆写本轮失败，不能将开发协议检查包装为独立专家验证或质量成绩。
