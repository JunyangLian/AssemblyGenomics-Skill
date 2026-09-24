# 决策记录

按时间记录关键决策、理由与影响。每条含时间、决策与依据。

## 2026-09-21

### D-001 报告类文档采用项目内 Markdown
- 决策：规划与竞争分析用 Markdown 落在项目 `docs/`，不生成 HTML 报告。
- 理由：这些是持续维护的开发基线文档，Markdown 可被后续 Agent 直接读取、可版本管理。
- 影响：`plan-m0-m1.md`、`competitive-analysis.md` 已按此落盘。

### D-002 项目根目录落位
- 决策：项目文件直接落在工作根 `AssemblyGenomics Skill/`，不加一层 `assembly-genomics/` 嵌套。
- 理由：工作目录本身已是专用项目目录，嵌套一层同名目录增加无意义跳转。
- 影响：全部文件相对工作根组织；若未来需移植到独立 repo，再整体改名。

### D-003 单倍型交付含义默认 primary
- 决策：`delivery.representation` 未显式声明时提示并阻断，不静默假定；默认立场为 primary_reference，phased 是需专门证据支持的选项。
- 理由：需求文档强调"不让 primary 冒充分相结果"。
- 影响：project.schema.json 中 `representation` 未填或为 unresolved 时校验阻断。

### D-004 主执行框架选定 Nextflow
- 决策：选定 Nextflow 作为计算执行框架。
- 理由：复用 Sanger genomeassembly 模块化组装经验。
- 影响：M1 预留 workflow 与 adapter 骨架约定；真实 Nextflow pipeline 属 M2。

### D-005 产品定位与执行模型
- 决策：一个 Skill，两个执行 backend（A 生成 SOP 包 / B 远程直连），先 A 后 B；保留在"LLM 自适应组装 + 强制人类审核门控"空白上做首版。
- 理由：`docs/competitive-analysis.md` 确认该组合无成熟竞品；合并架构复用共享地基，串行节奏先做透 A。
- 影响：backend 选项由后端契约承载；`references/remote-execution.md` 定义 B 的安全策略（本轮只落文档）。【2026-09-24 审计修正：该文档实际未落盘，B 维持无文档、无实现的 unsupported 状态（见 capability_matrix）】

### D-006 首版验收基线
- 决策：首版验收以"至少一条真实路线从原始读段走到报告 + Juicebox 人工审核不能绕过"为准，先做透 SOP 版。
- 理由：需求文档第 15 节首版验收清单。
- 影响：当前开发只走 M0 → M1 配置/状态/审核测试；不宣称跑通真实组装。

### D-007 M1 完成
- 决策：M1（配置/状态/审核/报告能力骨架）完成，71 个测试通过，产出 `validation_report.md`。
- 理由：规划段 1~段 5 全部交付，阻断用例覆盖面满足门槛。
- 影响：进入 M2 的方向是真实组装适配器（Juicer/3D-DNA 与 YaHS 两路）与 `preflight.py`；组装相关路线能力等级仍为 planned，未升级。

### D-008 冻结真实首用例 #001
- 决策：以真实数据 `Grape-001`（grape 三倍体、短读+Hi-C、复现已有结果、完整交付）作为首个冻结用例。【公开仓库中项目编号已脱敏为 Grape-001】
- 理由：数据清单证实短读+Hi-C、无长读；历史产物命名指向 Juicer+3D-DNA 主干。
- 影响：preflight 与 adapter 契约据此冻结（79 测试）。【流程细节初版含 SOAPdenovo2，随后被 D-009 据真实脚本修正】

### D-009 真实进度与单倍型交付修正
- 决策：修正用例 #001——真实进度仅到 **Hi-C 挂载 + 对参考标准化（一一对准染色体）**（含 Juicebox post-review），后续（单倍型验证、细胞器/污染、BUSCO、formal 报告、delivery）未跑；交付要求为**单倍型交付**。
- 理由：用户确认 + 上传真实 `.task.sh`/`shell/*` 脚本内容（突破此前"仅文件名"限制）。还原出：SGE 调度（非 SLURM）、手写 Juicer 流程（bwa+samtools+awk）、DpnII(GATCGATC)、3D-DNA `-m haploid`。
- 影响：流程 DAG 重写（第 6~9 步未跑部分为 skill 接管目标）；technology_registry 移除 SOAPdenovo2（contig 已有）、Juicer 改记为手写流程；environment.md 记录真实 SGE/资源；preflight 增加 SGE 探测与 conda-env 回退；79 测试全绿。

### D-010 接管目标改为注释阶段
- 决策：确认真实进度**到报告已完成**（挂载/标准化/单倍型/细胞器/BUSCO/报告都做完）；未完成的是**结构注释 + 功能注释**。skill 首试接管目标从"组装+评估"改为"注释（结构→功能）"。
- 理由：用户明确说明"细胞器/污染→BUSCO→报告我也做完了，只有结构注释和功能注释还没做"。
- 影响：use-case-001 DAG 加步 10（结构注释）、11（功能注释）为接管目标；technology_registry 新增注释阶段 required 工具（MAKER/Augustus-SNAP/InterProScan/eggnog /RepeatModeler/RepeatMasker）；preflight 将扩充注释工具探测。形成注释 pipeline 是本阶段验证主线。

### D-011 方向修正：以"静默缺口"陷阱库为首要机制
- 决策：修正产品重点——skill 的核心价值不是"代码一次写完美/跑通就算对"，而是**捕获"能跑通但不完整"（silent gap）**。新建 `knowledge/pitfalls/` 代码化陷阱库 + `scripts/run_pitfall_checks.py`，与报错修复（preflight/error）正交。
- 理由：用户真实体验+反思——RepeatMasker 跑通但只下到 dfam0 旧库，屏蔽少很多却不报错；新手最易被"看似成功"误导。
- 影响：（1）陷阱库首条真实种子 = 01-dfam.yaml（Dfam 库版本过旧）；（2）判定逻辑抽为纯函数 `_decide_gap`，只在脚本明确宣告"缺口/GAP"时判 gap，把"环境不支持/执行失败"与"真缺口"区分开（不误报）；（3）检查脚本面向 Linux/POSIX 服务器（本机开发 bash 存根不可用时回退需人工，不臆断）；（4）87 测试全绿。后续难点是把专家踩坑经验持续灌入陷阱库，而非追求代码完美。

### D-012 新手向导雏形（skill_coach）落地
- 决策：新增 `scripts/skill_coach.py` 作新手主入口——文件名数据识别（wgs/hic/rna 读段、组装产物、不可识别文件告警）→ plan 路由（复用硬约束）→ 输出分步 SOP（JSON），每步附 `pitfalls` 坑位预警；陷阱库含 annotation 条目时追加 SUGGESTED 注释步作为坑的挂靠点。
- 理由：对齐产品定位"skill 要指定怎么做，并在每步预警静默缺口"；新手第一触点应是"把数据放进来 → 得到带坑位预警的路线图"，而非先填 schema。
- 影响：测试增至 96 passed；SKILL.md 以 skill_coach 为新手入口、validate_project→plan 为专家入口双轨进入。后续真实闭环（重复屏蔽先行）从两条入口都能到达。

## 2026-09-22

### D-013 Siganus 真实注释全流程冻结为注释阶段参考实现（use-case-002）
- 决策：用户完整跑通的结构+功能注释（黄斑蓝子鱼 Siganus canaliculatus）整理为 `docs/use-case-002-siganus-annotation.md`，原始记录存 `docs/case-siganus/`。结构注释走 BRAKER3 ETP + TSEBRA(intron08) + AGAT + gffread + BUSCO 路线（替代原 MAKER 候选路线）；功能注释走 DIAMOND×5 + InterProScan 5.76-107.0 + Python 集成，test-then-promote 模式。
- 理由：D-010 定注释为 skill 接管目标，此前只有"工具名候选"；本用例提供已在真实服务器 case_validated 的完整 SOP（含参数、QC、检查点、续跑规则、真实结果 97.4% BUSCO / 86.09% Any-Annotated），是 skill 生成注释 SOP 的参考基线。
- 影响：（1）陷阱库新增 5 条真实种子 PIT-002~006（TSEBRA 默认阈值、BUSCO/miniprot 字段误读、蛋白内部歧义字符、GFF3 非编码残留、软屏蔽失效）；（2）technology_registry 注释工具升为"真实已验证"并列实际版本；（3）capability_matrix 注释路线记 case_validated（人工）与 skill 执行 planned 两档，不混写；（4）use-case-001 步 10/11 指向该参考实现，grape 采用时按物种适配（lineage eudicotyledons、单倍型分套、SGE 调度）。

### D-014 陷阱库真实数据校准通过（6/6）
- 决策：用 Siganus 服务器真实产物（已知标准答案）对 6 条探测器做零算力校准：PIT-002~006 全部命中预期（阳性报警、阴性沉默），PIT-004 与独立诊断的 ground truth 逐 ID 逐计数吻合（g17431.t2×4、427_t×1）。
- 理由：探测器此前只有合成数据测试；真实阳性命中 + 真实阴性不误报才算机制成立。方法即"用户在服务器跑只读命令贴回输出"，属 backend A 的最廉价真实接触。
- 影响：validation_report 记录校准证据表；error_log 记录过程中两处会话侧命令缺陷（单行 awk 丢括号、管道吞退出码），教训固化为"给用户的命令必须从已测试源提取"。仍不覆盖：其他物种/pipeline 产物上的误报率。

### D-015 新增"文献基线"机制：结果合理性对照（用户洞察产品化）
- 决策：新建 `knowledge/baselines/` + `scripts/check_baselines.py` + 测试。回答"这个数正常吗"：关键指标（基因数、BUSCO、屏蔽比例、注释覆盖率等）对照按类群的参考带，范围外报警并区分合法偏离（多倍化等）与非法偏离（指向对应 PIT 条目）。与 pitfalls 正交：pitfalls 问"这步做对了吗"，baselines 问"这个数像话吗"。
- 理由：用户指出——各物种类群的关键指标在网上有大量发表先例，除特殊情况外与文献差距悬殊必有问题，而新手没有文献量、意识不到。这正是"专家知道而新手不知道"的可代码化知识。
- 影响：（1）首版种子 5 条（BASE-001~005）全部 Siganus 真实案例锚定，`case_reference`/advisory 档；（2）**enforce 门槛代码强制**——强制报警档必须 `published` 且 ≥2 条带 doi/url 的引用，防止把个案当共识、防止凭记忆编造文献数值；（3）Siganus 真实交付值作为回归锚（应全部 within）。扩充路径：按 README 流程查文献补引用后升 enforce。

### D-016 基线改为双层结构：项目级锚点（intake 选定）优先于类群兜底带
- 决策：用户指出 skill 面向所有基因组，"扩充鱼类文献"的预填充思路不成立。改为——**intake 确定数据来源时一并选定该物种最近的已发表同类作为对照锚**（与选 BUSCO lineage 同一动作），写入 project.yaml 新增的 `baselines` 节（schema 支持 references + metric_overrides）；`check_baselines.py` 的 `--project` 优先采用项目锚点，未覆盖指标退回全局注册表兜底（advisory）。未选锚不阻断路由，但对照输出明示"仅类群兜底带"，报告须如实标注。
- 理由：预填充全局表覆盖不了所有类群，且对非模式物种参考价值低；"拿到数据→找最近同类"是用户在 Siganus 上实际做事的方式，属每次项目开始的可执行动作，与"交付表示必须显式声明"（D-003）同一纪律。
- 影响：（1）schema 加 baselines 节（顺手修复 scheduler 枚举缺失 sge——与 use-case-001 真实环境矛盾）；（2）enforce 两档门槛：全局 published ≥2 doi，项目锚 1 条 accession/doi 即可（intake 人类决策）；（3）演示验证：同值 40000 基因，有锚点 GAP / 无锚点明示兜底放行；（4）测试 114 全绿。

## 2026-09-22（下午，酵母测试用例启动）

### D-017 数据下载网络策略：境内镜像优先，国外兜底
- 决策：后续所有数据/数据库下载指令**优先给境内镜像**（清华 TUNA 及 CNGB/NGDC 等国内源），没有境内源时再给国外源；同时每种来源都要落哈希校验（NCBI 用官方 md5checksums，滚动发布库用"下载时实测 sha256 + 条目数 + 日期"绑定）。
- 理由：服务器直连国外实测仅 ~400-800 KB/s（Swiss-Prot 89 MB 用了近 4 分钟）；境内镜像显著更快，且规则由用户明确指示。
- 影响：environment.md 记录各数据源的境内可用性盘点；RNA-seq（SRA）下载时先试 CNGB 镜像再回 NCBI 直连； yeast 用例已下载文件不受影响。

### D-018 酵母机制闭环启动（use-case-003）+ 多 proband 规则修正
- 决策：grape 注释因算力大（三倍体双 hap、周级），首轮机制闭环改用 **S. cerevisiae S288C**（12.1 Mb 单倍体、公开数据、半天内跑完）。intake 已完成：数据下载并哈希绑定（NCBI md5 通过、Swiss-Prot sha256+575,748 条绑定）、锚点实测（17 序列 / 6,459 gene / 6,386 CDS / 6,021 protein）、project.yaml 草案过 schema、三条 metric_overrides 机械推导（CDS ±10% 等）。
- 理由：循环验证需要真实执行但不必用最贵数据；酵母的锚点强度（同种同株 RefSeq）使静默缺口检测最灵敏；低重复含量强制走项目级基线覆盖，演练 D-016 双层设计。
- 影响：（1）**首次真实 intake 即暴露校验器设计摩擦**——多 proband 规则误伤 RNA-seq 重复库，已修正为只对组装源文库（wgs/hic）计冲突，+2 回归测试（教训：schema 规则需区分组装源与证据文库）；（2）grape #001 仍为真实案例目标，不受影响；（3）待办：RNA-seq 选 run、BUSCO 谱系、锚点自跑 BUSCO、D-017 SOP 形态确认。

### D-019 资源预算必须显式向用户确认（用户指出，PIT-007）
- 决策：线程/内存/磁盘预算写入 project.yaml 前必须**向用户显式询问并确认**，不得沿用默认值、示例命令或上一项目的数值（如 Siganus 的 48 线程）。固化为：SKILL.md 硬约束第 7 条、工作循环步 4 的生成前置条件、陷阱库 PIT-007（check：预算 ≥ nproc 即 GAP，未提供退回人工）。
- 理由：用户指出 skill 在 yeast SOP 规划中默认沿用了 48 线程预算而从未询问——服务器可能公用或多用途，拉满不合适。这是 D-011"专家常识/新手盲区"方向的又一实证，且属于 skill 自身流程缺陷而非外部工具坑。
- 影响：（1）yeast project.yaml 的 cpu_limit: 16 标记为占位假设，待用户确认后改写；（2）SOP 生成的 settings 冻结流程增加"预算确认"必经步；（3）Siganus SOP（48 线程默认）在复用到新服务器时同样触发此确认。

### D-020 产品定位收窄：只面向新手，老手价值 = 毕业产物（可复用 SOP 包）
- 决策：目标用户明确定义为**第一次独立搭建基因组组装/注释的新手**；不做双通道/双档位。用户在 skill 护航下走完一遍后，项目终点交付物包含**一套属于用户自己的可复用流程 SOP 包**（冻结 settings、版本、检查点、坑位预警），此后用户可脱离 skill 自行复用——效率/复用价值放在终点而非并行通道。段 1 SOP 采用阶段化 Python 驱动形态（D-017 提议就此确认），Siganus three_assemblies 包即该形态的实证原型。
- 理由：用户拍板"只面向新手，目的是帮助新手搭建第一套自己组装的基因组"。单一定位让每个功能都有唯一裁判标准（是否帮新手成功）；"走一遍→沉淀可复用包"已被 Siganus 实证，比双通道更便宜且产物更真实。老手仍可借用机制层（陷阱库/基线/门控），但那不是产品设计目标。
- 影响：（1）SKILL.md 定位与入口段重写（取消"新手/专家双入口"表述）；（2）工作循环终点新增"毕业包"交付物；（3）段 1 SOP 按 32 线程（D-019 确认值）+ 新生档解释密度生成。

### D-021 SOP 包交付规程（用户抓出的交付漏洞）
- 决策：每个 SOP 包交付必须附带**落盘指令三件套**——目录创建命令、文件传输方式说明（优先复用用户已有传输习惯，不假设通道存在）、带期望 sha256 的完整性校验命令；包内对外路径一律服务器绝对路径，产物目录在包内自包含。
- 理由：段 1 首次交付只给了运行命令，用户在服务器上无目录可进（"你还没有让我新建好文件夹"）；同一次交付还暴露 settings 相对路径问题（genome 相对包目录会指错）。这是 skill 自身交付规程缺陷，属 PIT-007/D-019 同类的"流程级坑"。
- 影响：SKILL.md 工作循环步 4 增加交付规程；段 1 包附 `deploy_to_server.sh`（heredoc 落盘 + sha256 自校验）与短校验命令块；settings 的 genome_gz 改为服务器绝对路径。
## 2026-09-23

### D-022 危险指令纪律：禁止裸 `rm -f` + 通配符出现在用户指令中
- 决策：发给用户的任何命令块不得包含 `rm -f <glob>`（或 rm -rf）；需要清理时先给 `ls` 展示现状，指明确切文件名，或要求用户自查后自行删除。
- 理由：2026-09-23 事故——指令 `rm -f WT_Rep*.fq.gz` 在用户已经完成改名后执行，删掉 4 个完好的 RNA-seq 文件（2.7 GB，需重传）。裸通配符对命名时序零防护，风险远超便利。
- 影响：SKILL.md 工作循环步 4 指令纪律扩展；error_log 记严重条目；本会话所有后续指令一律不出现裸删除。

## 2026-09-24

### D-023 酵母机制环四段全通，毕业包达成（D-020 兑现）
- 决策：use-case-003 四段（重复注释 → RNA 比对 → 结构注释 → 功能注释）全部通过回传校验；`sop/yeast_loop/` 成为首个毕业包（可复用 SOP + 冻结 settings + 检查点 + 基线锚点）。
- 理由：机制层（intake/preflight/SOP/回传校验/基线/陷阱库）在真实数据上全链路验证；PIT-008/009 与 GO 多值解析等真实缺陷转化为 driver 防线与陷阱条目。
- 影响：capability_matrix 注释/功能两行升 case_validated（skill 排程）；Any-Annotated 基线 [80,99]→[95,100]（观测校准）；结构注释边界如实记录（ET 模式、单倍体酵母）。

### D-024 发布前审计修复：文档事实矛盾与敏感信息清零
- 决策：公开仓库全量审计后修复 12 项问题。事实矛盾 3 项：陷阱库 README 判定语义与 `_decide_gap` 实现相反（改为关键词宣告约定）、use-case-003 状态头/待办停在 intake 期、capability_matrix 头部停在 M1；敏感信息：项目编号脱敏为 Grape-001、实机绝对路径占位化（/home、/mnt、/program、本地盘符）、删除含真实 conda 路径的 run_stage3.py.bak（.gitignore 补 *.bak）；发布口径：README 安装改"clone 后自行打包"（无 Release、dist 不入库）、快速开始 check_baselines 命令实测修复、License 链接修正；validation_report 补酵母环验证节；backend B 悬空引用如实标注"文档未落盘"；SOP 包生成行按 D-023 理由升 case_validated（酵母环四段实证）。
- 理由：本项目核心即捕获"能跑通但不完整"——审计发现文档层存在同类静默缺口（状态头/验收报告停在旧版本、README 脱敏声明与公开内容不符），与运行层 silent gap 同源。
- 影响：新纪律——**每落一条 D-决策须同步刷新受影响文档的状态头与计数**（文档层无 run_registry，靠此防漂移）；git 历史中旧内容保留（敏感度低，不重写历史；如需彻底清除另行评估 force-push）；回归 117 passed，快速开始命令全部实测通过。
