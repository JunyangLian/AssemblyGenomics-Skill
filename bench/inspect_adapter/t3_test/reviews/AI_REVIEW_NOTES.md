# AI 公开资料盲审记录

审查者是 AI（Codex child agent inheriting parent model; exact provider model ID unavailable），不是真人专家。上下文为 fork_none/public_only。无 gold、答案映射或历史评分输入。仅访问 packets/schema.json、packets/system.txt、R001–R014/task.md 和各自 artifacts 的三个公开文件，以及本次自己创建的检查脚本和结果。未读取 meta.json、expected.json、PRIVATE_MAPPING.json、题库构建器或其他仓库资料。

本次隔离是执行中的访问约束，没有操作系统强制的独立沙箱或访问审计证明。默认 exec_command 启动失败，Node REPL 两次启动失败；后改用获准的 require_escalated 本地 PowerShell 读取公开文件并执行本地 Python。没有联网，没有调用其他或付费模型服务，没有修改题面或产物。

## 执行方法

blind_check.py 用 Python 标准库遍历全部 GFF 非注释行（按原文件一基行号）、全部 FAA header 和全部序列行。读取第九列中的 ID/Parent/protein_id；建立 ID 索引后对每个 Parent 检查存在性、类型（mRNA→gene，exon/CDS→mRNA）、seqid、strand，以及父.start ≤ 子.start ≤ 子.end ≤ 父.end。每行 CDS 的 protein_id 均与 FAA header 第一个 token 做区分大小写、保留版本的精确连接，并反向检查无游离 FAA 记录和无重复 FAA token。

CDS 行数与 unique CDS ID 分别计算；同时独立计算 unique protein_id 数。完整 FAA 序列按非空白字符统计 residues，再与 record_counts.json 的七个顶层统计字段逐一比较。复核了 compact 全记录显示、全部检查错误与原始证据位置；终端大批显示有截断，机械解析不依赖截断输出，R007 的局部显示另行完整读取。write_review.py 检查每题输出只有 schema 的七字段、字段类型和枚举，并校验 evidence 路径、实际文件与一基行号/JSON 顶层字段。

没有以 Name、Dbxref、CDS ID、orig_protein_id 替代 protein_id，没有执行去版本或相似名称补配。允许的 partial、异构体和重复多片段 CDS ID 未被当作异常。未检查翻译、phase 生物学正确性、功能、全基因组质量或历史上游过程，因为 task.md:5、task.md:9 明示这些范围限制。

## 合同与 schema 表达限制

合同对本批资料的阻断条件足够明确，未发现足以改变 pass/block 的合同歧义。“两套完整编码 gene 特征块”按全部层级记录已给出的文件完整性理解；task.md:9 明确允许 partial，因此不把 complete block 理解为强制生物学全长。

schema 的 root_cause 是有限标签：缺失 Parent 可同时被描述为标识引用不匹配或层级错误；本审查采用 gff_hierarchy_error 表示可观测的未解析层级边，不把它归因为上游重命名、丢基因或别的历史事故。它不区分坐标越界的具体方向、游离 FAA、同组多个错误 CDS 行，或正常的多片段/partial/异构体；这些事实在 evidence 和本笔记补记。没有运行日志，无法确定应该修改哪一侧的 ID、Parent 或坐标；修复必须依据可信来源，而不是自动套用相似名称。

所有记录计数字段均与直接重算一致。计数一致是次级事实，不能消除必要连接或层级缺陷。全部问题是启动前输入合同，不存在已完成结果或可恢复旧版，因此所有阻断判定均为 block，不是 rollback。

## 逐题记录

|题号|判定|GFF gene/mRNA/exon/CDS 行|unique CDS ID / unique protein_id / FAA|residues|Parent 边|计数核对|
|---|---|---|---|---|---|---|
|R001|pass|2/3/19/17|3/3/3|832|39|全七字段相符|
|R002|block|2/2/4/4|2/2/2|476|10|全七字段相符|
|R003|pass|2/2/8/8|2/2/2|1130|18|全七字段相符|
|R004|block|2/3/18/17|3/3/3|741|38|全七字段相符|
|R005|block|2/3/19/17|3/3/3|832|39|全七字段相符|
|R006|block|2/2/4/4|2/2/2|726|10|全七字段相符|
|R007|pass|2/2/4/4|2/2/2|726|10|全七字段相符|
|R008|pass|2/3/18/17|3/3/3|741|38|全七字段相符|
|R009|pass|2/2/4/4|2/2/2|476|10|全七字段相符|
|R010|pass|2/3/11/10|3/3/3|3044|24|全七字段相符|
|R011|pass|2/2/10/8|2/2/2|1826|20|全七字段相符|
|R012|block|2/2/10/8|2/2/2|1826|20|全七字段相符|
|R013|block|2/3/11/10|3/3/3|3044|24|全七字段相符|
|R014|block|2/2/8/8|2/2/2|1130|18|全七字段相符|

## 逐题次级事实与不确定性

### R001

判定：pass；缺陷：none；文件级原因标签：none。

- 全记录检查 39 条 Parent 边均通过存在性、类型、seqid、strand 与闭区间包含；全部 CDS 行及全部 FAA 双向精确连接通过。
- GFF 41 条非注释特征记录、CDS 17 行、unique CDS ID 3、unique protein_id 3、FAA 3 条和 832 residues 均已实际遍历；字面统计一致。
- 范围内合同判定无未决不确定性；未对范围外生物学质量作判断。

### R002

判定：block；缺陷：gff_faa_link_missing；文件级原因标签：id_mismatch。

- 其余全部 Parent 边检查通过。数值上 unique CDS ID、unique protein_id 与 FAA 记录数相等，但键集合不相等。
- partial=true 出现在 GFF 行 2, 3, 4, 5, 8, 9, 10, 11；该属性本身不阻断，也不豁免 Parent/蛋白连接合同。
- GFF 12 条非注释特征记录、CDS 4 行、unique CDS ID 2、unique protein_id 2、FAA 2 条和 476 residues 均已实际遍历；字面统计一致。
- 不确定性：确定存在精确连接键不一致；无法仅凭公开文件判断 GFF protein_id 还是 FAA header 才是应保留的正确标识，也无法推断上游生成过程。

### R003

判定：pass；缺陷：none；文件级原因标签：none。

- 全记录检查 18 条 Parent 边均通过存在性、类型、seqid、strand 与闭区间包含；全部 CDS 行及全部 FAA 双向精确连接通过。
- GFF 20 条非注释特征记录、CDS 8 行、unique CDS ID 2、unique protein_id 2、FAA 2 条和 1130 residues 均已实际遍历；字面统计一致。
- 范围内合同判定无未决不确定性；未对范围外生物学质量作判断。

### R004

判定：block；缺陷：gff_faa_link_missing；文件级原因标签：id_mismatch。

- 其余全部 Parent 边检查通过。数值上 unique CDS ID、unique protein_id 与 FAA 记录数相等，但键集合不相等。
- GFF 40 条非注释特征记录、CDS 17 行、unique CDS ID 3、unique protein_id 3、FAA 3 条和 741 residues 均已实际遍历；字面统计一致。
- 不确定性：确定存在精确连接键不一致；无法仅凭公开文件判断 GFF protein_id 还是 FAA header 才是应保留的正确标识，也无法推断上游生成过程。

### R005

判定：block；缺陷：gff_hierarchy_inconsistent；文件级原因标签：gff_hierarchy_error。

- Parent 均存在且类型、seqid、strand 一致，唯该 CDS 的包含失败；全部 CDS protein_id 与 FAA 记录双向精确连接通过。
- GFF 41 条非注释特征记录、CDS 17 行、unique CDS ID 3、unique protein_id 3、FAA 3 条和 832 residues 均已实际遍历；字面统计一致。
- 不确定性：越界事实确定；公开文件不能证明 CDS 坐标或父记录哪一项应修正，也不能推断历史上游事故。

### R006

判定：block；缺陷：gff_reference_unresolved；文件级原因标签：gff_hierarchy_error。

- 全部 CDS protein_id 与 FAA 记录双向精确连接通过；其余可解析 Parent 边的类型、seqid、strand 和包含检查通过。
- partial=true 出现在 GFF 行 2, 3, 4, 5, 8, 9, 10, 11；该属性本身不阻断，也不豁免 Parent/蛋白连接合同。
- GFF 12 条非注释特征记录、CDS 4 行、unique CDS ID 2、unique protein_id 2、FAA 2 条和 726 residues 均已实际遍历；字面统计一致。
- 不确定性：可确认 Parent 未解析；未提供生成日志或权威目标映射，不能断言这是上游重命名还是漏写记录。root_cause 的 id_mismatch 与 gff_hierarchy_error 标签存在语义重叠，本审查选后者表达结构引用错误。

### R007

判定：pass；缺陷：none；文件级原因标签：none。

- 全记录检查 10 条 Parent 边均通过存在性、类型、seqid、strand 与闭区间包含；全部 CDS 行及全部 FAA 双向精确连接通过。
- partial=true 出现在 GFF 行 2, 3, 4, 5, 8, 9, 10, 11；该属性本身不阻断，也不豁免 Parent/蛋白连接合同。
- GFF 12 条非注释特征记录、CDS 4 行、unique CDS ID 2、unique protein_id 2、FAA 2 条和 726 residues 均已实际遍历；字面统计一致。
- 范围内合同判定无未决不确定性；未对范围外生物学质量作判断。

### R008

判定：pass；缺陷：none；文件级原因标签：none。

- 全记录检查 38 条 Parent 边均通过存在性、类型、seqid、strand 与闭区间包含；全部 CDS 行及全部 FAA 双向精确连接通过。
- GFF 40 条非注释特征记录、CDS 17 行、unique CDS ID 3、unique protein_id 3、FAA 3 条和 741 residues 均已实际遍历；字面统计一致。
- 范围内合同判定无未决不确定性；未对范围外生物学质量作判断。

### R009

判定：pass；缺陷：none；文件级原因标签：none。

- 全记录检查 10 条 Parent 边均通过存在性、类型、seqid、strand 与闭区间包含；全部 CDS 行及全部 FAA 双向精确连接通过。
- partial=true 出现在 GFF 行 2, 3, 4, 5, 8, 9, 10, 11；该属性本身不阻断，也不豁免 Parent/蛋白连接合同。
- GFF 12 条非注释特征记录、CDS 4 行、unique CDS ID 2、unique protein_id 2、FAA 2 条和 476 residues 均已实际遍历；字面统计一致。
- 范围内合同判定无未决不确定性；未对范围外生物学质量作判断。

### R010

判定：pass；缺陷：none；文件级原因标签：none。

- 全记录检查 24 条 Parent 边均通过存在性、类型、seqid、strand 与闭区间包含；全部 CDS 行及全部 FAA 双向精确连接通过。
- GFF 26 条非注释特征记录、CDS 10 行、unique CDS ID 3、unique protein_id 3、FAA 3 条和 3044 residues 均已实际遍历；字面统计一致。
- 范围内合同判定无未决不确定性；未对范围外生物学质量作判断。

### R011

判定：pass；缺陷：none；文件级原因标签：none。

- 全记录检查 20 条 Parent 边均通过存在性、类型、seqid、strand 与闭区间包含；全部 CDS 行及全部 FAA 双向精确连接通过。
- GFF 22 条非注释特征记录、CDS 8 行、unique CDS ID 2、unique protein_id 2、FAA 2 条和 1826 residues 均已实际遍历；字面统计一致。
- 范围内合同判定无未决不确定性；未对范围外生物学质量作判断。

### R012

判定：block；缺陷：gff_hierarchy_inconsistent；文件级原因标签：gff_hierarchy_error。

- Parent 均存在且类型、seqid、strand 一致，唯该 CDS 的包含失败；全部 CDS protein_id 与 FAA 记录双向精确连接通过。
- GFF 22 条非注释特征记录、CDS 8 行、unique CDS ID 2、unique protein_id 2、FAA 2 条和 1826 residues 均已实际遍历；字面统计一致。
- 不确定性：越界事实确定；公开文件不能证明 CDS 坐标或父记录哪一项应修正，也不能推断历史上游事故。

### R013

判定：block；缺陷：gff_faa_link_missing；文件级原因标签：id_mismatch。

- 其余全部 Parent 边检查通过。数值上 unique CDS ID、unique protein_id 与 FAA 记录数相等，但键集合不相等。
- GFF 26 条非注释特征记录、CDS 10 行、unique CDS ID 3、unique protein_id 3、FAA 3 条和 3044 residues 均已实际遍历；字面统计一致。
- 不确定性：确定存在精确连接键不一致；无法仅凭公开文件判断 GFF protein_id 还是 FAA header 才是应保留的正确标识，也无法推断上游生成过程。

### R014

判定：block；缺陷：gff_reference_unresolved；文件级原因标签：gff_hierarchy_error。

- 全部 CDS protein_id 与 FAA 记录双向精确连接通过；其余可解析 Parent 边的类型、seqid、strand 和包含检查通过。
- GFF 20 条非注释特征记录、CDS 8 行、unique CDS ID 2、unique protein_id 2、FAA 2 条和 1130 residues 均已实际遍历；字面统计一致。
- 不确定性：可确认 Parent 未解析；未提供生成日志或权威目标映射，不能断言这是上游重命名还是漏写记录。root_cause 的 id_mismatch 与 gff_hierarchy_error 标签存在语义重叠，本审查选后者表达结构引用错误。

