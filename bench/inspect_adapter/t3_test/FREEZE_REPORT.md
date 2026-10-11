# T3 答案冻结与 GLM 后续配置

2026-10-11 用户回复“确认答案并允许冻结（推荐）”，随后指定 GLM-5.3-Flash，密钥不变。

## 本阶段完成

- APPROVAL.json记录人类授权范围；FROZEN.md逐题记录14份expected SHA-256；FROZEN.json保护84个题目文件及公共合同/schema、Linux与匿名AI审核凭据。
- t3_freeze.py及tests/test_t3_freeze.py提供重复冻结验证、答案/提示篡改拒绝、未授权拒绝及额外题目文件拒绝。没有修改已复现题面、产物、meta或expected字节；没有改动现有规则脚本。
- NEXT_RUN.draft.json配置SiliconFlow的zai-org/GLM-5.3-Flash及环境变量SILICONFLOW_API_KEY；PRICE_GLM.draft.json保存官方价格快照。历史DeepSeek草案保留。README及bench/CHANGELOG说明版本与状态。

## 验证

`bench/inspect_adapter/.venv/Scripts/python.exe -m pytest -q`：471 passed，9 warnings，264.32秒。警告来自Inspect依赖的tenacity弃用参数。冻结专项4/4通过，84文件与原复现manifest零差异，新增文件LF检查通过，git staged diff检查通过。

本阶段真实API调用0次，费用0；没有读取或记录密钥。用户上传的zip及tar.gz保持原状，不纳入本次提交。

## 后续边界

草案仍为14题×inline/tools×3=84条观测，最多294请求、150万输入代理token、279,552输出申请token。GLM官方价格无缓存输入¥0.80/百万、输出¥2.80/百万，代理/申请额度参考约¥1.98，非账单或金额硬上限。

金标准已获批准；新付费预算尚未批准。下一步先完成本运行的物理预算保护和离线协议fixture，再按具体运行上限确认真实调用。思考开关、JSON及工具调用的供应商参数兼容尚待验证，不自动切换型号或调整实验条件。模型配置不能改动gold冻结。

历史生成/验收文件中的draft/pending/false保留原字节，当前状态由APPROVAL与FROZEN侧录确定。匿名AI审核不是独立真人专家盲审，也不证明生物学正确性或证据语义完全无误。
