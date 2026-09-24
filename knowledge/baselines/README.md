# 文献基线（Literature Baselines）

回答一个新手最容易漏掉的问题：**"我这个数正常吗？"**

机制来源（用户洞察，D-015/D-016）：绝大多数物种类群的关键指标（基因数、BUSCO 完整度、
重复屏蔽比例、注释覆盖率……）有大量发表先例。除少数特殊情况（多倍化、超紧凑基因组、
极端 TE 膨胀），**与可比先例差距悬殊几乎必然有问题**——但新手没有文献量，不知道
"正常长什么样"。

本 skill 面向**所有基因组**，因此基线不是预填充的全局表，而是双层结构（D-016）：

## 双层结构

| 层 | 来源 | 权威性 | 何时确定 |
|---|---|---|---|
| **项目级锚点** | intake 确定数据来源时，选定该物种/属最近的已发表同类（发表注释、组装、基因组大小记录），写入 `project.yaml` 的 `baselines` 节 | 权威；`metric_overrides` 可 enforce（范围外按 GAP 报警） | **项目开始时**（与选 BUSCO lineage 同一动作） |
| **类群兜底带** | `knowledge/baselines/*.yaml` 全局注册表（真实案例种子逐步生长） | advisory；仅提示不强制 | 兜底：项目未覆盖的指标退回这里 |

项目未选定锚点**不阻断路由**，但对照输出会明示"仅类群兜底带"，最终报告必须如实标注——
不静默假定有锚。这正是"未声明不假定"纪律（D-003）在基线上的同构。

## 与陷阱库（pitfalls）的关系

- pitfalls 探测**过程**中的静默缺口（库版本、参数、文件格式）——问"这步做对了吗"。
- baselines 探测**结果**的合理性——问"这个数像话吗"。两者正交互补。

## 条目格式（YAML）

```yaml
id: BASE-001
metric: protein_coding_gene_count     # 规范指标名（见下表）
taxon_scope: actinopterygii           # 适用类群；any 表示不限
unit: genes
expected_range: [15000, 45000]
source_type: case_reference           # case_reference | published
enforce: false                        # true = 范围外按 warning 报警
references:                           # published 必须 ≥2 条且带 doi/url
  - text: "Siganus canaliculatus 交付 23,924 编码基因（本项目 use-case-002）"
    doi: null
notes: >
  偏离的常见合法原因与非法原因。
```

## enforce 的两档门槛（代码强制）

- **全局注册表条目** enforce=true：必须 `source_type=published` 且 ≥2 条带 doi/url——
  全局带声称的是类群普遍规律，单篇文献不够。
- **项目级 metric_overrides** enforce=true：须有 `based_on` 且项目已给 references
  （schema 保证每条 reference 带 accession_or_doi）——intake 选锚是明确的人类决策，
  1 条锚即可强制。

## 规范指标名

| metric | 含义 | 典型来源 |
|---|---|---|
| `protein_coding_gene_count` | 编码基因数（coding-only 交付口径） | GFF3 gene 计数（PIT-005 清洗后） |
| `annotation_busco_complete_pct` | 注释蛋白 BUSCO 完整度（proteins 模式） | BUSCO short_summary |
| `repeat_masked_pct` | 软屏蔽小写碱基比例 | PIT-006 的 lowercase 统计 |
| `median_protein_length_aa` | 蛋白长度中位数（aa） | 交付 pep.fa |
| `functional_any_annotated_pct` | 功能注释任一命中覆盖率 | use-case-002 第 8 步统计 |

## 使用

```bash
# 项目已选锚点（权威）：--project 读 project.yaml 的 baselines 节
python scripts/check_baselines.py --project project.yaml --taxon actinopterygii \
  protein_coding_gene_count=23924 annotation_busco_complete_pct=97.4

# 无项目锚点（兜底）：明示"仅类群兜底带"
python scripts/check_baselines.py --taxon actinopterygii protein_coding_gene_count=23924
```

## 全局注册表的扩充方式

首版种子全部来自本项目 Siganus 真实案例（`case_reference`，advisory），按**真实案例**
逐步生长（与陷阱库同一纪律：不预先堆投机条目）。升为 `published`/enforce 的流程：
查 ≥2 篇同类群发表文献 → 填范围与 doi → 改 `source_type: published`、`enforce: true`。
**不允许凭记忆填文献数值**——每条 published 范围都必须能点开引用核对。
日常优先级则是**项目级锚点**：每个新项目的 intake 都应产出自己的锚，而不是等全局表覆盖。
