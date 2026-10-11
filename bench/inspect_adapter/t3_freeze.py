"""Seal the human-approved T3 gold and public contract without rewriting cases."""
from __future__ import annotations

import argparse
from pathlib import PurePosixPath

from . import t3_packets as packets

DIRECTORY = packets.DIRECTORY
CONTRACT_FILES = (
    'CASE_MANIFEST.json', 'system.txt', 'final.txt', 'GUIDANCE_SCOPE.json',
    'schemas/case_meta.schema.json', 'schemas/expected.schema.json',
    'schemas/model_output.schema.json', 'LINUX_REPRODUCTION.json',
    'reviews/COMPARISON.json', 'reviews/AI_REVIEW_ORIGINAL.zip',
)


def safe_file(directory, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError('unsafe frozen path')
    path = directory.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(directory.resolve()) or not path.is_file():
        raise ValueError('missing or escaping frozen file: ' + name)
    return path


def verify(directory=DIRECTORY):
    seal = packets.read_json(directory / 'FROZEN.json')
    if seal['version'] != 'inspect-t3-gold-1' or seal['api_call_authorized'] is not False:
        raise ValueError('unsupported gold seal or API authorization')
    required = {'cases/' + name for name in packets.read_json(directory / 'CASE_MANIFEST.json')['files']}
    required.update(CONTRACT_FILES)
    required.update(('APPROVAL.json', 'FROZEN.md'))
    if set(seal['files']) != required:
        raise ValueError('incomplete frozen inventory')
    for name, expected in seal['files'].items():
        if packets.digest(safe_file(directory, name).read_bytes()) != expected:
            raise ValueError('frozen bytes changed: ' + name)
    actual = {p.relative_to(directory / 'cases').as_posix()
              for p in (directory / 'cases').rglob('*') if p.is_file()}
    if actual != set(packets.read_json(directory / 'CASE_MANIFEST.json')['files']):
        raise ValueError('unexpected case file inventory')
    approval = packets.read_json(directory / 'APPROVAL.json')
    if approval['answers_approved'] is not True or approval['api_call_authorized'] is not False:
        raise ValueError('missing answer-only human approval')
    return seal


def freeze(directory=DIRECTORY):
    if (directory / 'FROZEN.json').exists():
        return verify(directory)
    approval = packets.read_json(directory / 'APPROVAL.json')
    if approval['answers_approved'] is not True or approval['api_call_authorized'] is not False:
        raise ValueError('explicit answer-only human approval required')
    manifest = packets.read_json(directory / 'CASE_MANIFEST.json')['files']
    expected_names = sorted(name for name in manifest if name.endswith('/expected.json'))
    if len(manifest) != 84 or len(expected_names) != 14:
        raise ValueError('expected fourteen six-file cases')
    for name, expected in manifest.items():
        if packets.digest(safe_file(directory, 'cases/' + name).read_bytes()) != expected:
            raise ValueError('case differs from reproduced bytes: ' + name)
    linux = packets.read_json(directory / 'LINUX_REPRODUCTION.json')
    if linux['differences'] != 0 or linux['case_count'] != 14:
        raise ValueError('Linux reproduction not accepted')
    text = '# T3 gold freeze 1\n\n'
    text += '2026-10-11：用户确认14份答案及 draft-2 公共合同，真实调用预算未批准。\n\n'
    text += 'APPROVAL.json 是当前授权记录。题目、CASE_MANIFEST 及历史凭据中的 draft/pending/false 字段记录生成或验收时的状态，保留原字节；不代表本次授权被撤销。不得把这些私有记录送入模型。\n\n'
    text += '标准答案与公开合同冻结独立于后续模型配置。更换模型不能修改答案；修正答案须另起版本。AI审核不记为真人专家审核。\n\n'
    text += '| expected.json | SHA-256 |\n|---|---|\n'
    text += ''.join('| cases/' + name + ' | ' + manifest[name] + ' |\n' for name in expected_names)
    text += '\n完整公开输入、schema、共同提示、范围合同及验收/审核凭据哈希见 FROZEN.json。后续运行实现另建运行封存，不能从此文件推导付费授权。\n'
    (directory / 'FROZEN.md').write_bytes(text.encode('utf-8'))
    names = sorted({'cases/' + name for name in manifest} | set(CONTRACT_FILES) |
                   {'APPROVAL.json', 'FROZEN.md'})
    seal = {'version': 'inspect-t3-gold-1', 'date': '2026-10-11',
            'answers_frozen': True, 'api_call_authorized': False, 'case_count': 14,
            'public_contract': 'draft-2',
            'files': {name: packets.digest(safe_file(directory, name).read_bytes()) for name in names}}
    packets.write_json(directory / 'FROZEN.json', seal)
    return verify(directory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = verify() if args.verify else freeze()
    print('PASS: 14 frozen T3 answers; public contract unchanged; API calls not authorized')
