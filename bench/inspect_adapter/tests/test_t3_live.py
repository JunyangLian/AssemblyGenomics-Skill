"""Physical budget bounds, immutable targets and failure denominators for GLM."""
import json

import pytest

from bench.inspect_adapter import structured_pilot, t1_live, t3_live as live
from bench.inspect_adapter import t3_packets as packets


@pytest.fixture(scope='module')
def setup():
    return live.plan()


def final_request(setup):
    return json.dumps({'model': setup['model_id'], 'messages': [], 'temperature': 0,
        'stream': False, 'max_tokens': 2048, 'enable_thinking': False,
        'response_format': {'type': 'json_object'}}).encode()


def test_scope_never_inherits_old_model_or_budget(setup):
    assert setup['model_id'] == 'zai-org/GLM-5.3-Flash'
    assert setup['planned_observations'] == 84 and len(setup['case_ids']) == 14
    assert setup['max_http_requests'] == 42 * (1 + 6)
    assert setup['max_output_token_reservation'] == 42 * (2048 + 5 * 512 + 2048)
    assert setup['max_input_proxy_tokens'] == 1500000
    assert not setup['api_call_authorized']
    assert setup['sdk_retries'] == setup['inspect_retries'] == setup['format_retries'] == 0


@pytest.mark.parametrize('cap', ['max_http_requests', 'max_input_proxy_tokens', 'max_output_token_reservation'])
def test_every_physical_request_reserves_and_limits_before_transport(setup, cap):
    limited = {**setup, cap: {'max_http_requests': 1, 'max_input_proxy_tokens': 500,
        'max_output_token_reservation': 2048}[cap]}
    guard = structured_pilot.RequestBudget(limited)
    url = setup['base_url'] + '/chat/completions'
    guard.reserve('POST', url, final_request(setup))
    with pytest.raises(ValueError, match='limit reached'):
        guard.reserve('POST', url, final_request(setup))
    assert guard.calls == 1 and guard.output_reserved == 2048


@pytest.mark.parametrize('change', [{'model': 'another-model'}, {'enable_thinking': True},
    {'max_tokens': 4096}, {'response_format': {'type': 'text'}}])
def test_parameter_drift_is_blocked_before_reservation(setup, change):
    guard = structured_pilot.RequestBudget(setup)
    body = {**json.loads(final_request(setup)), **change}
    with pytest.raises(ValueError):
        guard.reserve('POST', setup['base_url'] + '/chat/completions', json.dumps(body).encode())
    assert guard.calls == guard.input_proxy == guard.output_reserved == 0


@pytest.mark.parametrize('status,model,usage', [(429, None, {}),
    (200, 'another-model', {}), (200, 'zai-org/GLM-5.3-Flash',
        {'completion_tokens_details': {'reasoning_tokens': 1}})])
def test_stop_and_credential_redaction_prevent_next_request(setup, status, model, usage):
    guard = structured_pilot.RequestBudget(setup)
    content = json.dumps({'model': model, 'usage': usage, 'error': 'fixture-secret'}).encode()
    redacted = t1_live.observe_body(guard, {}, status, content, 'fixture-secret')
    assert b'fixture-secret' not in redacted
    with pytest.raises(ValueError, match='stopped'):
        guard.reserve('POST', setup['base_url'] + '/chat/completions', final_request(setup))
    assert guard.calls == 0


def test_frozen_gold_and_native_limits_preserved(setup):
    task = live.make_task(setup, 'tools', True)
    assert task.message_limit is None and task.turn_limit == 6
    assert task.name == 't3_glm_tools' and len(task.dataset) == 42
    for sample in task.dataset:
        expected = packets.DIRECTORY / 'cases' / sample.metadata['case_id'] / 'expected.json'
        assert sample.target.encode() == expected.read_bytes()
        assert sample.metadata['answer_status'] == 'frozen'


def test_missing_and_parse_errors_keep_all_slots_and_pairs(setup):
    rows = [{'condition': condition, 'case_id': cid, 'repetition': rep, 'status': 'missing',
        'scores': {}, 'tool_calls': 0, 'tool_errors': 0}
        for condition in setup['conditions'] for cid in setup['case_ids'] for rep in (1, 2, 3)]
    for summary in live.summarize(setup, rows).values():
        assert summary['planned_observations'] == 42 and summary['planned_cases'] == 14
        assert summary['statuses'] == {'missing': 42} and summary['planned_pairs'] == 7
        assert summary['pair_successes'] == 0
        assert not any(summary['case_counts'].values())


def test_unfrozen_entry_fails_before_credential_access(tmp_path, monkeypatch):
    monkeypatch.setattr(live, 'DIRECTORY', tmp_path)
    with pytest.raises(ValueError, match='not frozen or authorized'):
        live.execute()


def test_current_fixture_binds_real_wire_limits_not_quality():
    receipt = packets.read_json(live.DIRECTORY / 'FIXTURE_RECEIPT.json')
    assert receipt['status'] == 'pass' and receipt['external_calls'] == 0
    assert receipt['wire_requests'] == 294 and receipt['planned_slots'] == 84
    assert receipt['valid_final_json'] == 84 and receipt['actual_tool_replies'] == 1050
    assert receipt['implementation'] == live.file_hashes()
    assert not receipt['model_quality_measured']
