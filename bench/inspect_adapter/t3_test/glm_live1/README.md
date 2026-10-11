# T3 GLM 原生 Inspect 运行

当前状态：首轮因强制思考与关闭思考合同不相容而停止，0份合法QC决定，不能做质量比较。见[兼容诊断](COMPATIBILITY_FAILURE.md)、[保留全分母的报告](REPORT.md)及[阶段汇报](PHASE_REPORT.md)。旧实现/授权保持冻结，不自动重新启动。

2026-10-11 用户授权：“完成 GLM 运行前的预算保护和离线调用检查后，你直接运行即可，不需要我同意”。[APPROVAL.json](APPROVAL.json)及[FROZEN.json](FROZEN.json)封存本轮授权、实现和计划，金标准仍为上级目录已确认的14题。

配置：SiliconFlow `zai-org/GLM-5.3-Flash`，本地环境变量 `SILICONFLOW_API_KEY`，14题×inline/tools×三次=84槽位，串行调用。请求前累计预留：最多294请求、150万输入代理token、279,552输出申请token；单请求≤80,000字节。输入代理不是供应商tokenizer或金额硬上限，按价格快照参考约¥1.98，实际以平台账单为准。

每道工具题最多5轮收集，每轮512输出token，之后关闭工具单独提交2048 token JSON。message_limit=None，turn_limit=6，480秒样本上限；所有SDK/Inspect/格式自动重试为0。预算、HTTP错误、传输失败、返回模型不符或意外推理用量会阻止后续物理请求；不改参数或自动换模型。一份授权只能claim一次，失败也不清除运行锁，不自动补跑。

[FIXTURE_RECEIPT.json](FIXTURE_RECEIPT.json)记录完整84槽位、294次离线OpenAI协议请求、1,050条实际Python工具回复和84合法最终JSON；最大生成轮数使用短回复，不代表最大可能回复体积。另一次长回复压力fixture在280次预留、输入代理1,493,992时拦截下一请求，保留84槽位及3条执行错误；这是保护检查，不是模型质量成绩，不扩大预算。所有fixture外部请求为0。

正常调用日志、脱敏原始响应、逐请求SHA/输入代理/输出申请/模型ID/usage/耗时和原生Inspect日志写在忽略目录 `bench/inspect_adapter/work/t3_glm_live/<run_id>/`。Inspect日志会含评分target，作为私有审计资料，不能再次作为模型输入。模型只接收冻结公共文件、共同提示/schema；五个原生只读工具没有答案判定能力。真实密钥仅进程环境读取，不写文件、日志或服务器。

主报告按题：三次中至少两次完整可接受决定匹配，错误/缺失不丢分母；逐字段与观测层成绩另列，七个来源/同源题对分别报告。自动schema/引用位置检查不等于证据语义或行动安全认可。此研究比较信息访问方式，不含Skill条件，不做旧H1–H3检验。

本地命令：

```powershell
bench/inspect_adapter/.venv/Scripts/python.exe -m bench.inspect_adapter.t3_live api
```

供应商对当前模型的thinking/JSON/tools实际兼容在第一批已计预算的真实请求核对；不发送额外试探或失败重试。
