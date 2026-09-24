# QC 与审核门控策略

状态机、审核门槛与失效传播的语义。实现：`scripts/state_registry.py`（状态机）、`scripts/validate_review.py`（审核）、`scripts/plan.py` 的 `invalidate_downstream`（失效传播）。

## 状态词表

```
PENDING -> READY -> RUNNING -> SUCCEEDED
RUNNING -> FAILED / WAITING_REVIEW / BLOCKED
WAITING_REVIEW -> READY / REJECTED
常驻：SKIPPED_NOT_APPLICABLE, STALE
```

语义要点：

- `SUCCEEDED` 只表示该节点执行与产物检查通过，**不代表组装科学质量通过**。
- `WAITING_REVIEW` 是正常业务状态，不是故障；进入后依赖审核结果的下游不占计算节点。
- `STALE` 表示上游输入、配置或工具版本改变后，原产物不再适用于当前任务。
- 状态以磁盘结构化记录（RunRegistry）为准，不以聊天历史为准；写入原子化。

## 重调度与恢复

- 禁止同一活跃项目重复提交。
- FAILED 后不得无界重试：须显式经 READY 才可重调度（`state_registry.py recover`）。
- 会话中断后恢复不重复提交。

## 审核门控（validate_review.py）

post-review 产物进入下一阶段前，逐项校验（任一不过即阻断，exit 1）：

1. **人类批准二要素**：`approval.approved_by_human=true` 且 `approval.submission_action` 非空，二者缺一即未批准。LLM 不能代写。
2. **hash 绑定**：`binds_to.input_assembly_hash` 与 `binds_to.review_package_hash` 必填；`stale=true` 的旧绑定拒绝复用——旧版批准不可延续到新版产物。
3. **编辑引用合法**：坐标/片段引用格式 `chr:start-end[:hap1|hap2]` 或 scaffold 引用；重复坐标须逐项可解释；缺 ref 即阻断。
4. **liftover 归属**：`liftover_from` 的 hap 与引用的 hap 标注不一致时阻断（hap1/hap2 不串用）。
5. **status 门控**：仅 `accepted`/`modified` 可继续；`rejected`/`undetermined` 阻断。

## 失效传播

上游 FASTA 或参数修改后，把项目置 `STALE`（仅对仍有效状态 SUCCEEDED/READY/RUNNING/WAITING_REVIEW 生效；FAILED/BLOCKED 已是非稳态，保持不变）。依赖旧产物的审核与指标随之失效，只重算受影响节点，历史版本保留。

## 报告如实原则（summarize_results.py）

- 数字由结构化产物确定性提取，不用 LLM 编造。
- 指标缺失、工具失败显示"未评估/不适用/执行失败"，不包装成通过。
- 污染/细胞器候选不未经批准直接删除——报告必须标出待批准项。
- 运行前交付表示未定即报告阻断；primary 不冒充分相结果（出现即警告）。

## 三种验证严格区分

| 验证类型 | 证明 | 不证明 |
|---|---|---|
| 配置/模拟 | 路由、审核门槛、状态转换、错误提示正确 | 工具真实运行与生物学质量 |
| 小样本 smoke | 接口兼容、命令与产物链路 | 完整基因组质量与资源规模 |
| 真实案例 | 指定数据/版本/目标下的表现 | 所有物种与未测组合的可靠性 |

引用能力结论时必须声明属于哪一类。当前项目仅完成第一类。
