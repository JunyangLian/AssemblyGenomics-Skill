"""Preserve a completed context-isolated AI draft before comparing author gold."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from bench.inspect_adapter import t3_packets as p, t3_task
from bench.inspect_adapter.readonly import PublicFiles


def archive_review(work):
    work=Path(work)
    output=work/'reviewer_output.json'
    raw=p.read_json(output)
    if raw.get('review_kind')!='ai_blind_review' or raw.get('context')!='fork_none/public_only':
        raise ValueError('review origin/isolation not declared')
    mapping=p.read_json(work/'PRIVATE_MAPPING.json')
    if set(mapping)!=set(raw['cases']) or set(mapping.values())!=set(t3_task.CASE_IDS) or len(mapping)!=14:
        raise ValueError('review case coverage differs')
    target=p.DIRECTORY/'reviews'
    target.mkdir(parents=True,exist_ok=True)
    archive=target/'AI_REVIEW_ORIGINAL.zip'
    contents={n:(work/n).read_bytes() for n in ('reviewer_output.json','reviewer_notes.md','blind_check.py',
                                              'blind_check_results.json','write_review.py')}
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as handle:
        for name,data in sorted(contents.items()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,11,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            handle.writestr(info,data)
    # LF views; byte-exact original output and checks remain in the zip.
    p.write_json(target/'AI_BLIND_REVIEW.json',raw)
    (target/'AI_REVIEW_NOTES.md').write_bytes(contents['reviewer_notes.md'].replace(b'\r\n',b'\n'))
    packet_hashes={q.relative_to(work/'packets').as_posix():p.digest(q.read_bytes())
                   for q in sorted((work/'packets').rglob('*')) if q.is_file()}
    rows=[]
    for rid,cid in sorted(mapping.items()):
        folder=work/'packets'/rid
        files=PublicFiles(folder)
        # Author comparison happens only after immutable review draft is archived.
        parsed=t3_task.parse_output(json.dumps(raw['cases'][rid]['output'],ensure_ascii=False),files)
        for entry in files.manifest():
            if p.digest((p.DIRECTORY/'cases'/cid/entry['path']).read_bytes())!=entry['sha256']:
                raise ValueError('blind packet differs from corresponding public case')
        expected=p.read_json(p.DIRECTORY/'cases'/cid/'expected.json')
        decision={k:parsed[k] for k in ('verdict','observed_defect','root_cause')}
        rows.append({'review_id':rid,'case_id':cid,'decision':decision,
            'agrees_with_candidate':decision in expected['acceptable_decisions'],
            'expected_sha256':p.digest((p.DIRECTORY/'cases'/cid/'expected.json').read_bytes()),
            'uncertainties':raw['cases'][rid].get('uncertainties',[])})
    comparison={'review_kind':'ai_blind_review_comparison_after_review','rows':rows,
        'candidate_matches':sum(r['agrees_with_candidate'] for r in rows),'case_count':14,
        'human_expert_validation':False,'user_answer_approval':False,'answers_frozen':False,
        'candidate_expected_files_modified':False,'exact_reviewer_model_id_available':False,
        'reviewer_origin':raw['reviewer_origin'],'same_model_family_independence_not_claimed':True,
        'access_isolation':'fresh fork_none context, anonymous public-only copies and instructions; not OS-enforced',
        'original_review_sha256':p.digest(contents['reviewer_output.json']),
        'public_lf_review_sha256':p.digest((target/'AI_BLIND_REVIEW.json').read_bytes()),
        'original_archive_sha256':p.digest(archive.read_bytes()),
        'raw_archive_members':{name:p.digest(data) for name,data in contents.items()},
        'blind_public_packet_sha256':packet_hashes,
        'prompt_at_review_sha256':p.digest((work/'packets/system.txt').read_bytes()),
        'post_review_author_change':'Common draft-2 system now defines id_mismatch as cross-file joins and gff_hierarchy_error as within-GFF hierarchy. Original independent review and candidate answers unchanged.',
        'validation_scope':'schema, exact public packet mapping and locator existence; no automatic evidence-semantic or action-safety score'}
    p.write_json(target/'COMPARISON.json',comparison)
    print(f"PASS: {comparison['candidate_matches']}/14 candidate decisions match AI draft; not human approval")
    return comparison


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work_directory')
    archive_review(parser.parse_args().work_directory)
