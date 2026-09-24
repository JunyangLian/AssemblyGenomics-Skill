# 首用例定义（真实数据：F24A040009496_Grape）

> 状态：**frozen（已冻结）**，基于用户真实上传的本项目数据清单确认。
> 物种：**葡萄（Grape，栽培种，三倍体）**。`Gracilaria_changii / Gracilaria_bailinae`（红藻）参考序列在数据中作为对照/参考出现，**不代表本项目物种**；skill 必须能识别这种"参考序列 ≠ 目标物种"并判断其角色，这是数据识别能力的关键场景之一。

## 一、数据全貌（从真实清单识别出）

项目 `F24A040009496_Grape`，三个个体，各有**双端短读 + Hi-C**→**hap1/hap2 两套单倍型组装**。按目录组织：

| 目录 | 内容 | 数据类型识别 |
|---|---|---|
| `00.data/`：<每个样本>/{样本}.hic_1/2.fq.gz、CWHPE 短读 _1/_2.fq.gz、md5.txt、work*.sh | **原始数据**：Hi-C FASTQ（19G/端）+ 二代短读 | 识别为 raw reads |
| `01.Genome_Denovo/01.denovo/`：{样本}.hic.p_utg.gfa / .p_ctg.gfa / .r_utg.gfa 及 .noseq 变体、.lowQ.bed、{样本}.p.fa、.hap1.fa、.hap2.fa、.N50 | **已组装图与结果**：GFA 格式组装图、合并 FASTA、低质量区域 bed | 识别为 assembly products |
| `02.BUSCO/`：{样本}.hap1/2.buso/short_summary...json/txt、Step1.sh | **质量评估**：BUSCO 结果（eudicotyledons_odb12.2） | 识别为 evaluation |
| `03.Redup/`：purge_dups.sh、purge_haplotig.sh | **单倍型去冗余**：purge_dups / purge_haplotig 脚本 | 识别为 haplotig purging |
| `04.MapEvaluation/`：s14.bwa.sh | **比对评估**：bwa 短读回比对 | 识别为 mapping eval |
| `Data/`：{样本}.fq.gz、Bam.list、Bam2name.list、*depth* | 中间数据：合并读段、BAM 列表、深度统计 | 识别为 intermediates |
| 其它：purge_dups.sh、BUSCO.sh、Cal_GC.pl、GC 分选（.GC0.45）、organelle_ref/mitochondrion/chloroplast、*.paf、Get_fq2.pl | 工作脚本 | 识别为 workflow scripts |

**三倍体证据**：三样本 + hap1/hap2 两套组装 + `GC0.45` 阈值 + purge_dups/purge_haplotig —— 典型的**多倍体单倍型分离**工作流。

## 二、冻结决策（用户确认）

- **目标**：复现已有的一轮人工组装结果（SM4b/7C/9C 的 hap1/hap2）。
- **交付终点**：完整交付 = 组装(fasta) + Hi-C 挂载(gfa) + BUSCO 评估 + 单倍型去冗余(purge_dups) + 细胞器/污染分离 + 汇总报告。
- **物种/工具口径**：葡萄、三倍体；用合式流程（短读 + Hi-C，非 long-read-only）。

## 三、识别难点（skill 必须学会的教训）

1. **`.hic_1.fq.gz` 是 Hi-C FASTQ，不是 `.hic` 图**——新手易误判。
2. **`Gracilaria_*` 参考 ≠ 目标物种葡萄**——参考/对照文件不能污染物种判断。
3. **`.gfa` 是组装图、`.bam` 是比对、`.paf` 是 minimap/paf 长读比对**——扩展名分组是弱信号，须结合目录语义（denovo=组装、Map=比对）。
4. **同一目录下 `*_1.fq.gz`/`*_2.fq.gz` 配对短读可成 R1/R2 对**——校验配对完整性（M1 有对应规则）。

## 四、已知缺口（需后续补全）

- 这份清单没有 ONT/HiFi 长读产物迹象（.paf 6 个可能是 minimap2 比对而非长读源）。**预 gin：若以"短读 + Hi-C"组装三倍体葡萄并要 hap1/hap2 分离，推荐参考路线待冻结**（短读 de Bruijn + Hi-C 挂载在该规模有限，需确认用户预期质量）。

## 五、冻结判定

状态：**frozen**。以上数据识别结论已按用户澄清（grape 非红藻）+ 目标/终点确认锁定。后续 preflight 与 adapter 以"短读 + Hi-C、三倍体、到完整交付"为目标。

> **进度更新（用户补充）**：**到报告均已完成**——Hi-C 挂载 + 对参考标准化（一一对准染色体）、单倍型验证、细胞器/污染、BUSCO、formal 报告、delivery 全部做过。**未完成的是注释阶段**：结构注释 + 功能注释。交付要求是**单倍型交付**。真实工作流与脚本见下方第七节（已拿到真实 `.task.sh`/`shell/*` 内容，突破此前"脚本内容缺失"限制）。**skill 首试的接管目标是注释（结构 + 功能）**，而非早期组装/评估。

## 六、冻结流程 DAG（首条流程）

> 数据形态：**短读 + Hi-C**（从真实清单确认，无 HiFi/ONT 长读）。目标：复现并**完整交付**（组装 + Hi-C 挂载 + 单倍型分离 + BUSCO + 细胞器分离 + 报告）。
> 工具链依据：历史产物命名（`.hic.p_utg.gfa`/`.p_ctg.gfa`/`.lowQ.bed` = 3D-DNA 输出；`*.hap1/2.buso` = BUSCO；`.paf` = minimap2）+ 已查证的主流流程 [$TRAE_REF](https://bio-protocol.org/exchange/protocoldetail?id=4475&type=1)[$TRAE_REF](https://hcc.unl.edu/docs/applications/app_specific/bioinformatics_tools/de_novo_assembly_tools/soapdenovo2/)。

| 步 | 环节 | 工具 | 输入 | 输出 | 人工门槛 | 真实状态 |
|---|---|---|---|---|---|---|
| 0 | 数据校验 | (本项目校验器) | 原始 fq.gz | 校验报告、manifest | 无 | 待接入 |
| 1 | 短读质控 | fastp | 短读 R1/R2 | clean.fq.gz | 无 | 已完成 |
| 2 | contig 组装 | (历史已有) | clean 短读 | hap1/hap2.contig | 无 | 已完成 |
| 3 | Hi-C 比对 | Juicer(手写脚本) | Hi-C fq + hap contig | merged_nodups.txt | 无 | **已完成** |
| 4 | 3D-DNA 挂载 | 3D-DNA `-m haploid` | hap contig + merged | scaffold gfa | **STOP: Juicebox 人工调图** | **已完成** |
| 5 | 对参考标准化 | postreview_standardization | scaffold + 参考 | 一一对准染色体的组装 | 须 review 批准 | **已完成** |
| 6 | 单倍型验证/去冗余 | purge_dups(待确认) | scaffold + BAM depth | hap1/hap2 干净 .fa | 无 | **已完成** |
| 7 | 细胞器/污染分离 | contamination_screen | 组装 + 比对 | 核基因组分离 | 候选须批准 | **已完成** |
| 8 | BUSCO + QUAST | BUSCO(双子叶库) | 最终 .fa | BUSCO/N50 | 无 | **已完成** |
| 9 | 汇总报告 | summarize_results | 全部产物 + 状态 | 结构化 + 报告 | 报告前确认 | **已完成** |
| 10 | **结构注释** | 参考实现：use-case-002（BRAKER3+TSEBRA+AGAT） | 最终 .fa (+转录证据) | 基因结构 gff | 注释质量可核 | **未跑 = skill 接管目标** |
| 11 | **功能注释** | 参考实现：use-case-002（DIAMOND×5+InterProScan） | gff + 蛋白 | GO/KEGG 功能 | 无 | **未跑 = skill 接管目标** |

**skill 首试接管目标是步 10、11（注释）**。步 1~9 已完成，作为接续输入起点（最终 .fa / hap 组装 / BUSCO 结果）。真实 Juicer/挂载流程见第七节。**注释 SOP 参考实现已冻结**：见 `use-case-002-siganus-annotation.md`（Siganus 真实跑通）；grape 采用时按物种适配——BUSCO lineage 换 eudicotyledons、三倍体 hap1/hap2 分套注释、调度沿用 SGE。陷阱库 PIT-002~006 为注释阶段真实坑位。

**冻结判定**：以真实脚本落地流程细节（见第七节），交付终点为**注释完成（单倍型）**。

## 七、真实工作流还原（来自 `02.HIC` 的 `.task.sh` / `shell/*`）

> 数据：用户上传 SM4-hap1 的真实脚本内容。这是首次拿到**脚本内容**（非仅有文件名），据此精确还原工具链与调度，突破此前推断局限。

### 目录结构（`${HOME}/Grape/02.HIC/`）
- 每个 hap 独立目录：`SM4-hap1/ SM4-hap2/ SM7-hap1/ SM7-hap2/ SM9-hap1/ SM9-hap2/`，内含 `Juicer/`、`3ddna/`、`shell/`、`workflow_snapshot/`
- `New_Template/`：**参考主代码**（教师模板，用户指定以此为准）
- `00_setup_*_postreview_standardization.sh`：post-review 后对参考标准化（一一对准染色体）
- `contamination_screen/`、`delivery_inventory/`、`final_assembly_report/`、`hic_heatmaps/`、`standardized_genome_validation/`：**后续/交付产物，未完成**
- `local_scripts/`：fastaDeal.pl、changReadName.py、wrap_fasta.py 等辅助脚本

### 真实 Juicer 流程（手写脚本，非官方 juicer.sh 一键）
1. `00.ln.sh`：`ln -sf` Hi-C 原始读段 1/2 → Juicer/fastq
2. `01.mkindex.sh`：`bwa index` hap 参考（`.clear.fa`，来自 05.Contamination 的 SM4b.hap1.clear.fa）
3. `02.bwawork.sh`：`bwa mem -t 32` 分别比对 R1/R2 → `samtools sort -n` → `changReadName.py` 加 /1、/2 后缀
4. `03.bwamerge.sh`：`samtools merge` 两 split → `samtools view → .sam` → `chimeric_blacklist.awk`（norm/abnorm/unmapped 三路）→ `fragment.pl`（**DpnII 酶切，GATCGATC** 位点）→ sort → `dups.awk` → `statistics.pl` → `merged_nodups.txt`
5. `05.3ddna.sh`：`run-asm-pipeline.sh -m haploid -r 0 --build-gapped-map`（配 wrap_fasta.py 定宽 + fastaDeal.pl 校验 id:len）
- **调度为 SGE**：`qsub-sge.pl --queue bc.q --resource "num_proc=32,vf=54G -binding linear:32"` 等（步 3 用 32 核/54G，3ddna 用 20 核/25G），**非 SLURM**
- **单倍型交付**：每个 hap 独立打一轮 Juicer+3D-DNA，各自挂载

### 对 skill 的关键启示
- **真实工具链并非官方 juicer.sh 一键**，而是一套手写 bwa+samtools+awk 流程。skill 复现前需确认是"复刻手写流程"还是"转译成官方 Juicer/Nextflow"。
- **调度是 SGE**；preflight 的 resource 探测须识别 SGE（qsub）而非仅 SLURM。
- 酶切为 **DpnII (GATCGATC)**；BWA 内存/线程参数可作 real 资源参考（54G/32 核）。
- `-m haploid` 3D-DNA 说明是按单倍型 hap 挂载，印证"单倍型交付"是设计目标。