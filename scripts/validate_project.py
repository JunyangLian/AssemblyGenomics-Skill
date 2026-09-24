#!/usr/bin/env python3
"""校验 project.yaml / project.json 是否符合 schema 及跨字段安全规则。

用法:
    python validate_project.py <project.yaml-or.json> [--schema schemas/project.schema.json]

返回 0 表示通过；非 0 表示存在阻断项。阻断项打印为 key path + 原因。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


def load_document(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SystemExit(f"[error] 无法读取 {path}: {e}")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise SystemExit(f"[error] YAML/解析失败 {path}: {e}")
    if not isinstance(data, dict):
        raise SystemExit(f"[error] {path} 根节点必须是对象，得到 {type(data).__name__}")
    return data


def load_schema(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SystemExit(f"[error] 无法加载 schema {path}: {e}")


def schema_errors(data: dict, schema: dict) -> list[str]:
    validator = Draft202012Validator(schema)
    return [f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
            for e in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))]


def cross_field_errors(data: dict) -> list[str]:
    """跨字段安全规则：不兼容组合、资源缺失、角色约束。"""
    errs: list[str] = []

    delivery = data.get("delivery") or {}
    if "representation" not in delivery or delivery.get("representation") in (None, "unresolved"):
        errs.append("delivery.representation: 未声明或为 unresolved，需人工澄清交付表示（不允许静默假定）")

    execution = data.get("execution") or {}
    backend = execution.get("backend")
    if backend == "remote_agent" and execution.get("allow_remote_upload") is not False:
        errs.append("execution.allow_remote_upload: remote_agent 后端默认不允许远程上传，须显式保持 false（首版不放行）")

    limits = ["cpu_limit", "memory_gb_limit", "disk_gb_limit"]
    if execution.get("backend") in ("sop_package", "remote_agent"):
        missing = [k for k in limits if execution.get(k) in (None, "")]
        if missing:
            errs.append(f"execution.{','.join(missing)}: 正式运行须声明资源上限（缺一即阻断）")

    inputs = data.get("inputs") or {}
    libraries = inputs.get("libraries") or []
    proband_assembly = 0
    proband_rna = 0
    parent_role_seen = False
    for lib in libraries:
        role = lib.get("sample_role")
        if role == "proband":
            # RNA-seq 复用同一 proband 是合法的重复证据（酵母 2 对、Siganus 30 对）；
            # 多 proband 冲突只针对组装源文库（wgs/hic）。
            if lib.get("library_type") == "rna_seq":
                proband_rna += 1
            else:
                proband_assembly += 1
        elif role == "parent":
            parent_role_seen = True
        if role is None:
            errs.append(f"inputs.libraries[].sample_role: 文库 {lib.get('library_id', '?')} 未声明样本角色")

    if proband_assembly + proband_rna == 0 and libraries:
        errs.append("inputs.libraries: 至少需要一个 proband 角色文库")
    if proband_assembly > 1:
        errs.append(f"inputs.libraries: 混样或来源冲突，组装源文库（wgs/hic）proband 多于 1 个（{proband_assembly}），需人工方案审核")

    if delivery.get("parental_identity_required"):
        if not parent_role_seen:
            errs.append("delivery.parental_identity_required: 需要亲本身份，但 inputs.libraries 无 parent 角色文库")

    return errs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("doc", help="project.yaml / project.json 路径")
    parser.add_argument("--schema", default=str(Path(__file__).resolve().parent.parent / "schemas" / "project.schema.json"),
                        help="schema 路径（默认取自本项目 schemas 目录）")
    args = parser.parse_args(argv)

    doc_path = Path(args.doc)
    schema_path = Path(args.schema)
    data = load_document(doc_path)
    schema = load_schema(schema_path)

    errs = schema_errors(data, schema)
    errs += cross_field_errors(data)

    if errs:
        print("[blocked] 项目配置校验未通过，共 %d 项阻断：" % len(errs))
        for e in errs:
            print("  - " + e)
        return 1

    print("[ok] 项目配置校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())