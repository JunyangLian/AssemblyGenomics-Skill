import shutil

import pytest

from bench.inspect_adapter import t3_freeze as freeze
from bench.inspect_adapter import t3_packets as packets


@pytest.fixture
def directory(tmp_path):
    target = tmp_path / 't3_test'
    shutil.copytree(freeze.DIRECTORY, target)
    for name in ('FROZEN.json', 'FROZEN.md'):
        (target / name).unlink(missing_ok=True)
    return target


def test_freeze_preserves_reproduced_bytes_and_is_idempotent(directory):
    before = {p: p.read_bytes() for p in (directory / 'cases').rglob('*') if p.is_file()}
    first = freeze.freeze(directory)
    assert first['api_call_authorized'] is False
    assert freeze.freeze(directory) == first
    assert all(p.read_bytes() == data for p, data in before.items())
    assert len([n for n in first['files'] if n.endswith('/expected.json')]) == 14


@pytest.mark.parametrize('name', ['cases/t3_001/expected.json', 'system.txt'])
def test_verify_rejects_gold_or_public_contract_tampering(directory, name):
    freeze.freeze(directory)
    path = directory / name
    path.write_bytes(path.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='frozen bytes changed'):
        freeze.verify(directory)


def test_requires_human_answer_approval_and_rejects_extra_visible_file(directory):
    approval = packets.read_json(directory / 'APPROVAL.json')
    approval['answers_approved'] = False
    packets.write_json(directory / 'APPROVAL.json', approval)
    with pytest.raises(ValueError, match='approval required'):
        freeze.freeze(directory)
    approval['answers_approved'] = True
    packets.write_json(directory / 'APPROVAL.json', approval)
    freeze.freeze(directory)
    (directory / 'cases/t3_001/artifacts/extra.txt').write_bytes(b'extra\n')
    with pytest.raises(ValueError, match='unexpected case file'):
        freeze.verify(directory)
