import json
from types import SimpleNamespace

import pytest

from bench.inspect_adapter import response_policy as policy


@pytest.mark.parametrize('reported', [None, 0])
def test_reasoning_content_stops_even_without_reported_reasoning_tokens(reported):
    guard = SimpleNamespace(plan={'stop_http_statuses': [400, 429], 'accepted_response_ids': ['glm']}, stopped_reason=None)
    usage = {} if reported is None else {'completion_tokens_details': {'reasoning_tokens': reported}}
    body = {'model': 'glm', 'usage': usage, 'choices': [{'message': {'content': '', 'reasoning_content': 'fixture-secret'}}]}
    record = {'phase': 'final'}
    data = policy.observe_body(guard, record, 200, json.dumps(body).encode(), 'fixture-secret')
    assert b'fixture-secret' not in data
    assert guard.stopped_reason == 'unexpected_reasoning_response'
    assert record['reasoning_content_present']


def test_allow_reasoning_does_not_treat_empty_final_as_success():
    guard = SimpleNamespace(plan={'stop_http_statuses': [400, 429], 'accepted_response_ids': ['glm'],
                                  'allow_reasoning': True}, stopped_reason=None)
    body = {'model': 'glm', 'choices': [{'message': {'content': '', 'reasoning_content': 'fixture'}}]}
    policy.observe_body(guard, {'phase': 'final'}, 200, json.dumps(body).encode(), '')
    assert guard.stopped_reason == 'empty_final_submission'
    guard.stopped_reason = None
    body['choices'][0]['message']['content'] = '{"verdict":"pass"}'
    policy.observe_body(guard, {'phase': 'final'}, 200, json.dumps(body).encode(), '')
    assert guard.stopped_reason is None
