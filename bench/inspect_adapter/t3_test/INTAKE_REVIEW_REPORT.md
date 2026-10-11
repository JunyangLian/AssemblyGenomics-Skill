# T3 Linux验收与AI审核阶段汇报

2026-10-11。只进行回传验收、离线核查和已授权AI审核；没有评测API调用、答案冻结或候选决定修改。

1. **完成文件**：t3_intake.py及验收测试；LINUX_REPRODUCTION.json；t3_review.py、reviews内独立原稿/原字节zip/事后COMPARISON及测试；GUIDANCE_SCOPE.json、官方PRICE_SNAPSHOT.draft.json；公共system和PLAN.draft升级为draft-2，刷新原生MOCK_RECEIPT；README、导航和[冻结审核摘要](APPROVAL_REVIEW.md)。全部改动在bench下。
2. **pytest**：完整 `python -m pytest -q`，467 passed，9条第三方弃用警告，264.27秒。既有测试及新增传输损坏、版本错位、自洽篡改答案、AI审核身份/原稿字节保护均通过。最终28条native mock/350工具回复通过，零供应商调用；不是质量成绩。
3. **待决定事项**：请用户确认14份候选答案，允许新版本冻结。真实评测预算仍未批准，后续先完成物理请求防护/离线协议核验再执行已批准范围；不自动消耗旧额度。服务器未记录jsonschema准确版本；评审确切供应商模型ID不可用，照实保留，不要求重传或补造记录。

## 回传验证

回传暂存目录为bench/v4/incoming/inspect_t3_cases_reproduction/bundle。运输manifest的85个payload完整，其中14题84文件与Windows参考逐字节一致；服务器构建器、私有真实子集、参考case manifest三项SHA亦一致。Linux记录Python 3.9.23，内核6.8.0-106-generic；平台字段是服务器记录，本地确认的是内容与版本绑定。

运输manifest SHA：acc726f070825014a891f01adc1626dc591f2e89004e6c4faa3f6b621fd2d49d。题库manifest保持661664a3e60b7b1ab56f9ec35e80cb1b07a5d5519805018831680486633065b5。没有再次扫描原始GFF/FAA。

## AI审核与合同修订

未参与构题的fork_none子agent仅收到14个匿名公共题包和共享schema/system。它自行解析全部记录、计算计数和引用关系，14份独立决定与作者候选均一致：7 pass、7 block。原稿、独立检查脚本和结果按原字节封存，LF阅读副本另存，作者完成后才读取匿名映射并对照。

这不是真人专家验证、跨模型独立性或模型性能测量；访问约束不是OS强制隔离。上游历史原因、错误字段的权威修复方向仍不能由公开文件确定。独立评审没有得到gold，也没有按作者答案重写。

评审指出Parent ID不匹配可被泛化为id_mismatch。运行前公共合同draft-2明确：id_mismatch为跨文件连接键问题，gff_hierarchy_error为单个GFF内部引用/层级问题。该一般定义对两条件和全部题一致，不带具体题答案；十四题输入/expected/meta与AI旧稿不改，服务器复现结果仍适用。它是测试前类别边界修订，不是看了评测成绩后改gold。

新研究不注入Skill，不使用旧H1–H3或Skill暴露分层。GUIDANCE_SCOPE侧文件将此轴明确记为不适用，保留原meta的unassigned以保持已复现字节；不把它解释成not_exposed。

## 尚未批准的真实设计

14题×inline/tools×3次，共84槽位，主单位为题级完整决定匹配至少2/3；观测与7来源/7对分别报告，失败不缩分母。最多294物理请求、输入代理150万、输出申请279,552，温度0、关闭思考和自动重试；模型草案沿用SiliconFlow deepseek-ai/DeepSeek-V4-Flash。公共合同修订后初始正文代理均值4,944.2，工具索引1,711.3，工具声明和累计回复另计。

2026-10-11[官方价格](https://siliconflow.cn/pricing)及[分时公告](https://docs.siliconflow.cn/docs/release-notes/overview)复核：高峰无缓存输入¥3/百万token、输出¥9/百万token，按代理预算计算参考¥7.015968；凌晨2–8点参考半价。不按代理数字保证实际账单或硬金额上限，不自动改供应商/型号，没有付费探测当前模型身份。批准前不会使用这个预算。
