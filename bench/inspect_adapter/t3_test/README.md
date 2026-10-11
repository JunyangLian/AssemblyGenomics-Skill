# T3 七来源 Inspect 测试

## 当前状态：答案已冻结

2026-10-11 用户确认14份答案并允许冻结；[FROZEN.md](FROZEN.md)逐题登记expected SHA-256，[FROZEN.json](FROZEN.json)封存84个题目文件、公共提示/schema及验收依据。题目内draft/pending和历史凭据中的false是生成时状态，保留复现字节；当前授权以[APPROVAL.json](APPROVAL.json)为准。此授权不包含付费调用。

用户随后指定改用 GLM-5.3-Flash，完整API ID为 `zai-org/GLM-5.3-Flash`，base_url沿用 `https://api.siliconflow.cn/v1`，密钥只读 `SILICONFLOW_API_KEY`。后续计划见[NEXT_RUN.draft.json](NEXT_RUN.draft.json)；下文及PLAN.draft/价格快照是之前DeepSeek准备阶段的历史记录，不作为当前运行配置。新运行还需物理预算保护与模型参数兼容验证，未发送真实请求。

新草案保持14题×两条件×三次=84条观测，最多294请求、150万输入代理token、279,552输出申请token。[官方价格](https://siliconflow.cn/pricing)列出该GLM无缓存输入¥0.80/百万、输出¥2.80/百万；按上述代理/申请额度参考约¥1.98，非实际账单或金额硬上限。[新价格快照](PRICE_GLM.draft.json)与历史DeepSeek快照分别保存。思考开关、JSON格式及工具调用参数尚未经过供应商真实请求验证，不从其它模型的成功结果推断兼容。

冻结后不要执行build或prepare覆盖文件；可运行 `bench/inspect_adapter/.venv/Scripts/python.exe -m bench.inspect_adapter.t3_freeze --verify`。若修改答案或公开合同，须新建版本而非覆盖本冻结。

以下为冻结前准备记录。

2026-10-11。14题、7个同源题对，Windows/Linux复现均已验收，上下文隔离AI审核完成；答案未获用户批准、未冻结，没有真实评测模型结果。当前公共类别合同为draft-2，详见[验收与审核汇报](INTAKE_REVIEW_REPORT.md)。沿用已验收的 `bench/v3/SOURCE_RECEIPT.json`，只读取其中七套T3 GFF/FAA；没有重跑注释或引入其它本地物种。不是旧v3 28题计划的自动替代。

| 来源 | 正常题 / 变体 | 唯一改变 | 原始特征行 / 蛋白条数 |
|---|---|---|---|
| Arxiozyma heterogenica，GCF_036370985.1 | t3_001 / t3_002 | 一个CDS所有片段的protein_id版本后缀 | 12 / 2 |
| Strongyloides ratti，GCF_001040885.1 | t3_003 / t3_004 | 一条mRNA的Parent | 12 / 2 |
| Anopheles gambiae，GCF_943734735.2 | t3_005 / t3_006 | 一个CDS所有片段的protein_id版本后缀 | 26 / 3 |
| Carica papaya，GCF_054855325.1 | t3_007 / t3_008 | 一条mRNA的Parent | 20 / 2 |
| Ornithorhynchus anatinus，GCF_004115215.2 | t3_009 / t3_010 | 一个CDS所有片段的protein_id版本后缀 | 40 / 3 |
| Gallus gallus，GCF_016699485.2 | t3_011 / t3_012 | 一个CDS片段移到自身mRNA末端之外，片段长度不变 | 41 / 3 |
| Zeus faber，GCF_960531495.2 | t3_013 / t3_014 | 同上 | 22 / 2 |

拟定判定：每对正常题为pass；变体为block。protein_id不能接续为文件级id_mismatch；Parent缺失或父子区间不满足为文件级gff_hierarchy_error。这些只是候选答案，具体证据见各题expected.json及[审核表](REVIEW_SHEET.csv)。作者AI草拟，另一个fork_none子agent匿名公开资料审核14/14决定一致，未改候选答案；不是跨模型独立性、真人专家验证或评测模型正确率。原稿和不确定性保存在[reviews](reviews/COMPARISON.json)。

## 输入合同与来源

每题审核待启动的下游输入，两套完整编码gene块及所有子记录、关联完整FAA蛋白序列。Parent必须接续、类型正确、同seqid/链、子闭区间位于父内；CDS的protein_id必须与FAA首token精确连接。不按Name或CDS ID兜底，不去版本号。允许异构体、多片段CDS和partial=true，不能据此推断全长或生物学质量；真菌和线虫原始块确实含partial=true。

截取算法固定为GFF顺序中前50个满足闭包、大小及多片段条件的候选；保留其中最先能接上完整FAA且总公开材料≤30,000字节的两个块。不是按模型成绩选样，也不是注释产物总体的随机样本。GFF原特征行照录、FAA完整原序列按60字符LF重排；基因数、蛋白数、残基数由子集直接计算，不借用全物种统计。所有格式子集标synthetic=true，不声称生成新生物学数据。

`selection/SOURCE_SUBSETS.json`保存私有原子集及来源绑定；meta保存运输包源路径、原服务器路径、已有SHA-256、选样/变换方式及来源凭据SHA。没有反复重扫完整源哈希。生成和验证核对Parent/区间/连接并进行泄漏扫描；参考核算只用于候选答案校验，不是A组新规则，也不向模型提供决定工具。

同源题对的task、FAA、计数逐字节相同，仅GFF指定字段改变。模型输入只含task、artifacts，以及共用说明/schema；不含题号、pair_id、meta、expected或私有子集。私有标准答案作为Inspect Sample.target仅在评分端使用；原生日志会含target，不能作为未来模型输入。

## Inspect条件与评分草案

inline提供全部公开正文；tools提供任务和公开文件索引，由现有五个只读函数访问不可变公开字节。没有添加GFF缺陷判定工具、shell或网络能力。两条件使用同一新七字段schema及共用处置定义；不包含Skill知识包，不对应历史B/C条件。新任务区分observed_defect与可确证文件级root_cause，不改变T1冻结的六字段口径。

tools最多5次收集生成（每次512输出token），随后关闭工具并单独提交JSON（2048）；最多6次生成，480秒。取消旧message_limit=16，以轮数限制运行；一次生成可产生多条工具回复，消息数不能当生成次数。[Inspect官方限制定义](https://inspect.aisi.org.uk/reference/inspect_ai.util.html)与[工具解析](https://inspect.aisi.org.uk/reference/inspect_ai.solver.html)说明了该区别。原工具输出分页/体积限制仍适用；新真实运行还需独立的物理请求/累计token预算保护。原T1受限失败与分数保留。

主分析单位拟为题：每题3次中至少2次完整匹配某个可接受的verdict/observed_defect/root_cause组合，才算决定共同成功；逐字段正确率和观测层结果另报。解析错误或缺失槽位留在分母中；配对成功需两题都达到题级共同成功。另按7个来源组报告，重复与同源题对不视为独立来源。

严格schema及引用位置存在仅证明格式/定位；自动决定评分不证明证据语义和action安全。这两项需单独人工或明确标注的AI编码复核；自报booleans不作安全保证。新来源不等于模型预训练未见，连接机制也可能在旧指导中相关出现。[GUIDANCE_SCOPE.json](GUIDANCE_SCOPE.json)明确此研究没有Skill条件，旧Skill暴露轴不适用；保留已复现meta中的unassigned字节，不将它当作not_exposed分层。不用于旧H1–H3检验或声称Skill提升。T1与本版合同、schema、来源不同，分开报告。

AI审核指出Parent标识错误可被宽泛理解为id_mismatch。公共system的draft-2在正式评测前统一约定：id_mismatch用于跨文件连接键；gff_hierarchy_error用于GFF内部引用/层级。该定义对两条件、所有题相同，不包含某题答案或注入记录。评审看到的是旧draft-1，独立原稿不重写；14道题的task/artifacts/meta/expected字节不变，不需要重新构题或服务器复现。

## 已做的离线验证

- [VALIDATION.json](VALIDATION.json)：14题schema、来源绑定、引用位置、连接参考事实、泄漏扫描和成对表面一致性通过。
- [MOCK_RECEIPT.json](MOCK_RECEIPT.json)：28条原生模拟观测、98次模拟生成、350条实际Python工具回复，28条最终JSON合法，零供应商调用；脚本回答不读取target，不计作质量成绩。另有3次模拟生成的旧16消息上限负对照，复现最终提交未到达。
- [WINDOWS_REPRODUCTION.json](WINDOWS_REPRODUCTION.json)：实际展开分发包重新生成，14题、84个题目文件哈希一致；重复打包逐字节一致。
- [LINUX_REPRODUCTION.json](LINUX_REPRODUCTION.json)：用户回传Linux/Python 3.9.23包，本地核对85个运输payload与84个题目文件，全部一致；构建器/子集/参考manifest版本也一致。未再次扫描原始大文件。服务器没有记录精确jsonschema版本，保留此记录缺口。
- 上下文隔离AI审核14题，7 pass、7 block，与作者候选14/14一致；匿名复制及访问约束不是操作系统强制隔离，精确评审模型ID不可用，不声称跨模型独立性。未冻结答案，没有真实API入口。

本地命令（无需密钥）：

```powershell
bench/inspect_adapter/.venv/Scripts/python.exe -m bench.inspect_adapter.t3_packets build
bench/inspect_adapter/.venv/Scripts/python.exe -m bench.inspect_adapter.t3_task --prepare
bench/inspect_adapter/.venv/Scripts/python.exe -m bench.inspect_adapter.t3_task --mock
bench/inspect_adapter/.venv/Scripts/python.exe -m pytest -q
```

## 服务器复现与下一步

将[复现包](reproduction_package.zip)传到 `~/AssemblyGenomics-Skill/bench/inspect_t3_reproduction_package.zip`，在服务器执行：

```bash
cd ~/AssemblyGenomics-Skill/bench
python -m zipfile -e inspect_t3_reproduction_package.zip .
python t3_reproduction/reproduce_cases.py
```

脚本只需Python和jsonschema（缺依赖时先用 `python -m pip install jsonschema`）；无需Inspect或API key。重建所有题目，比较参考manifest，固定输出 `bench_transfer/inspect_t3_cases_reproduction/bundle/`，登记Python/平台版本及完整SHA-256清单，可重复执行，不扫描原大文件。请回传该bundle目录。

此复现证明同一运输子集在两端生成相同字节，不是再次验证完整原GFF/FAA提取。当前包含私有候选答案构造逻辑，专用于复现/审核，不能交给被评测模型。

Linux已验收；现在等待用户确认候选答案。之后冻结答案/提示/实现，真实预算单独批准。[PLAN.draft.json](PLAN.draft.json)仅拟定14题×2条件×3次=84槽位，最多294请求、输入代理150万、输出申请279,552；不是已批准调用。初始正文与工具索引代理量分别记录在计划的initial_input_summary，工具声明和累计回复另计。

[官方价格](https://siliconflow.cn/pricing)与[分时说明](https://docs.siliconflow.cn/docs/release-notes/overview)于2026-10-11复核：此Flash高峰无缓存输入¥3/百万token、输出¥9/百万token。按代理输入预算与输出申请上限计算参考约¥7.02；这是估算，不是tokenizer精确成本、金额硬上限或账单。价格快照见[PRICE_SNAPSHOT.draft.json](PRICE_SNAPSHOT.draft.json)。不继承T1额度，不做自动换型号；没有真实请求验证供应商当前返回的模型身份。
