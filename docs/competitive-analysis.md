# 竞争分析：AssemblyGenomics Skill

> 编写日期：2026-09-21
> 状态：两轮只读调研综合结论。调研不校验工具维护状态，结论以两轮检索当时的公开资料为准。
> 用途：支撑项目定位决策，回答"是否已有成熟成品、是否还值得做"。

---

## 一句话结论

截至调研时，学术、商业、社区三个层面都不存在"开箱即用、覆盖原始读段到交付报告、且带 Hi-C/Juicebox 人工审核硬门控"的成熟成品。现有项目大部分只覆盖该组合的某一部分，没有项目同时具备这三个要素，因此自研价值成立。

---

## 三要素拆分：每个要素的现状

| 能力要素 | 已有项目示例 | 现状 |
|---|---|---|
| 组装流程的 LLM 自适应编排 | BioAgents、BioMaster、AutoBA、（传统流水线 nf-core / Sanger / Colora 无 LLM） | 有通用生信多 Agent 框架，但无面向组装的完整编排成品；传统流水线可靠但硬编码 |
| Hi-C / Juicebox 人工审核门控 | AutoHiC（DL 纠错）、三代 Hi-C 流水线（YaHS/Juicebox，脚本层） | 只有 pipeline 层可选模块或散落的脚本指导，无数值 Agent 级硬门控 |
| 断点续接 / 状态持久化 | LangGraph、Bioinfoysis | 通用工作流框架具备潜力，但未针对组装暴露为 Copilot 能力 |

没有任何单一项目把上表三格同时做齐。这正是本产品要占据的定位。

---

## 分面调研明细

### 学术 / 论文面

未发现"现成可下载即用"的 LLM agent 驱动组装成品；工具分两类，且未交汇：

- DL 驱动组装/scaffolding（非 LLM agent）：AutoHiC、GNNome、GTasm、Puzzler 均开源可用 [1][2]。
- LLM agent 通用生信分析：BioAgents（Phi-3 多 agent，部分标注 close-sourced）[3]、AutoBA、Bio-Copilot，均未覆盖 genome assembly/scaffolding。
- human-in-the-loop 门控在组装 agent 中是空白：Puzzler 仅将 curation 作为可选模块，未见明确 checkpoint/resume 证据 [1]。

### 商业产品面

不存在"原始读段到交付报告 + Hi-C 人工审核门控"的商业成品：

- Geneious、DNASTAR 有组装但无 Hi-C 门控 [4][5]；Illumina BaseSpace、Sentieon 非端到端组装与可控 [6][7]；Seqera/Nextflow Tower 是编排平台无组装智能 [8]。
- "AI Copilot" 类初创全部没碰组装：OmicsWeb 仅 RNA-seq、Genovera 侧重 DNA 注释/蛋白结构、Profluent 做蛋白设计 [9][10][11]。
- "组装即服务"（Thinkubate、Sanger ToL、BV-BRC）是人工驱动的流水线服务，不是 LLM agent [12]。

### 社区 / MCP / Agent 生态面

现有生信 MCP 与多 Agent 框架停留在"工具接入/脚本生成"层，未形成组装 Agent 成品：

- BioinfoMCP 把工具转 MCP（含 FastQC/fastp/SPAdes/QUAST），AlphaGenome、gget、UCSC 是数据源接入，均非组装 Copilot。
- BioMaster 覆盖 QC/alignment 等分析，无 Hi-C 门控；Bioinfoysis 有持久化 artifact run，但未针对组装。

---

## 对我们的价值判断

1. 我们不必与火箭级传统流水线拼可靠性，而是把"自然语言描述需求 → LLM 自适应生成流程 → Hi-C 挂载后硬性 STOP 等人类用 Juicebox 调 → 批准后继续 → 交付报告"做成组合空白里的可用产品。
2. 首版采用"生成 SOP 包、用户自行跑、回传成果"的执行模型（安全、不触碰用户生产环境）；agent 直连服务器作为可选后续路线。两条模型都不放松三要素约束。
3. 复用时保留来源与必要声明，维护状态会变化，执行时应重新核验、固定版本、检查许可。

---

## 来源

[1] Puzzler, Bioinformatics Advances 2025 — HiFi+Hi-C pipeline，含可选 curation：https://academic.oup.com/bioinformaticsadvances/article/6/1/vbaf329/8432934
[2] AutoHiC / GNNome / GTasm：https://academic.oup.com/nar/article/52/19/e92/7759145 ；https://pmc.ncbi.nlm.nih.gov/articles/PMC12047240/ ；https://www.frontiersin.org/journals/genetics/articles/10.3389/fgene.2024.1495657/full
[3] BioAgents, arXiv:2501.06314：https://arxiv.org/html/2501.06314v1
[4] Geneious Prime：https://www.geneious.com/features/prime
[5] DNASTAR de novo assembly：https://www.dnastar.com/workflows/de-novo-genome-assembly/
[6] Illumina BaseSpace：https://www.illumina.com/products/by-type/informatics-products/basespace-sequence-hub.html
[7] Sentieon：https://www.sentieon.com/products/
[8] Seqera Platform：https://docs.seqera.io/platform/23.4/getting-started/deployment-options
[9] OmicsWeb (Biostate AI)：https://www.biostate.ai/rna-sequencing
[10] Genovera AI：https://www.genovera.ai/
[11] Profluent Bio：https://aiwiki.ai/wiki/profluent/raw
[12] Thinkubate、Sanger ToL、BV-BRC：https://www.thinkubate.io/ ；https://pipelines.tol.sanger.ac.uk/pipelines ；https://www.bv-brc.org/docs/tutorial/genome_assembly/assembly.html

参考前一轮：bioSkills https://github.com/GPTomics/bioSkills ；tacc-mcp-bio https://github.com/Narasimhan-Lab/tacc-mcp-bio ；jobd https://pypi.org/project/jobd/0.5.29/ ；RASER (arXiv:2609.03598) https://arxiv.org/html/2609.03598v1