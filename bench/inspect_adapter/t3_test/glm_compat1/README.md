# 待确认的 GLM 思考兼容性试跑

这份草案不授权API。上一轮关闭思考合同与GLM-5.3-FLASH强制思考不相容，0份合法QC决定；旧失败记录和已冻结答案保持原状。

可审核方案见PLAN.draft.json：同一模型、接口、环境变量密钥，冻结t3_001正常/t3_002蛋白ID故障×inline/tools各一次，共4槽位；只测试原生Inspect推理重放、工具和最终JSON兼容，不把开发样例作为新质量成绩。公共题面/产物/schema与gold都不改。

申请改变运行条件：enable_thinking=true，reasoning_effort=low，thinking_budget=2048；最多5轮收集，每轮max_tokens=2048，最终max_tokens=8192。每次预留max_tokens+thinking_budget；14请求、10万输入代理、81,920总输出申请，参考新增¥0.31。与已消费43请求、231,593输入代理、86,528输出申请合并，最多57请求、331,593输入代理、168,448输出申请；不增加原累计上限。

Z.AI原生接口支持低强度，但SiliconFlow对此型号路由的实际支持尚未验证。首批请求若4xx、空最终content、型号漂移、超预留用量或预算失败立即停止，不自动尝试其它参数、换模型或补跑。新版响应策略显式检查reasoning_content，不能仅依赖usage明细。

当前仅规格与响应保护已准备，完整新版调用适配及原生离线fixture仍待完成；完成之前不调用、不冻结API授权。此文档不是声称已经完成新协议验证。
