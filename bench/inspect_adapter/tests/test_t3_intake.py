"""Reproduction integrity must establish parity, not manufacture approval."""
import shutil

import pytest
from bench.inspect_adapter import t3_intake as intake, t3_packets as p


@pytest.fixture
def returned(tmp_path):
    original=p.ROOT.parent/'v4/incoming/inspect_t3_cases_reproduction/bundle'
    # Tests also run in clean public checkouts with no user's incoming folder.
    if original.exists():
        shutil.copytree(original,tmp_path/'bundle')
    else:
        root=tmp_path/'bundle'
        for name in p.read_json(p.DIRECTORY/'CASE_MANIFEST.json')['files']:
            target=root/'cases'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((p.DIRECTORY/'cases'/name).read_bytes())
        p.write_json(root/'RECEIPT.json',p.read_json(p.DIRECTORY/'LINUX_REPRODUCTION.json')['server_receipt'])
        p.write_json(root/'MANIFEST.json',{'algorithm':'sha256','files':{
            q.relative_to(root).as_posix():p.digest(q.read_bytes()) for q in root.rglob('*') if q.is_file()}})
    return tmp_path/'bundle'


def test_exact_reproduction_does_not_approve_or_freeze_answers(returned):
    result=intake.verify(returned)
    assert result['case_count']==14 and result['case_files']==84 and result['differences']==0
    assert not result['answer_approval'] and not result['answers_frozen']
    assert result['source_rescans']==result['api_calls']==0


def test_changed_bytes_and_missing_payload_rejected(returned):
    path=returned/'cases/t3_001/artifacts/models.gff3'
    path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='transport manifest'):
        intake.verify(returned)
    path.unlink()
    with pytest.raises(ValueError,match='missing'):
        intake.verify(returned)


def test_self_consistent_changed_answer_still_cannot_pass_windows_parity(returned):
    path=returned/'cases/t3_001/expected.json'
    expected=p.read_json(path)
    expected['rationale']='test alteration, not a benchmark answer'
    p.write_json(path,expected)
    manifest=p.read_json(returned/'MANIFEST.json')
    manifest['files']['cases/t3_001/expected.json']=p.digest(path.read_bytes())
    p.write_json(returned/'MANIFEST.json',manifest)
    with pytest.raises(ValueError,match='Windows reference'):
        intake.verify(returned)


def test_manifest_escape_and_forged_builder_rejected(returned):
    manifest=p.read_json(returned/'MANIFEST.json')
    altered={**manifest,'files':{**manifest['files'],'../outside':'0'*64}}
    p.write_json(returned/'MANIFEST.json',altered)
    with pytest.raises(ValueError,match='unsafe'):
        intake.verify(returned)
    p.write_json(returned/'MANIFEST.json',manifest)
    receipt=p.read_json(returned/'RECEIPT.json');receipt['builder_sha256']='0'*64
    p.write_json(returned/'RECEIPT.json',receipt)
    manifest['files']['RECEIPT.json']=p.digest((returned/'RECEIPT.json').read_bytes())
    p.write_json(returned/'MANIFEST.json',manifest)
    with pytest.raises(ValueError,match='implementation'):
        intake.verify(returned)
