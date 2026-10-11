"""AI agreement must retain provenance and must not imply human approval."""
import json
import zipfile

from bench.inspect_adapter import t3_packets as p, t3_task
from bench.inspect_adapter.readonly import PublicFiles


def test_review_original_is_byte_preserved_and_not_relabelled_human():
    root=p.DIRECTORY/'reviews'
    comparison=p.read_json(root/'COMPARISON.json')
    assert comparison['candidate_matches']==comparison['case_count']==14
    assert not comparison['human_expert_validation'] and not comparison['user_answer_approval']
    assert not comparison['answers_frozen'] and not comparison['candidate_expected_files_modified']
    with zipfile.ZipFile(root/'AI_REVIEW_ORIGINAL.zip') as archive:
        raw=archive.read('reviewer_output.json')
        assert p.digest(raw)==comparison['original_review_sha256']
        assert json.loads(raw)==p.read_json(root/'AI_BLIND_REVIEW.json')
        assert all(p.digest(archive.read(n))==sha for n,sha in comparison['raw_archive_members'].items())


def test_ai_evidence_is_public_and_expected_answers_stay_the_original_candidates():
    root=p.DIRECTORY/'reviews'
    raw=p.read_json(root/'AI_BLIND_REVIEW.json')
    comparison=p.read_json(root/'COMPARISON.json')
    assert len({r['case_id'] for r in comparison['rows']})==14
    for row in comparison['rows']:
        files=PublicFiles(p.DIRECTORY/'cases'/row['case_id'])
        value=t3_task.parse_output(json.dumps(raw['cases'][row['review_id']]['output']),files)
        expected_path=p.DIRECTORY/'cases'/row['case_id']/'expected.json'
        assert p.digest(expected_path.read_bytes())==row['expected_sha256']
        assert value['verdict']==row['decision']['verdict']
        assert not p.read_json(expected_path)['user_approved']


def test_skill_axis_is_explicitly_unused_without_changing_reproduced_meta():
    scope=p.read_json(p.DIRECTORY/'GUIDANCE_SCOPE.json')
    assert scope['skill_files_injected']==[] and scope['skill_exposure_axis']=='not_applicable'
    assert not scope['historical_h1_h3_applied'] and not scope['case_meta_modified']
    for cid in t3_task.CASE_IDS:
        assert p.read_json(p.DIRECTORY/'cases'/cid/'meta.json')['guidance_exposure']=='unassigned'
    assert p.read_json(p.DIRECTORY/'PLAN.draft.json')['unresolved_pre_freeze']==['user answer review']
