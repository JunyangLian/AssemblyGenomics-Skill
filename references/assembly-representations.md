# 交付表示（assembly representations）

`delivery.representation` 决定整条交付路线，因此**必须显式声明**。未声明或为 `unresolved` 时 `validate_project.py` 与 `plan.py` 均阻断，不静默假定（D-003）。

## 枚举与含义

| 值 | 含义 | 前提/证据要求 |
|---|---|---|
| `primary_reference` | 主参考组装（默认立场） | 无分相声明；不得冒充分相结果 |
| `primary_alternate` | 主 + alternate 两组装 | 需 alternate 证据 |
| `selected_phased_haplotype` | 选定单套分相单倍型交付 | 需分相证据 + 选择依据 |
| `all_phased_haplotypes` | 全部分相单倍型交付（如 hap1+hap2） | 需分相证据；hap 数据/命名不得串用 |
| `subgenome_resolved` | 亚基因组分辨交付（多倍体） | 需亚基因组证据；路径未验证即阻断 |
| `unresolved` | 未决——**阻断状态**，不是合法交付目标 | 澄清后重路由 |

## 默认立场

未声明时默认倾向 `primary_reference`，但**默认倾向 ≠ 静默假定**：仍须用户显式确认后才路由。

## phased 交付的规则

- 分相主张需专门证据支持（亲本数据、Hi-C 分相、purge_dups/haplotig 证据等），`ploidy_evidence` 与 `parental_identity_required` 字段承载：后者为 true 时强制要求亲本角色文库独立存在。
- hap1/hap2 数据与命名不得串用；`validate_review.py` 会识别 liftover 归属与 hap 标注不一致。
- 合法拆分不强制 ID 集合完全不变，但覆盖/缺失/重复/变更须逐项可解释。

## 冻结首例口径

use-case-001 的交付要求是**单倍型交付**（每个 hap 独立一轮 Juicer+3D-DNA 挂载），已由用户确认写入 `docs/use-case-001.md`。
