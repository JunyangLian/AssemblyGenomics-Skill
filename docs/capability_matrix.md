# 能力矩阵

记录每条能力路线的验证等级。等级定义：planned（仅设计）/ implemented_unverified（已实现未验证）/ smoke_tested（小样本验证链路）/ case_validated（真实案例验证）/ unsupported（不支持）。

当前状态（2026-09-24，D-025）：全量回归 **128 passed**。数据识别层 P0 修复（D-025）：BAM 不再视作组装源、无法识别的 FASTQ 归 unknown_reads 并阻断待显式确认（不默认 WGS）、删除 hiseq 误判关键词、R1/R2 按样本前缀硬阻断、交付表示缺省即阻断（模板默认 unresolved）。注释全流程（重复 → RNA → 结构 → 功能）经 skill 生成的 SOP 在酵母机制环（use-case-003）**端到端跑通并逐段回传校验**，毕业包沉淀于 `sop/yeast_loop/`；Siganus 注释（use-case-002）为人工跑通的参考实现。**从原始读段组装仍未验证**（组装路线保持 planned；酵母环输入为已发表组装）。人工跑通与 skill 闭环分档记录，不混写。

| 路线 | 输入 | 验证等级 | 说明 |
|---|---|---|---|
| SOP 包生成（backend A） | 元数据 + 目标 | **case_validated（酵母环四段实证）** | 机制层（intake/preflight/SOP/回传校验/基线/陷阱库）在真实数据全链路验证（D-023）；换物种复用见 `sop/yeast_loop/` 毕业包 |
| 远程直连（backend B） | — | unsupported | D-005 保留方向：接口契约与安全策略文档未落盘（计划未执行），实时执行延后 |
| Juicer + 3D-DNA + Juicebox（冻结 #001） | Hi-C + draft FASTA | planned | adapter 通道契约已定，真实执行待服务器 |
| YaHS + JBAT | Hi-C + contigs | planned | 未安装验证 |
| 纯二代 WGS 真核组装 | 二代双端 | under_frozen_flow | 冻结流程 #001 明确为短读+Hi-C，多倍体情况需证据 |
| 结构注释（BRAKER3 ETP + TSEBRA + AGAT，#002） | 软屏蔽基因组 + RNA BAM + 蛋白证据 | case_validated（人工）/ skill 执行 planned | Siganus self 真实跑通（23,924 基因，BUSCO 97.4%）；grape 适配未做 |
| 结构注释（酵母环 #003：ET 模式 + TSEBRA + AGAT + BUSCO） | softmasked + 2 BAM | **case_validated（skill 生成 SOP + 回传校验闭环）** | 5,384 基因 BUSCO 99.0%；边界：单倍体酵母、ET 模式（非 ETP）、最长集交付 |
| 功能注释（DIAMOND×5 + InterProScan + 集成，#002） | 代表蛋白 + 5 库 | case_validated（人工）/ skill 执行 planned | Qatar 真实跑通（86.09% Any-Annotated，validation PASS） |
| 功能注释（酵母环 #003：DIAMOND×5 + InterProScan） | 最长蛋白集 5,384 | **case_validated（skill 生成 SOP + 回传校验闭环）** | Any-Annotated 99.96%；GO 多值解析修复；五库真菌适配 |