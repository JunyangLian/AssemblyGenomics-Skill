#!/usr/bin/env python3
"""把本仓库打包为可安装的 Copilot 技能包，支持两种 Agent 格式。

Codex（默认，--format codex）：
  assembly-genomics/
    AGENTS.md            # 全局指令（放 ~/.codex/AGENTS.md，每次会话自动携带）
    commands/assembly-genomics.md   # slash 命令（放 ~/.codex/commands/，按需触发）
    scripts/ knowledge/ references/ schemas/ templates/ sop/ docs/ …  # 资产
  --install 时：AGENTS.md 放到 ~/.codex/；命令文件放到 ~/.codex/commands/
  （若 ~/.codex/AGENTS.md 已存在则拒绝覆盖，提示手工合并）

ZCode（备选，--format zcode）：
  <name>/SKILL.md + references/ + scripts/ + …（放进 ~/.zcode/skills 或 ~/.agents/skills）

用法:
    python scripts/package_skill.py                     # 默认 codex 格式
    python scripts/package_skill.py --format zcode
    python scripts/package_skill.py --install           # 打包并安装（codex → ~/.codex）
    python scripts/package_skill.py --dest DEST         # 自定义安装目录
    python scripts/package_skill.py --version x.y.z
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "assembly-genomics"

PACKAGE_ITEMS = [
    "SKILL.md", "README.md", "LICENSE",
    "references", "schemas", "scripts", "knowledge",
    "templates", "sop", "docs", "workflows", "pytest.ini",
]
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git", ".stale", "runs", "dist"}

AGENTS_MD = """# AssemblyGenomics 技能指令（AGENTS.md）

本文件把 "AssemblyGenomics Skill" 的方法论注入每一次会话：
**帮助新手搭建第一套属于自己的基因组组装/注释流水线**——但更根本的，
是捕获"能跑通但不完整"的静默缺口（silent gap），并回答"这个数正常吗"。

## 不可逾越的硬约束（与代码层校验一致）

1. 交付表示（delivery.representation）必须显式声明；未声明/为 unresolved 时阻断澄清，不得静默假定。
2. 人类批准二要素缺一不可：approved_by_human=true 且 submission_action 非空。LLM 不能代写"已审核"，不能复用旧版 hash 的批准。
3. 状态以磁盘结构化记录为准，不以对话历史为准；禁止无界重试；失败保留现场、不伪造完成标记。
4. 硬阻断场景直接停：缺 R2、错误文库类型、样本角色冲突、多倍体路径未验证、只有 Hi-C 无组装源。告知缺什么、能做什么。
5. 失败/缺失如实报告；"未评估/不适用/执行失败"是合法输出，不得包装成通过。
6. 不臆断环境：探测不到的能力标记"需人工/需服务器"，不宣称已验证。
7. 资源预算（线程/内存/磁盘）必须显式向用户确认后才写入配置，不得沿用默认/上一项目数值（共享服务器纪律）。
8. 工具 CLI 参数必须按目标版本实测核对（--help/官方文档），禁止凭记忆拼参数；兜底分支不得与管道同用。
9. 发送给用户的指令禁止裸 rm -f/rm -rf + 通配符；删除一律先 ls 展示现状、点名到文件。

## 工作循环（backend A：SOP 包模式）

intake（数据识别 + 选文献基线锚点）→ preflight（探测环境，SGE 非 SLURM）→
validate_project（schema + 跨字段安全规则）→ plan（路由 + 流程步 + 人工门）→
SOP 生成（每步挂坑位预警；budget 先确认）→ 服务器执行 → 回传校验（hash 绑定 +
陷阱检查 + 基线对照）→ 如实报告 → 毕业包（可复用 SOP 沉淀）。

## 入口与脚本速查

- 新手入口：`python scripts/skill_coach.py <files...> [--repr X] [--ploidy N]`
- 校验：`python scripts/validate_project.py <project.yaml>`
- 路由：`python scripts/plan.py <project.yaml>`
- 审核：`python scripts/validate_review.py <review.json>`（阻断 exit 1）
- 报告：`python scripts/summarize_results.py --project p.json --products prod.json`
- 陷阱：`python scripts/run_pitfall_checks.py [--dir knowledge/pitfalls]`
- 基线：`python scripts/check_baselines.py --project project.yaml metric=value ...`
- 打包：`python scripts/package_skill.py [--format codex|zcode] [--install]`
- 深层阅读：`references/`（路由/表示/门控）、`knowledge/pitfalls/`（真实陷阱）、
  `knowledge/baselines/`（类群兜底带）、`docs/use-case-00*.md`（真实案例实录与边界）、
  `sop/yeast_loop/`（四段可复用毕业包 + 冻结 settings + 检查点）

## 验证与边界（写结论时必须声明层）

- 配置/模拟层：117 tests 全绿（pytest）
- 真实案例：酵母机制环四段（重复注释→RNA 比对→结构 BUSCO 99.0%→功能 Any 99.96%）
- 未验证：从原始读段组装、ETP 蛋白环（GeneMark-ETP git 版缺陷，走 ET 模式并记录）、
  多倍体/分相交付、长读路线。详见 docs/capability_matrix.md。
"""

COMMAND_MD = """---
description: 基因组组装/注释 Copilot 入口（AssemblyGenomics Skill）——识别数据、定路由、生成带坑位预警的分步 SOP。触发词：基因组组装、注释、Hi-C、BUSCO、重复序列、基因预测。
argument-hint: [文件清单] [--repr 交付表示]
---

你是 AssemblyGenomics Skill 的执行者。方法论与硬约束见本技能包根目录的 AGENTS.md
（若已装入 ~/.codex/AGENTS.md 则自动生效）。步骤：

1. 用数据文件名跑新手入口（包内 scripts/skill_coach.py）：
   `python "{PKG}/scripts/skill_coach.py" {ARGUMENTS}`
2. 原样转述识别结果、路由意图与阻断原因；把坑位预警（knowledge/pitfalls/ 内容）
   逐条转述，不软化。
3. 若需要继续：按 AGENTS.md 的工作循环走 validate_project → plan → SOP 生成，
   记得先向用户确认线程/内存/磁盘预算（共享服务器纪律）。
4. 引用能力与边界时，以 docs/capability_matrix.md 与 use-case 实录为准，不得升级。
"""


def git_version() -> str:
    try:
        out = subprocess.run(["git", "describe", "--tags", "--always"],
                             capture_output=True, text=True, cwd=str(ROOT))
        return (out.stdout or "").strip() or "1.0.0"
    except Exception:
        return "1.0.0"


def collect() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for item in PACKAGE_ITEMS:
        p = ROOT / item
        if not p.exists():
            continue
        if p.is_file():
            files.append((p, f"{NAME}/{item}"))
            continue
        for f in sorted(p.rglob("*")):
            if f.is_file() and not any(part in SKIP_DIRS for part in f.parts):
                files.append((f, f"{NAME}/{f.relative_to(ROOT).as_posix()}"))
    return files


def generated(fmt: str) -> dict[str, bytes]:
    if fmt == "zcode":
        return {}
    return {
        f"{NAME}/AGENTS.md": AGENTS_MD.encode("utf-8"),
        f"{NAME}/commands/{NAME}.md": COMMAND_MD.replace(
            "{PKG}", "~/.codex/" + NAME).replace("{ARGUMENTS}", "{ARGUMENTS}").encode("utf-8"),
    }


def build_zip(version: str, fmt: str) -> Path:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    suffix = "" if fmt == "codex" else ".zcode"
    out = dist / f"{NAME}-{version}{suffix}.zip"
    files = collect()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, arc in files:
            zf.write(src, arc)
        for arc, data in generated(fmt).items():
            zf.writestr(arc, data)
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
        assert names, "empty package"
        if fmt == "codex":
            assert f"{NAME}/AGENTS.md" in names, "AGENTS.md missing"
            assert f"{NAME}/commands/{NAME}.md" in names, "command missing"
        else:
            sk = zf.read(f"{NAME}/SKILL.md").decode("utf-8", errors="replace")
            assert sk.lstrip("\ufeff").startswith("---"), "SKILL.md frontmatter missing"
    print(f"[OK] 打包完成：{out}（{len(files) + (2 if fmt == 'codex' else 0)} 个文件，{fmt} 格式）")
    return out


def install(zip_path: Path, dest: Path, fmt: str) -> None:
    if fmt == "zcode":
        target = dest / NAME
        if target.exists():
            raise SystemExit(f"[停止] 目标已存在：{target}——先移除旧安装再重装（不覆盖）")
        target.mkdir(parents=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest)
        print(f"[OK] 已安装到 {target}（ZCode：~/.zcode/skills 或 ~/.agents/skills）")
        return
    # codex：AGENTS.md → dest/AGENTS.md；commands → dest/commands/；资产 → dest/<NAME>/
    agents = dest / "AGENTS.md"
    if agents.exists():
        raise SystemExit(f"[停止] {agents} 已存在——为不覆盖你的既有全局指令，请手工合并 AGENTS.md 内容后再安装")
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "commands").mkdir(parents=True, exist_ok=True)
    pkg_dir = dest / NAME
    if pkg_dir.exists():
        raise SystemExit(f"[停止] 资产目录已存在：{pkg_dir}——先移除旧资产再重装")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    agents.write_bytes(AGENTS_MD.encode("utf-8"))
    cmd_src = pkg_dir / "commands" / f"{NAME}.md"
    if cmd_src.exists():
        shutil.copyfile(cmd_src, dest / "commands" / f"{NAME}.md")
    print("[OK] Codex 安装完成：")
    print(f"  AGENTS.md → {agents}")
    print(f"  命令      → {dest / 'commands' / (NAME + '.md')}")
    print(f"  资产      → {pkg_dir}（scripts/knowledge/references…）")
    print(f"验证：新开会话输入 /{NAME} 触发；或直接描述组装/注释任务自动套用方法论")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--format", choices=("codex", "zcode"), default="codex",
                    help="打包格式（默认 codex：AGENTS.md + commands，适配 Codex CLI）")
    ap.add_argument("--version", default=None, help="版本号（默认读 git tag）")
    ap.add_argument("--install", action="store_true", help="打包后直接安装")
    ap.add_argument("--dest", default=None,
                    help="安装目录（codex 默认 ~/.codex；zcode 默认 ~/.agents/skills）")
    args = ap.parse_args()
    version = args.version or git_version()
    fmt = args.format
    dest = Path(args.dest) if args.dest else (
        Path.home() / ".codex" if fmt == "codex" else Path.home() / ".agents" / "skills")
    zf = build_zip(version, fmt)
    if args.install:
        install(zf, dest, fmt)
    return 0


if __name__ == "__main__":
    sys.exit(main())