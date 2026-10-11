"""Verify returned Linux T3 reproduction bytes, never rescan original sources."""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath

from bench.inspect_adapter import t3_packets as p


def verify(path):
    root=Path(path).resolve(strict=True)
    if (root/'bundle').is_dir():
        root=root/'bundle'
    if not (root/'MANIFEST.json').is_file():
        raise ValueError('returned manifest missing')
    manifest=p.read_json(root/'MANIFEST.json')
    if manifest.get('algorithm')!='sha256' or not isinstance(manifest.get('files'),dict):
        raise ValueError('unrecognized transport manifest')
    declared=manifest['files']
    for name,sha in declared.items():
        rel=PurePosixPath(name)
        if (not name or '\\' in name or rel.is_absolute() or '..' in rel.parts or rel.as_posix()!=name or
                not isinstance(sha,str) or len(sha)!=64):
            raise ValueError('unsafe manifest member')
        path=root/rel
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError('manifest member missing or outside bundle')
    inventory={}
    for q in root.rglob('*'):
        if q.is_symlink() or not q.resolve().is_relative_to(root):
            raise ValueError('returned inventory contains link/outside path')
        if q.is_file() and q.relative_to(root).as_posix()!='MANIFEST.json':
            inventory[q.relative_to(root).as_posix()]=q
    if set(inventory)!=set(declared):
        raise ValueError('returned payload differs from transport manifest')
    actual={name:p.digest(q.read_bytes()) for name,q in inventory.items()}
    if actual!=declared:
        raise ValueError('returned payload differs from transport manifest')
    reference_path=p.DIRECTORY/'CASE_MANIFEST.json'
    reference=p.read_json(reference_path)
    wanted={'cases/'+name:sha for name,sha in reference['files'].items()}
    if set(actual)!=set(wanted)|{'RECEIPT.json'}:
        raise ValueError('returned case inventory differs')
    if any(actual[name]!=sha for name,sha in wanted.items()):
        raise ValueError('Linux case bytes differ from Windows reference')
    # Also protect against local changes after the original Windows package.
    if any(p.digest((p.DIRECTORY/'cases'/name).read_bytes())!=sha
           for name,sha in reference['files'].items()):
        raise ValueError('local case bytes differ from Windows reference')
    receipt=p.read_json(root/'RECEIPT.json')
    for key,value in {'status':'pass','cases':14,'differences':0,'api_calls':0,'source_rescans':0,
                      'answers':'draft, not frozen'}.items():
        if receipt.get(key)!=value:
            raise ValueError('unexpected server receipt: '+key)
    expected={'builder_sha256':p.digest(Path(p.__file__).read_bytes()),
              'source_subset_sha256':p.digest((p.DIRECTORY/'selection/SOURCE_SUBSETS.json').read_bytes()),
              'reference_case_manifest_sha256':p.digest(reference_path.read_bytes())}
    if any(receipt.get(name)!=sha for name,sha in expected.items()):
        raise ValueError('server implementation/subset/reference differs')
    if not str(receipt.get('platform','')).startswith('Linux-') or not receipt.get('python'):
        raise ValueError('Linux runtime receipt missing')
    result={'status':'verified_linux_windows_parity','case_count':14,'case_files':84,'transport_payloads':85,
            'differences':0,'transport_manifest_sha256':p.digest((root/'MANIFEST.json').read_bytes()),
            'server_receipt_sha256':p.digest((root/'RECEIPT.json').read_bytes()),'server_receipt':receipt,
            'local_reference_sha256':p.digest(reference_path.read_bytes()),'api_calls':0,'source_rescans':0,
            'answer_approval':False,'answers_frozen':False,
            'scope':'same transported subsets reproduce exact case bytes; not independent source or biological validation',
            'tool_version_notice':'server receipt records Python/platform; exact installed jsonschema version not recorded'}
    return result


def save(path):
    result=verify(path)
    p.write_json(p.DIRECTORY/'LINUX_REPRODUCTION.json',result)
    print('PASS: Linux/Windows 14 cases, 84 identical files, 85 verified payloads; 0 API calls')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    save(parser.parse_args().directory)
