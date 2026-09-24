# M0 + M1 实施规划：AssemblyGenomics Skill

> 编写日期：2026-09-21
> 文档状态：实施规划，待审核。审核通过前只生产本计划文档，不创建项目代码、schema 或测试文件。
> 依据：`# 自适应基因组组装全流程 Skill`需求文档（工作目录外上传，随项目保留参照）。

***

## 决策记录

本轮由使用者确认了三项影响开发方向的决定，写入项目 `decisions.md` 作为第一组记录：

| 决策点     | 结论                                                | 影响                                                      |
| ------- | ------------------------------------------------- | ------------------------------------------------------- |
| 本轮推进范围  | 仅产出 M0 + M1 实施规划，审核通过后再动工                         | 暂不创建任何代码 / schema / 测试文件                                |
| 主执行框架   | 选定 Nextflow                                       | M1 预留 workflow 与 adapter 骨架约定；真实 Nextflow pipeline 属 M2 |
| 单倍型交付含义 | 默认 primary reference，phased haplotype 为需专门证据支持的选项 | `delivery.representation` 未显式声明时提示并阻断，不静默假定             |

另有两项经使用者讨论后补充进决策记录：

| 决策点  | 结论                                               | 影响             |
| ---- | ------------------------------------------------ | -------------- |
| 产品定位 | 市场调研确认"LLM 自适应组装 + 强制人类审核门控"组合无成熟竞品，保留在这条空白上做价值  | 见"执行模型选项"与竞争分析 |
| 执行模型 | 首版采用"生成 SOP 包、用户自行跑、回传阶段成果"；agent 直连服务器列为可选的后续路线 | 见"执行模型选项"      |

### 执行模型选项

一项竞争调研（落地为 `docs/competitive-analysis.md`）显示，市场现有两类成品都有缺口：传统流水线（nf-core genomeassembler、Sanger genomeassembly、Colora）可靠但硬编码、无 LLM 自适应、无人工门控；AI 技能库（bioSkills、bioflowkit、ClawBio、OLAF）自适应但无硬性人工审核门控。agent 直连真实服务器调度 HPC 的完整闭环（断点续接、失败恢复、状态持久化、产物回传分析）目前没有成熟产品，tacc-mcp-bio 最接近但也只是查日志/队列的 Copilot。我们保留在"LLM 自适应组装 + 强制 Juicebox 人类审核门控"这个组合空白上做首版。

结构决策：**一个 Skill，两个执行 backend，先 A 后 B**。共享地基（schema、状态机、manifest、路由、审核门控、失效传播、报告、产物校验）两个 backend 复用同一套；SOP 包生成是 backend A，远程调度是 backend B。它们是从属的升级关系，不是两个并列产品，因此拆成两个 skill 会重复维护地基，此处合并架构。

| 模型 (backend) | 说明 | 实现阶段 |
|---|---|---|
| A. 生成 SOP 包 | agent 本地生成 SOP 压缩包，用户在服务器自行运行，跑完回传 logs、产物 hash、run 明细；agent 校验回传后生成下一段 SOP | 首版完整闭环，优先做透 |
| B. agent 直连服务器 | 用户授权后，agent 通过 ssh / Nextflow executor 远程下发、读回日志并编排 | 后续作为同一 skill 的第二个 backend；先定义接口契约与安全策略文档 |

架构合并、节奏串行：首版验收标准是"至少一条真实路线从原始读段走到报告"，先把 A（SOP 版）走完；B 只在本轮落 backend 选择、接口契约与 `references/remote-execution.md` 的安全策略定义，其实时执行延后。两条 backend 都不放松约束：回传/读回的产物必须经校验，状态以磁盘结构化记录为准，不因改成 SOP 形态而放松；agent 不替人类完成最终 Juicebox 判断。

### 待确认事项

其余未定事项（首例数据、服务器、用户现有脚本、首版物种与倍性、纯二代真核组装路线、POD5 basecalling、是否公开）继续作为 M0 待确认输入，见下节。

***

## M0 范围与输入确认

### M0 交付物

1. 用户现有流程盘点表：已有脚本、工具版本、成功案例、中间产物位置与授权。
2. 首例数据清单与授权声明。
3. 服务器体检基线：操作系统、调度器、CPU/RAM/磁盘/配额、容器权限、网络策略。
4. 交付表示与倍性约定（本轮已定 primary 为默认，仍需按首例样本确认）。
5. 支持矩阵初稿：路线 × 输入组合 × validation 等级（planned / implemented\_unverified / smoke\_tested / case\_validated / unsupported）。

### M0 需要使用者提供的信息

| 项                        | 用途                | 缺失时处理                        |
| ------------------------ | ----------------- | ---------------------------- |
| 首例数据路径、规模、来源与授权          | 选第一条真实全流程路线       | 不启动正式任务，能做设计与本地测试            |
| 服务器登录/资源上限/调度器           | 校准 preflight 探测指标 | preflight 用 mock 环境自测，不连真实集群 |
| 用户现有脚本与成功案例              | 优先复用，保留原始，不覆盖     | M1 归档脚本改名工具测                 |
| 首版物种与倍性                  | 定支持矩阵边界           | 暂按真核单个体案例设计                  |
| 已有 Nextflow / nf-core 环境 | 决定 adapter 打包方式   | environment.md 记录探测缺失        |

### M0 明确不做

- 不使用企业客户或未授权科研数据。

- 不沿用其他 LLM 项目的 RTX 3070 预算假设。

- 不公开或上传任何数据、代码与成果。

- 不安装未选定的工具（draft 阶段）。

### M0 完成门槛

- 上表每项结转到 pending / done / blocked 之一；BLOCKED 项有明确原因与替代建议。

- 支持矩阵初稿经使用者审阅。

- 归档或路由现有脚本的方式已与使用者确认。

***

## M1 项目骨架设计

目标是跑通"配置校验 → 路由 → 状态持久化 → 审批与失效传播"这条与真实计算无关的链路，全部用模拟数据自测，不宣称跑通组装。

### 目录结构（落地版，含 Nextflow 预留）

```text
assembly-genomics/
  SKILL.md                        # 入口文档；简洁，细节指向 references/
  references/
    scope-and-routing.md
    assembly-representations.md
    qc-and-review-policy.md
    juicer-3ddna.md
    yahs-jbat.md
    contamination-and-organelles.md
    troubleshooting.md
  schemas/
    project.schema.json
    review.schema.json
  scripts/
    preflight.py
    validate_project.py
    plan.py
    validate_review.py
    summarize_results.py
  workflows/
    adapters/                     # Nextflow process 封装；M2 填充，M1 只留输入/输出通道约定
    nextflow.config               # M1 只含 failsafe 与资源上限占位
  templates/
    project.yaml
    review_decisions.tsv
    report.md
  tests/
    fixtures/                     # mock 数据集、坏 manifest、旧 review 文件
    test_routing.py
    test_review_gate.py
    test_invalidation.py
    test_reporting.py
  docs/
    capability_matrix.md
    environment.md
    validation_report.md
    decisions.md
    run_registry.md
    error_log.md
```

M1 只建实际需要的模块，不机械生成空文件；`workflows/adapters/` 与 `nextflow.config` 各只落一条说明性骨架，确认打包约定。

### schema 字段规格

`project.schema.json` 字段取自需求文档 4.3 示例，并把未定项显式暴露为可阻断状态：

- `schema_version`：固定 `1`。

- `project_id` / `run_id`：持久化项目与运行标识，防重复提交。

- `sample`：`id`、`organism`、`taxid`、`ploidy`、`ploidy_evidence`、`genome_size_bp`、`genome_size_basis`、`sex`、`tissue`、`mixed_sample`。`ploidy` 与 `genome_size_bp` 未提供时按"未知"校验，进入 `genome_survey` 而非阻断（前提是交付表示已定）。

- `delivery`：`representation`（枚举 primary\_reference / primary\_alternate / selected\_phased\_haplotype / all\_phased\_haplotypes / subgenome\_resolved / unresolved）、`phase_scope_required`、`parental_identity_required`、`organelle_policy`（默认 `review_and_separate`）。

- `inputs`：`libraries[]`（每项含 technology、library\_type、library\_id、read\_files、batch、read\_quality、sample\_role）、`existing_assembly`（version、origin、integrity）。

- `execution`：`framework=nextflow`、`scheduler`、`cpu_limit`、`memory_gb_limit`、`disk_gb_limit`、`allow_remote_upload=false`、`tool_versions`。

- `review`：`require_plan_approval`、`require_sequence_edit_approval`、`require_hic_review`、`require_release_approval`（默认全 true）。

校验关系（`validate_project.py` 实现）：`delivery.representation` 未声明或为 `unresolved` 时阻断；resource 任一上限缺失阻断；样本无角色或角色冲突阻断；`parental_identity_required=true` 时强制要求亲本角色独立存在。校验失败给出具体字段路径与原因，而不是一句 YAML 解析失败。

`review.schema.json` 关键字段：

- `review_round_id`、`project_id`、`sample`、`assembly_identity`、`upstream_route`。

- `binds_to`：`input.assembly_hash` 与 `review_package_hash`（本轮绑定，旧版批准不可复用）。

- 配套文件：FASTA hash、supporting files hash、软件版本、坐标/缩放信息、生成时间、恢复输入位置（过大文件用带校验值的受控路径引用，不全量复制到本地）。

- `status`：accepted / modified / rejected / undetermined。

- `approval`：`approved_by_human=true` 且 `submission_action` 非空（明确的人类提交动作），二者缺一即未批准。M1 承诺"流程可追踪"，不宣称强身份认证级别。

### manifest 与状态词表

manifest：项目、样本、组装身份、上游路线、FASTA hash、配套文件 hash、软件版本、坐标/缩放、生成时间、恢复输入位置。

状态词表：`PENDING -> READY -> RUNNING -> SUCCEEDED`；`RUNNING` 可到 `FAILED / WAITING_REVIEW / BLOCKED`；`WAITING_REVIEW -> READY / REJECTED`；常驻 `SKIPPED_NOT_APPLICABLE`、`STALE`。语义要点：

- `SUCCEEDED` 只表示该节点执行与产物检查通过，不代表整个组装科学质量通过。

- `WAITING_REVIEW` 是正常业务状态，进入后依赖审核结果的下游不占用计算节点。

- `STALE` 表示上游输入、配置或工具版本改变后，原产物不再适用于当前任务。

- 状态以磁盘结构化记录为准，不以聊天历史为准；写入原子化，禁止同一项目重复提交。

### 路由与能力约束（代码化）

按需求文档第 6 节映射为 `scripts/plan.py` 内的判定表，每条输入组合落到路由意图与门槛。硬约束（缺 R2、损坏文件、错误文库类型、样本角色冲突、倍性/表示未定义、多倍体未验证路径、只有 Hi-C 无可用组装）由代码直接阻断并给出缺什么、能做什么。LLM 可解释与提出候选，但不得越过代码层硬约束。

### 审批与失效传播

- LLM 不能写一个"已审核"绕过状态；批准须经 `validate_review.py` 校验人类提交动作、本轮 hash 绑定、片段/方向/边界合法性与 liftover 归属通过后才进入下一阶段。

- 上游组装修改后，依赖其序列和坐标的比对、图、审核与指标标为 `STALE`，只重算受影响节点，同时保留历史版本。

- 合法拆分不强制 ID 集合完全不变，但覆盖/缺失/重复/变更须逐项可解释。

### scripts 规格

| 脚本                     | 职责                                             | 输入 → 输出                         |
| ---------------------- | ---------------------------------------------- | ------------------------------- |
| `preflight.py`         | 探测 OS/调度器/CPU/RAM/disk/配额/容器权限/网络，列出可用工具与版本    | `manifest` → 资源与依赖报告            |
| `validate_project.py`  | 校验 schema 枚举、路径、单位、样本角色、不兼容组合、表示必填             | `project.yaml` → 通过或阻断+原因       |
| `plan.py`              | 依据 manifest、QC、目标生成 DAG/配置/预算/审核点，受支持矩阵与资源边界约束 | 已批准 project + QC → 方案 DAG       |
| `validate_review.py`   | 校验审核包 hash 绑定、编辑引用合法、覆盖/缺失/重复、liftover 归属、批准记录 | `review.assembly` + 审核包 → 通过或阻断 |
| `summarize_results.py` | 从结构化产物确定性提取指标生成报告，缺失/失败/不适用如实标注                | 产物 + 状态 → 汇总报告                  |

命令参数结构化构造与安全引用，不把文件名或用户文本拼进 shell 命令。

### Nextflow 集成边界（M1 只到这一层）

- `nextflow.config`（M1）只含 failsafe（maxRetries、进程资源上限）与全局预算占位，不含真实组装 process。

- `workflows/adapters/` 各留一条 input/output 通道约定与版本固定说明，供 M2 填充 Juicer/3D-DNA 与 YaHS 两条适配器；不做无损假设，BAM 不默认等于 HiFi。

- 版本锁定策略记入 `environment.md` 与 `technology_registry.md`（来源文档第 17 节引用项目）。

***

## 测试清单

三种验证严格区分，报告各自结论，不合并成一个"成功率"：

| 验证类型           | 用途                | 不证明什么         |
| -------------- | ----------------- | ------------- |
| 配置/模拟          | 路由、审核门槛、状态转换、错误提示 | 工具真实运行与生物学质量  |
| 小样本 smoke test | 接口兼容、命令与产物链路      | 完整基因组质量与资源规模  |
| 真实案例           | 指定数据/版本/目标下的表现    | 所有物种与未测组合的可靠性 |

M1 只做第一类（配置/模拟）。由需求文档 14.2 的必测情形映射出的用例，按四个测试文件拆解：

`test_routing.py`：有/无 Hi-C 路由正确并记录跳过原因；缺 R2、损坏文件、错误文库类型、样本冲突被阻断；倍性/交付表示未知时不擅自选择；多倍体未验证路径自动阻断；只有 Hi-C 无组装时阻断并给出可执行范围。

`test_review_gate.py`：未经人类批准不得进入 post-review 或交付；旧 `review.assembly`、错用 liftover、错误片段或坐标被识别；合法拆分的编辑可通过，不被粗糙 ID 校验误判；hap1/hap2 数据与命名不串用。

`test_invalidation.py`：会话中断、任务失败后恢复不重复提交；修改 FASTA/参数后下游缓存与旧审核正确失效；依赖工具/数据库/资源不足时明确报错而非无界重试。

`test_reporting.py`：指标缺失、工具失败不被包装成正常通过；污染/细胞器候选不未经批准直接删除；交付表示在运行前明确，primary 不冒充分相结果；数字由结构化产物确定性提取，缺失显示"未评估/不适用/执行失败"。

### M1 完成门槛

- 上述四个测试在 mock fixtures 上全部通过。

- `validate_project.py`、`validate_review.py` 对各阻断用例给出可定位的字段路径与原因。

- `decisions.md`、`environment.md`、`run_registry.md`、`error_log.md` 建立并能读写。

- 明确声明：此阶段未执行任何真实组装，能力矩阵相应格子保持 planned / implemented\_unverified 中未验证到位。

***

## 里程碑拆分

| 段   | 内容                                                | 产出          |
| --- | ------------------------------------------------- | ----------- |
| 段 1 | 目录落位 + schema + validate\_project + fixtures      | 项目可解析、校验可阻断 |
| 段 2 | 状态机 + manifest + run\_registry + 恢复逻辑             | 状态持久化与原子写入  |
| 段 3 | test\_routing + test\_invalidation                | 路由与失效传播通过   |
| 段 4 | validate\_review + review 状态 + test\_review\_gate | 审批门槛通过      |
| 段 5 | summarize\_results + test\_reporting + docs 补全    | 报告如实 + 文档齐  |

段内停点：每段完成后展示真实结果并给 2～3 个理解检查问题，确认后再进下一段；不跳过、不假装通过。

***

## 待使用者审阅的决策点

1. 目录根名用 `assembly-genomics`（需求文档 11.2 拟议名）还是直接落在工作目录当前路径。
2. M1 是否要求把 `workflows/adapters/` 与 `nextflow.config` 骨架一并产出，还是先做纯框架无关部分、Nextflow 边界留到 M2。
3. 上述任何工程规格（状态词表、schema 字段、测试拆分）是否有需要调整之处。

