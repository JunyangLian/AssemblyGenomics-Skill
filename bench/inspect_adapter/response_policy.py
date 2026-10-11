"""Future-run response checks; do not patch historical frozen transports."""
import json

from bench.inspect_adapter import pilot


def observe_body(guard, record, status, data, key):
    data = data.replace(key.encode(), b'[CREDENTIAL_REDACTED]') if key else data
    record.update(status_code=status, response_body_sha256=pilot.sha(data))
    try:
        body = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        body = {}
    record.update(returned_model_id=body.get('model'), usage=body.get('usage'))
    choices = body.get('choices') or []
    record['reasoning_content_present'] = any(bool((c.get('message') or {}).get('reasoning_content')) for c in choices)
    reported = ((body.get('usage') or {}).get('completion_tokens_details') or {}).get('reasoning_tokens', 0) or 0
    record['reasoning_tokens_reported'] = reported
    if status in guard.plan['stop_http_statuses']:
        guard.stopped_reason = 'provider_stop_status_' + str(status)
    elif 200 <= status < 300:
        if body.get('model') not in guard.plan['accepted_response_ids']:
            guard.stopped_reason = 'unapproved_returned_model_identity'
        elif not guard.plan.get('allow_reasoning', False) and (reported or record['reasoning_content_present']):
            guard.stopped_reason = 'unexpected_reasoning_response'
        elif record.get('phase') == 'final' and (not choices or not (choices[0].get('message') or {}).get('content')):
            guard.stopped_reason = 'empty_final_submission'
    return data
