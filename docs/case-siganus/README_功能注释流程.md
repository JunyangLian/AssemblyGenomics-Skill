# 黄斑蓝子鱼功能注释：先小样本，再全量

本目录提供可上传到 Linux 服务器的脚本，目标项目为 `~/Siganus_annotation/Siganus_qatar`。当前交付的是**测试流程和通过测试后的正式流程生成器**。本机没有服务器上的蛋白序列、GFF、数据库或 InterProScan；真实生物信息学测试尚未执行。合成数据回归测试只检查程序逻辑，不能代替真实测试。

## 1. 现有 NR 结果的判断

原命令的 `-e 1e-5` 是可以采用的初筛阈值，不是明显错误。但建议在新流程中重跑，保留旧结果作对照：

- `out="./2.NR"` 与实际 `1.NR` 不一致，而且相对路径依赖启动目录。
- `-k 1` 只留下一个候选，无法检查近似高分候选间的冲突。DIAMOND 的 `-k` 还会参与搜索启发式，不只是最终输出数量。
- 未明确启用高灵敏度模式；默认模式对远缘同源的召回有限。
- 默认 12 列 m8 没有蛋白长度、双方覆盖度、subject title。单独满足 E-value，不能排除只匹配一个短结构域的情况。
- `/nr_20240416.../animal.fa` 看起来是 NR 动物子集；目录名不能证明实际数据库版本。报告应写明实际范围，不应声称使用完整 NR。
- 命中 hypothetical/uncharacterized protein 仍是数据库命中，但不是已明确其具体功能。也不能仅据同源性命中宣称实验证实或正交关系。

新流程默认 `--very-sensitive -e 1e-5 -k 25 --max-hsps 1`，先保存原始命中，再以查询覆盖度 ≥50% 筛选并选最高 bitscore 的命中。并列时依次比较 E-value、查询覆盖度、subject ID。输出 17 列，包括 `qlen/slen/qcovhsp/scovhsp/stitle`。

**50% 是透明、可调整的起始参数，不是适用于所有蛋白的“严谨标准”。** 默认不强制 subject coverage 或 identity 阈值，以免系统性丢失融合蛋白、部分蛋白和远缘同源；两项可在配置中修改。单 HSP 覆盖度不等于多个 HSP 合并覆盖度。正式分析前应复核低覆盖、近似同分和多结构域蛋白；如需严格全长同源证据，可另检视双方覆盖度。仅保留前 25 个候选也不保证枚举所有同源序列。

## 2. 上传与启动

将本地的 `test/scripts` 目录上传至服务器项目的 `test/scripts`。所有文件均为 UTF-8、LF 换行，无需逐个 `chmod`，用 `bash` 启动即可。不要把测试脚本放进外层 `scripts`，配置中的相对根目录是按 `test/scripts` 设计的。

```bash
cd ~/Siganus_annotation/Siganus_qatar
# 首先按下一节核对/修改 test/scripts/config.json
bash test/scripts/check.sh && bash test/scripts/run_all.sh > test/run_all.log 2>&1
```

如果希望断开终端后继续：

```bash
cd ~/Siganus_annotation/Siganus_qatar
if bash test/scripts/check.sh; then
    nohup bash test/scripts/run_all.sh > test/run_all.log 2>&1 &
fi
```

也可以从其他目录用绝对路径启动。`run_all.sh` 自动按依赖顺序执行 0–8，任一步失败立即停止，修好后重新执行同一条命令即可。总控默认串行使用 32 线程，避免多个大库任务同时占满 CPU/内存；“一次启动”不需要七个任务同时并发。

脚本依赖 Linux、Bash、Python ≥3.9、DIAMOND 2.x、**InterProScan 5 及其完整数据库/运行依赖**。Python 只用标准库，不需要 pandas 或 Biopython。当前方案不适用于 InterProScan 6 的 Nextflow 接口。Python 可用 `PYTHON=/path/to/python3 bash test/scripts/run_all.sh` 指定。DIAMOND 与 InterProScan 路径在 JSON 中设置。

服务器当前 base 中的 Java 25 不作为本流程的运行环境。先运行 `python3 test/scripts/configure_java11.py`，它会查找已有 Java 11 并写入 `java_home`；也可用 `--java-home /实际/Java11/根目录` 明确指定。流程仅对 InterProScan 子进程设置 Java 环境。没有找到 Java 11 时的独立环境安装与帮助退出码修复说明见 `PREFLIGHT_FIX.md`。

## 3. 数据库路径配置

唯一配置入口是 `test/scripts/config.json`，它是严格 JSON，不能加 `#` 注释。原始数据默认从项目的 `0.Raw_Data/protein.faa` 和 `0.Raw_Data/genomic.gff` 读取。

| 项目 | 已知信息与待核对项 |
|---|---|
| NR | 已填附件中的 `animal.fa` 前缀，检查 `animal.fa.dmnd`。优先从 DIAMOND `stitle` 取得描述；若建库时未保留描述，需提供配套动物 ID→描述表。不会使用附件中的 `Plants_annot.tsv` 默认值。 |
| Swissprot | 已由服务器列表确认并固定 `swissport/diamond/uniprot_sprot.Eukaryota.fasta.simple.dmnd`，与 Eukaryota 描述表配对。`swissport` 拼写按实际路径保留。 |
| KEGG | 根据服务器目录列表，已固定 `kegg/101.0/animal.fa.dmnd` 与 `animal.id.annot.xls`。文件名显示二者范围对应；实际 ID 匹配由测试检验。不会隐式选择 `plant.id.annot.xls`。 |
| KOG | 已填 `kog/20090331` 目录及 `kog_clean.fa.id`，支持附件示例的 `[R] KOG1721 ...` 和制表符多列形式。 |
| TrEMBL | 根据服务器预检查输出，已固定 `uniprot_trembl.Eukaryota.fasta.simple.dmnd`，与配置中的 Eukaryota `simple.ann.tsv` 描述表保持范围一致。 |
| InterProScan | 已由服务器搜索结果确认并配置 `${SHARED}/ann/interproscan-5.76-107.0/interproscan.sh`。这是已找到安装目录中的较新版本；脚本存在不代表成员库与运行环境已验证，须通过预检查和真实小样本。 |

`databases.*.db` 留空时，只检查该目录**第一层**的 `.dmnd`；恰好一个非 plant/viridiplantae 候选才采用。多个候选会列出并停止，不会猜测。自动排除文件名中的 plant 只是避免明显误用，**不代表已经核实唯一候选的物种范围**；仍须对照库说明核对。

KEGG 的 `annotation` 留空时同样只接受唯一的非植物 `*.id.annot.*` 文件。各库的 `db` 与 `annotation` 最好最终都填绝对路径。目录发现不递归、不自动建库、不下载或修改共享数据库。带 `.xls` 后缀的附件表按纯文本 TSV 读取；如果实际是二进制 Excel 文件，应先导出 TSV。

服务器可以用以下命令收集资源信息：

```bash
command -v diamond
command -v interproscan.sh
ls -lh ${DB}/swissport/diamond/
ls -lh ${DB}/kegg/101.0/
ls -lh ${DB}/kog/20090331/
ls -lh ${DB}/trembl/
```

服务器已发现 InterProScan 5.30-69.0、5.59-91.0、5.76-107.0 及一个未核实指向的通用启动脚本。当前固定使用明确版本目录中的 5.76-107.0，并采用官方要求的 Java 11 环境（不能由 Conda 环境名推断实际 Java 版本）；可用 `java -version` 查看当前 Java。预检查汇总缺失资源，并执行工具版本、InterProScan 5 参数检查和各 DIAMOND 库的 `dbinfo`。只有真正的小样本执行才能检验成员库二进制、临时空间等运行条件。要求依据：[InterProScan 5 官方安装要求](https://interproscan-docs.readthedocs.io/en/v5/UserDocs.html)。

## 4. 输入与统计单位

默认 `sequence_unit="gene_representative"`：

1. 读取所有蛋白，检查唯一 ID、空序列及非法字符。只移除一个末端 `*` 并记录，不静默替换内部终止符或改写 U/O 等氨基酸。
2. 根据 GFF3 的 `protein_id`、明确的 CDS ID/Name/Dbxref 和 `Parent` 关系追溯基因。保留 accession 的版本号，不盲目去掉 `.1`。
3. 每个基因选最长蛋白，等长时按蛋白 ID 字典序选择。默认抽取 100 个代表蛋白，随机种子 `20260907`。不足 100 时全部使用，不重复抽样。
4. 同一套 query FASTA 用于全部数据库。该统计描述“基因的最长蛋白代表序列的注释覆盖率”，不等于汇总所有异构体的功能并集，也不包括未提供蛋白的非编码基因。

若任何蛋白无法唯一映射基因，流程停止并给出 ID 示例。先核对 GFF 与蛋白是否配套；只有明确选择做蛋白层面分析时才改为 `sequence_unit="protein"`。该模式保留所有蛋白/异构体，不输出误导性的基因计数。

固定种子的小样本用于检查数据格式、环境、库匹配及流程衔接，不能证明全量不会出现更长蛋白、特殊字符或资源瓶颈。为了减少后续意外，第 0 步会先验证完整蛋白文件及完整蛋白→基因映射，然后再抽样。

## 5. 编号、流程与结果

| 脚本 | 对应目录 | 主要内容 |
|---|---|---|
| `0.Raw_Data.sh` | `test/0.Raw_Data` | query.faa、全量与抽样 ID 清单、序列处理及 QC |
| `1.NR.sh` | `test/1.NR` | NR 比对、描述、覆盖度、最佳命中 |
| `2.Swissprot.sh` | `test/2.Swissprot` | Swiss-Prot 比对与注释 |
| `3.KEGG.sh` | `test/3.KEGG` | KEGG 比对、候选 KO、相近分数候选及冲突 |
| `4.KOG.sh` | `test/4.KOG` | KOG 编号与类别 |
| `5.TrEMBL.sh` | `test/5.TrEMBL` | TrEMBL 比对与描述 |
| `6.Interpro.sh` | `test/6.Interpro` | InterProScan、成员库签名、IPR、GO 证据 |
| `7.GO.sh` | `test/7.GO` | 去重 protein2go，基因模式另有 gene2go |
| `8.Integration.sh` | `test/8.Integration` | 七类注释总表、统计、重叠组合、技术验证报告 |

SH 文件是统一 Python 实现的薄入口；比对命令和解析逻辑集中在 `pipeline.py`，避免测试与正式脚本各维护一份而产生偏差。也可单独运行 `bash test/scripts/3.KEGG.sh`，但必须已有当前配置下完成的输入准备结果。所有入口都重新预检查资源。

最重要的交付结果：

- `8.Integration/functional_annotation.tsv`：每条 query 一行，包含未注释序列、七类 0/1 标记、KO/KOG/IPR/GO、各库命中与比对证据。
- `8.Integration/annotation_statistics.tsv`：注释数、全部输入数、百分比与统计单位，含 Any-Annotated。
- `8.Integration/annotation_overlap.tsv`：七类二进制组合及数量，可用于 UpSet 绘图；不是把七个注释数直接相加。
- `8.Integration/validation.json`：技术验证 PASS/告警，**不表示每个功能推断均正确**。
- `run_manifest.json`：解析后的配置、输入 SHA256、程序指纹、软件版本、库信息和大库文件的大小/修改时间。

各 DIAMOND 目录另有原始 17 列 `raw_hits.tsv`（无表头；字段见 `raw_hit_columns.tsv`）、带表头的 `filtered_hits.tsv` 和 `best_hits.tsv`、未匹配注释表的 subject 清单及 QC。解析大注释表时逐行扫描，只保存需要的命中 ID，避免把整个 TrEMBL 描述库加载进内存；不过即使 query 很少，仍可能要扫描很大的数据库/注释表。

## 6. 七类“Annotated”的具体含义

- **Nr / Swissprot / TrEMBL**：至少一个通过设定比对过滤的同源性命中。描述与 accession 同时保留，不把 uncharacterized/hypothetical 自动当成具体功能结论。Swiss-Prot 的 reviewed 标签描述的是库中条目，不会让查询蛋白因此变成已审定条目。
- **KEGG**：过滤后最高分命中的配套注释记录含 KO；另列 `KEGG_sequence_hit`，避免将“命中 KEGG 蛋白但没有 KO”算成 KO 注释。不会跳过最高分无 KO 的命中去挑低分有 KO 的命中。5% 近最高 bitscore 范围中的不同 KO 会标记 `ambiguous_near_top`；这些仍计入“有候选 KO”的数量，应在功能结论前复核。
- **KOG**：最高分命中的配套记录有 KOG 编号；另列 `KOG_sequence_hit`。类别字母与完整描述同时保留。字母不自动补成人工猜测的类别定义。
- **Interpro**：至少一个合法 `IPRxxxxxx` 编号。只有 Pfam 等成员签名但未整合入 InterPro 的命中，单独留在签名表，不混入 IPR 计数。
- **GO**：来自本次 InterProScan `--goterms` 的 GO accession，去重并保留来源。不是从 NR/TrEMBL 自由文本中猜 GO；不表示覆盖所有可能的 GO 注释来源。未补 GO 名称、BP/MF/CC 分类或祖先项传播，因尚未提供匹配版本的 GO ontology；本次不做富集分析。

**KEGG 方法边界：** 当前按附件已有 DIAMOND 库走同源比对与 ID 映射，产物是候选 KO；不等同于 KofamScan/KAAS 的正交功能分配。若后续结论依赖具体代谢通路或酶功能，建议加入 KofamScan 的 KO 专属阈值证据，并复核冲突。当前未提供 KOfam 安装与库路径，所以没有虚构该步骤已经运行，也不虚构 KO→pathway 映射。

InterProScan 默认运行本安装可用的默认成员分析，并保存 help/版本信息。`interpro_applications=[]` 表示不限制成员库。默认关闭远程预计算查询以便本地重算；因此测试也可能较慢。若显式只选择 Pfam 等子集，测试与正式都将使用该子集，覆盖范围必须写入方法。

## 7. 通过真实测试后生成正式脚本

检查统计和告警后执行：

```bash
cd ~/Siganus_annotation/Siganus_qatar
cat test/8.Integration/annotation_statistics.tsv
cat test/8.Integration/validation.json
bash test/scripts/promote.sh
# 正式脚本生成成功后，全量分析单独启动：
nohup bash scripts/run_all.sh > full_annotation.log 2>&1 &
```

`promote.sh` 会重新核对配置、输入、软件/库指纹及各步骤输出 SHA256。只有本机实际测试状态完整、当前配置未改变且不是 synthetic 标记时才生成外层 `scripts`，将样本数改为 0（全部），输出根目录改为项目根目录，并固定通过测试的具体库/软件路径。

若外层已有 `scripts/1.NR.sh` 等同名文件，先复制到 `scripts/before_annotation_*` 备份，再写入正式版本；其他脚本不动。已有 `1.NR/Siganus_qatar_NR.m8` 与日志不会覆盖，新结果使用新的通用文件名。正式第 0 步会在原始 `0.Raw_Data` 旁写入 query/清单等新文件，不修改 `protein.faa` 或 `genomic.gff`。

完成标记由输出校验决定，不凭文件夹存在判断成功。修改配置、输入、程序或数据库大小/mtime 会使旧结果失效并重新运行；不会递归删除旧目录。失败尝试的日志保存在对应步骤的 `.attempt-*` 目录中。成功的 InterProScan 临时目录也可能保留，真实测试后可自行确认空间占用。大数据库未逐字节哈希，故若库被原地改写又刻意保持大小与 mtime，不能依此检测；正式记录中仍应保存管理员提供的 release/checksum。

## 8. 本地验证与资料

运行逻辑测试：`python test/scripts/test_pipeline.py`。测试使用合成 FASTA/GFF、模拟比对和 InterPro TSV，不调用真实 DIAMOND/InterProScan，也不会生成可用于正式部署的真实测试通过状态。覆盖 ID 错配、无命中、重复 ID、内部终止、最长异构体、固定随机抽样、KO 冲突、无 KO 最佳命中、GO 去重、序列 MD5 校验、失败保留诊断、断点续跑与防止模拟测试晋级等情况。

参数与格式依据：

- [DIAMOND 官方参数文档](https://github.com/bbuchfink/diamond/wiki/3.-Command-line-options)：灵敏度、候选上限的搜索影响、自定义输出、覆盖度。
- [InterProScan 5 官方运行说明](https://interproscan-docs.readthedocs.io/en/v5/HowToRun.html)：成员库选择、GO/IPR 与本地计算选项。
- [InterProScan 官方 TSV 格式](https://interproscan-docs.readthedocs.io/en/v5/OutputFormats.html)：IPR、GO 列与仅输出有签名命中的序列。
- [NCBI GFF3 说明](https://www.ncbi.nlm.nih.gov/datasets/docs/v2/reference-docs/file-formats/annotation-files/about-ncbi-gff3/)：protein_id、Parent、基因/转录本/CDS 模型。
- [KofamKOALA 官方说明](https://www.genome.jp/tools/kofamkoala/)：基于 profile HMM 与各 KO 阈值的赋值方法。
