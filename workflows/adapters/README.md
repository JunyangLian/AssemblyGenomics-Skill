# workflows/adapters: Nextflow process 适配器骨架

M1 阶段这些适配器**只定义 input/output 通道约定与版本固定说明**，用于确认打包约定，不包含任何真实组装 process。真实 Juicer/3D-DNA 与 YaHS 两条组装适配器由 M2 填充。

每条适配器须在 SKILL.md 或引用中声明：输入通道、输出通道、工具版本固定、以及"不做无损假设"的约束。特别地，**BAM 不默认等于 HiFi**——适配器不得把任意 BAM 当成 HiFi 组装源，须由元数据（technology_source）佐证。

## 目录约定（M2 填充时）

- `juicer_3ddna/`：Juicer + 3D-DNA + Juicebox 人工调图路线（haplotype-aware）
- `yahs_jbat/`：YaHS + JBAT 路线

每个子目录预留：`adapter.nf`（通道约定）、`versions.json`（版本锁定）、`README.md`（输入/输出通道契约）。