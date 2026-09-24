#!/usr/bin/env python3
"""把本仓库打包为可安装的 ZCode skill 包（<name>/SKILL.md 形态）。

用法:
    python scripts/package_skill.py                 # 生成 dist/<name>-<ver>.zip
    python scripts/package_skill.py --install       # 生成并安装到 ~/.agents/skills/<name>
    python scripts/package_skill.py --dest DEST     # 指定安装目录（如 ~/.zcode/skills）
    python scripts/package_skill.py --version x.y.z # 覆盖版本号（默认读 git tag，回退 1.0.0）

安装后验证：新开会话输入 /skill assembly-genomics 应能加载。
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "assembly-genomics"

# 安装包内容（skill 运行时需要的全部；tests/.git 等开发资产不进包）
PACKAGE_ITEMS = [
    "SKILL.md", "README.md", "LICENSE",
    "references", "schemas", "scripts", "knowledge",
    "templates", "sop", "docs", "workflows", "pytest.ini",
]

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git", ".stale", "runs", "dist"}


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


def build_zip(version: str) -> Path:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    out = dist / f"{NAME}-{version}.zip"
    files = collect()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, arc in files:
            zf.write(src, arc)
    # 校验：包内 SKILL.md 可解析 frontmatter
    with zipfile.ZipFile(out) as zf:
        data = zf.read(f"{NAME}/SKILL.md").decode("utf-8")
        assert data.lstrip("﻿").startswith("---"), "SKILL.md frontmatter missing"
        assert "name:" in data.split("---", 2)[1], "frontmatter name missing"
    print(f"[OK] 打包完成：{out}（{len(files)} 个文件）")
    return out


def install(zip_path: Path, dest: Path) -> None:
    target = dest / NAME
    if target.exists():
        raise SystemExit(f"[停止] 目标已存在：{target}——先移除旧安装再重装（不覆盖）")
    target.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            zf.extract(member, dest)
    print(f"[OK] 已安装到 {target}")
    print("验证：新开会话，用 /skill 触发（description 里写了触发词），或直接 /skill assembly-genomics")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", default=None, help="版本号（默认读 git tag）")
    ap.add_argument("--install", action="store_true", help="打包后直接安装")
    ap.add_argument("--dest", default=str(Path.home() / ".agents" / "skills"),
                    help="安装目录（默认 ~/.agents/skills）")
    args = ap.parse_args()
    version = args.version or git_version()
    zf = build_zip(version)
    if args.install:
        install(zf, Path(args.dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())