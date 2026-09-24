# 能力矩阵

记录每条能力路线的验证等级。等级定义：planned（仅设计）/ implemented_unverified（已实现未验证）/ smoke_tested（小样本验证链路）/ case_validated（真实案例验证）/ unsupported（不支持）。

当前状态：**M1 配置/状态/审核/报告测试通过（当前全量 96 passed）+ 冻结流程 #001 的 preflight 与 adapter 通道契约 + 注释阶段参考实现冻结（use-case-002，Siganus 真实 SOP）**。无 skill 执行的真实组装/注释。组装相关路线仍为 planned；注释路线的 **SOP 基线是真实跑通的（人工），skill 接管执行仍 planned**，两者分开记录。

| 路线 | 输入 | 验证等级 | 说明 |
|---|---|---|---|
| SOP 包生成（backend A） | 元数据 + 目标 | implemented_unverified | M1 已实现 schema/校验/路由/状态/审核；preflight 已针对 #001 实现；注释参考 SOP 基线已冻结（use-case-002） |
| 远程直连（backend B） | 见 references/remote-execution.md | unsupported（仅文档） | 本阶段仅定义接口契约与安全策略 |
| Juicer + 3D-DNA + Juicebox（冻结 #001） | Hi-C + draft FASTA | planned | adapter 通道契约已定，真实执行待服务器 |
| YaHS + JBAT | Hi-C + contigs | planned | 未安装验证 |
| 纯二代 WGS 真核组装 | 二代双端 | under_frozen_flow | 冻结流程 #001 明确为短读+Hi-C，多倍体情况需证据 |
| 结构注释（BRAKER3 ETP + TSEBRA + AGAT，#002） | 软屏蔽基因组 + RNA BAM + 蛋白证据 | case_validated（人工）/ skill 执行 planned | Siganus self 真实跑通（23,924 基因，BUSCO 97.4%）；grape 适配未做 |
| 结构注释（酵母环 #003：ET 模式 + TSEBRA + AGAT + BUSCO） | softmasked + 2 BAM | **case_validated（skill 生成 SOP + 回传校验闭环）** | 5,384 基因 BUSCO 99.0%；边界：单倍体酵母、ET 模式（非 ETP）、最长集交付 |
| 功能注释（DIAMOND×5 + InterProScan + 集成，#002） | 代表蛋白 + 5 库 | case_validated（人工）/ skill 执行 planned | Qatar 真实跑通（86.09% Any-Annotated，validation PASS） |
| 功能注释（酵母环 #003：DIAMOND×5 + InterProScan） | 最长蛋白集 5,384 | **case_validated（skill 生成 SOP + 回传校验闭环）** | Any-Annotated 99.96%；GO 多值解析修复；五库真菌适配 |