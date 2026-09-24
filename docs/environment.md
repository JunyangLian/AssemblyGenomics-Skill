# 环境说明

记录本项目所需环境的探测与配置约定。正式运行目标为 Linux 服务器；当前为本地开发环境。

## 本地开发环境（当前）
- 系统：Windows 11 Home China
- Python：3.10.11（TRAE 虚拟工具环境）
- 依赖：jsonschema、PyYAML、pytest（见 technology_registry.md）
- 用途：Skill 调度、schema 校验、状态机与审核门槛测试、Juicebox 人工调图（本地）

## 服务器环境（M0 待确认，未提供）
以下信息缺失，不得沿用其他项目的资源预算假设：
- 操作系统 / 调度器（SLURM/PBS/无）
- CPU 核数、RAM、磁盘与配额
- 容器权限、网络策略
- 现有脚本与工具版本、成功案例

拿到服务器信息后，由 preflight 探测并写入本文件。

## 真实服务器信息（来自 use-case-001 脚本，2026-09-21 首次确认）

> 来源：`02.HIC/SM4-hap1/` 下 `.task.sh` 与 `shell/*` 中硬编码的调度命令与资源。这是首个真实环境事实，据此修正"SLURM"的先前假设。

- **调度器：SGE**（`qsub-sge.pl --queue bc.q`，`--resource "num_proc=..,vf=..G -binding linear:.."`）。**非 SLURM**——此前 use-case 默认写 SLURM，已修正。
- **用户**：`USER`，组 `GROUP`。参考主代码位于 `${HOME}/Grape/02.HIC/New_Template/`。
- **数据根**：`${DATA}/Grape-001/` 与 `${HOME}/Grape/Grape-001.putao/`（含原始 HIC 读段 `SM-4_hic_all_1/2.fq.gz`）。
- **真实资源硬编码（可作参考，非预算承诺）**：
  - bwa mem 比对：`num_proc=32, vf=54G, linear:32`
  - 3d-dna：`num_proc=20, vf=25G, linear:20`
- **工具以 conda env 提供**：`${SHARED}/.conda/envs/bwa/`、`${SHARED}/.conda/envs/samtools/`、`${SHARED}/.conda/envs/java8/`；3D-DNA 在 `${HOME}/env/3D-DNA/`；Juicer 辅助脚本在 `${HOME}/env/Juicer/`。
- **酶切**：DpnII，切点序列 GATCGATC（`generate_site_positions.py` / `fragment.pl` 用）。
- **调度命令** Bash 手写的 `qsub-sge.pl` 包装（非原生 qsub），脚本在 `shell/*.sh`。

### 对 preflight 的修正
- preflight 需识别 **SGE (qsub-sge.pl / qsub)**，不能只认 SLURM/PBS。
- 工具探测需覆盖 `$HOME/.conda/envs/<tool>/bin` 与 `${HOME}/env/*`，不只靠 `which`。
- 资源参考阈值（54G/32 核）仅供预算占位，真实值由用户在预检确认。
## 服务器网络与数据获取策略（D-017，2026-09-22 实测确立）

- **规则：境内镜像优先，国外兜底**（用户明确指示）。服务器直连国外实测 ~400-800 KB/s。
- 各数据源境内可用性盘点（随使用更新）：

| 数据源 | 境内镜像 | 状态 |
|---|---|---|
| NCBI RefSeq/genomes | CNGB `https://ftp.cngb.org/pub/NCBI/`（另 NGDC/BIGD 候选） | 待验证（SRA 下载时先试） |
| UniProt | 未发现可靠境内镜像 | 国外直连（已实测可用，89 MB / 4 分钟） |
| BUSCO lineages | 未发现境内镜像 | 国外直连（单谱系几十 MB，可接受） |
| SRA 读段 | CNGB / NGDC（CNSA）候选 | 待选 run 后验证 |
| Dfam/FamDB | 服务器已装 Dfam 4.0 | 无需下载 |

- **滚动发布库的身份绑定**：UniProt 等按月滚动、无固定 md5 文件的库，以"下载时实测 sha256 + 条目数 + 下载日期 + release 版本"绑定，写入 run manifest；NCBI 等 fix release 用官方 md5checksums，且**校验命令必须与实际下载清单对齐**（教训见 error_log）。
- 酵母用例已下载（2026-09-22，直连国外）：GCF_000146045.2_R64 基因组/GFF/蛋白（NCBI 官方 md5 通过）+ Swiss-Prot fasta（sha256 a9c3496a…、575,748 条、2026-09-22，身份绑定完成）。

### 两台服务器的事实区分（2026-09-22 酵母 intake 时澄清）

| | 服务器 `server`（账户 `user`） | 服务器 `user`（账户 `USER`） |
|---|---|---|
| 已验证工具链 | Siganus 结构注释全套：`${SHARED}/env/braker3/bin/{braker.pl,busco,tsebra.py}`、BUSCO 6.1.0、AGAT env | Qatar 功能注释：`${SHARED}/.conda/envs/braker3/bin/diamond`、`${SHARED}/ann/interproscan-5.76-107.0`（共享路径） |
| 关联项目 | Siganus_self 结构注释 | grape 数据（SGE/qsub-sge.pl）、Qatar 功能注释、**yeast_test（当前）** |
| 未验证 | — | busco/braker.pl/RepeatModeler 等结构注释工具是否可用（`${SHARED}/env/braker3/bin/busco` 不存在，已实测） |

 yeast 循环在本机执行前必须先 preflight 盘点；缺什么按 D-017（境内镜像优先）补装，或整体迁往 `server` 机（数据仅 ~100 MB，迁移成本低）。

- **base 壳持久污染（反复踩，串案的根）**：`.bashrc` 会导出 PERL5LIB（braker3）+ PYTHONPATH（CPhasing-main）。一切 perl/python wrapper 直接调用都会被带偏（AGAT、busco、sra_tools 连续三次中招）。对策已固化：env 类工具一律"env 自带解释器 + 脚本绝对路径"或 `conda activate` 后显式 `unset PERL5LIB PERLLIB PERL5OPT PYTHONPATH`；本 skill 的 stage driver 已内建 PYTHONPATH 清除。
