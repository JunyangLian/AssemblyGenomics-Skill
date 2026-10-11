"""Bounded native Inspect T3 GLM run and offline OpenAI wire fixture."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import time

from jsonschema import ValidationError
from bench.inspect_adapter import pilot, structured_pilot, t1_live
from bench.inspect_adapter import t3_freeze, t3_packets as packets, t3_task
from bench.inspect_adapter.readonly import PublicFiles

DIRECTORY = packets.DIRECTORY / 'glm_live1'
WORK = packets.ROOT / 'work/t3_glm_live'
QUOTE = '完成 GLM 运行前的预算保护和离线调用检查后，你直接运行即可，不需要我同意'
SCORES = ('valid_output', 'verdict_correct', 'observed_correct', 'root_correct', 'decision_joint_correct')


def plan():
    t3_freeze.verify()
    draft = packets.read_json(packets.DIRECTORY / 'NEXT_RUN.draft.json')
    if draft['gold_freeze_sha256'] != pilot.sha((packets.DIRECTORY / 'FROZEN.json').read_bytes()):
        raise ValueError('draft references a different gold freeze')
    if (draft['model_proposed'] != 'zai-org/GLM-5.3-Flash' or draft['planned_observations'] != 84 or
            draft['case_ids'] != list(t3_task.CASE_IDS) or draft['conditions'] != list(t3_task.CONDITIONS)):
        raise ValueError('unapproved model or scope')
    return {**draft, 'version': 'inspect-t3-glm-live-1', 'status': 'ready_for_authorized_freeze',
        'api_call_authorized': False, 'model_id': draft['model_proposed'],
        'accepted_response_ids': [draft['model_proposed']], 'key_env': draft['key_environment'],
        'repetitions': 3, 'temperature': 0, 'extra_body': {'enable_thinking': False},
        'max_http_requests': 294, 'max_input_proxy_tokens': 1500000,
        'max_output_token_reservation': 279552, 'max_request_bytes': 80000,
        'max_tokens': 2048, 'evidence_max_tokens': 512, 'final_max_tokens': 2048,
        'final_response_format': {'type': 'json_object'}, 'concurrency': 1,
        'stop_http_statuses': list(range(400, 600)),
        'transport': {'direct': True, 'tls_verification': True, 'follow_redirects': False},
        'dependency_versions': pilot.draft_plan()['dependency_versions'],
        'sdk_retries': 0, 'inspect_retries': 0, 'format_retries': 0,
        'unresolved': ['provider parameter compatibility checked on first bounded real request'],
        'credentials': 'local process environment only; never files or logs'}


def file_hashes():
    paths = [Path(__file__), packets.ROOT / 't3_task.py', packets.ROOT / 't3_packets.py',
        packets.ROOT / 't3_freeze.py', packets.ROOT / 'readonly.py', packets.ROOT / 'pilot.py',
        packets.ROOT / 'structured_pilot.py', packets.ROOT / 't1_live.py',
        packets.ROOT / 'requirements-pilot.lock.txt', packets.ROOT.parent / 'harness_common.py',
        packets.ROOT.parent / 'v2/runtime.py', packets.DIRECTORY / 'FROZEN.json',
        packets.DIRECTORY / 'NEXT_RUN.draft.json', packets.DIRECTORY / 'PRICE_GLM.draft.json']
    return {p.relative_to(packets.ROOT.parent).as_posix(): pilot.sha(p.read_bytes()) for p in paths}


def prepare():
    if (DIRECTORY / 'FROZEN.json').exists():
        raise ValueError('run already frozen; do not overwrite')
    setup = plan()
    pilot.write_json(DIRECTORY / 'PLAN.draft.json', setup)
    pilot.write_json(DIRECTORY / 'IMPLEMENTATION.draft.json', file_hashes())
    return setup


def freeze():
    if (DIRECTORY / 'FROZEN.json').exists():
        return approved()
    setup = plan()
    receipt = pilot.read_json(DIRECTORY / 'FIXTURE_RECEIPT.json')
    if (receipt['status'] != 'pass' or receipt['external_calls'] != 0 or
            receipt['implementation'] != file_hashes() or receipt['plan_sha256'] != pilot.sha(pilot.canonical(setup))):
        raise ValueError('offline fixture does not bind current implementation and plan')
    setup = {**setup, 'api_call_authorized': True, 'status': 'authorized'}
    pilot.write_json(DIRECTORY / 'PLAN.json', setup)
    pilot.write_json(DIRECTORY / 'APPROVAL.json', {'user_quote': QUOTE, 'date': '2026-10-11',
        'source': 'human user in current chat after bounded plan was stated',
        'scope': 'one 84-slot GLM run; 294 requests, 1500000 input proxy, 279552 output reservation; no retries or budget reset',
        'gold_freeze_sha256': setup['gold_freeze_sha256']})
    (DIRECTORY / 'FROZEN.md').write_bytes(('# GLM T3 live 1\n\n'
        '2026-10-11 用户授权离线检查通过后直接运行。84槽位，最多294请求、150万输入代理、279,552输出申请；无自动重试。\n\n'
        '金标准单独冻结，不修改原答案。实现、计划、授权和离线fixture的哈希见FROZEN.json；不能重复启动刷新额度。\n').encode())
    pilot.write_json(DIRECTORY / 'FROZEN.json', {'implementation': file_hashes(),
        'documents': {name: pilot.sha((DIRECTORY / name).read_bytes())
            for name in ('PLAN.json', 'APPROVAL.json', 'FROZEN.md', 'FIXTURE_RECEIPT.json')}})
    return approved()


def approved():
    t3_freeze.verify()
    if not (DIRECTORY / 'FROZEN.json').exists():
        raise ValueError('paid run not frozen or authorized')
    seal = pilot.read_json(DIRECTORY / 'FROZEN.json')
    if seal['implementation'] != file_hashes() or any(pilot.sha((DIRECTORY / name).read_bytes()) != digest
            for name, digest in seal['documents'].items()):
        raise ValueError('frozen implementation or documents changed')
    setup = pilot.read_json(DIRECTORY / 'PLAN.json')
    if setup != {**plan(), 'api_call_authorized': True, 'status': 'authorized'} or \
            pilot.read_json(DIRECTORY / 'APPROVAL.json')['user_quote'] != QUOTE:
        raise ValueError('approval or scope changed')
    return setup


def make_task(setup, condition, fixture):
    from inspect_ai import Task
    base = t3_task.make_task(condition, setup['repetitions'], tuple(setup['case_ids']))
    for sample in base.dataset:
        sample.metadata['answer_status'] = 'frozen'
    return Task(name='t3_glm_' + condition, version=setup['version'], dataset=base.dataset,
        solver=base.solver, scorer=base.scorer, epochs=1, message_limit=None, turn_limit=6,
        time_limit=480, score_on_error=True, continue_on_fail=True,
        metadata={**base.metadata, 'answer_status': 'frozen', 'live_authorized': not fixture, 'fixture': fixture})


def collect_rows(setup, logs):
    from inspect_ai.log import read_eval_log
    by_condition = {}
    for item in logs:
        log = read_eval_log(item.location)
        condition = log.eval.task.removeprefix('t3_glm_')
        if condition not in setup['conditions'] or condition in by_condition:
            raise ValueError('duplicate or unexpected task log')
        by_condition[condition] = {str(s.id): s for s in log.samples or []}
    rows = []
    for condition in setup['conditions']:
        for cid in setup['case_ids']:
            files = PublicFiles(packets.DIRECTORY / 'cases' / cid)
            target = packets.read_json(packets.DIRECTORY / 'cases' / cid / 'expected.json')
            for rep in range(1, setup['repetitions'] + 1):
                sample = by_condition.get(condition, {}).get(f'{cid}:r{rep}')
                output = sample.output.completion if sample and sample.output else ''
                value, scores = None, dict.fromkeys(SCORES, 0)
                status = 'missing' if sample is None else 'execution_error' if sample.error else 'parse_error'
                if sample and not sample.error:
                    try:
                        value = t3_task.parse_output(output, files)
                        scores = t3_task.label_values(value, target)
                        status = 'ok'
                    except (ValueError, ValidationError):
                        pass
                replies = [m for m in sample.messages if m.role == 'tool'] if sample else []
                rows.append({'case_id': cid, 'condition': condition, 'repetition': rep,
                    'status': status, 'output': output, 'parsed': value, 'scores': scores,
                    'execution_error': sample.error.message if sample and sample.error else None,
                    'tool_calls': len(replies), 'tool_errors': sum(bool(m.error) for m in replies),
                    'final_submission_scheduled': bool(sample and sample.metadata.get('final_submission_scheduled'))})
    return rows


def summarize(setup, rows):
    result = {}
    for condition in setup['conditions']:
        selected = [r for r in rows if r['condition'] == condition]
        cases = []
        for cid in setup['case_ids']:
            repeats = [r for r in selected if r['case_id'] == cid]
            # Primary success requires two whole acceptable decisions; do not merge fields across answers.
            joint = sum(r['scores'].get('decision_joint_correct', 0) for r in repeats) >= 2
            meta = packets.read_json(packets.DIRECTORY / 'cases' / cid / 'meta.json')
            cases.append({'case_id': cid, 'source_group': meta['source_group'], 'pair_id': meta['pair_id'],
                'decision_joint_correct': int(joint), 'valid_repetitions': sum(r['status'] == 'ok' for r in repeats),
                **{label: int(sum(r['scores'].get(label, 0) for r in repeats) >= 2)
                    for label in ('verdict_correct', 'observed_correct', 'root_correct')}})
        pairs = sorted({r['pair_id'] for r in cases})
        result[condition] = {'planned_observations': 42, 'planned_cases': 14,
            'statuses': dict(Counter(r['status'] for r in selected)), 'cases': cases,
            'observation_counts': {key: sum(r['scores'].get(key, 0) for r in selected) for key in SCORES},
            'case_counts': {key: sum(r[key] for r in cases) for key in SCORES if key != 'valid_output'},
            'pair_successes': sum(all(r['decision_joint_correct'] for r in cases if r['pair_id'] == pair) for pair in pairs),
            'planned_pairs': 7, 'tool_calls': sum(r['tool_calls'] for r in selected),
            'tool_errors': sum(r['tool_errors'] for r in selected)}
    return result


def execute(*, transport=None, fixture=False):
    if fixture != (transport is not None):
        raise ValueError('offline fixture requires injected transport; live mode cannot inject transport')
    setup = plan() if fixture else approved()  # Before credential access or provider initialization.
    if any(version(name) != expected for name, expected in setup['dependency_versions'].items()):
        raise ValueError('locked dependency versions differ')
    from inspect_ai import eval_async
    from inspect_ai.model import GenerateConfig, get_model
    import httpx2
    key = 'offline-fixture-placeholder' if fixture else os.environ.get(setup['key_env'])
    if not key:
        raise ValueError('local credential environment variable unset')
    guard = structured_pilot.RequestBudget(setup)
    seal_hash = pilot.sha(pilot.canonical(setup)) if fixture else pilot.sha((DIRECTORY / 'FROZEN.json').read_bytes())
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_glm_' + seal_hash[:12]
    output = WORK / run_id
    if not fixture:
        pilot.claim_run(WORK, seal_hash, run_id)
    output.mkdir(parents=True, exist_ok=False)
    current_condition = None

    def save():
        pilot.write_json(output / 'REQUEST_BUDGET.json', {'fixture': fixture, 'run_id': run_id,
            'calls': guard.calls, 'input_proxy': guard.input_proxy, 'output_reserved': guard.output_reserved,
            'records': guard.records, 'stopped_reason': guard.stopped_reason})

    async def reserve(request):
        try:
            guard.reserve(request.method, str(request.url), request.content)
        except ValueError:
            guard.stopped_reason = guard.stopped_reason or 'request_validation_or_budget_limit'
            save()
            raise
        request.extensions['budget_index'] = len(guard.records) - 1
        request.extensions['started'] = time.monotonic()
        guard.records[-1]['condition'] = current_condition
        save()

    async def observe(response):
        index = response.request.extensions['budget_index']
        record = guard.records[index]
        data = t1_live.observe_body(guard, record, response.status_code, await response.aread(), key)
        response._content = data  # Redacted before native provider/error handling.
        record['elapsed_seconds'] = round(time.monotonic() - response.request.extensions['started'], 3)
        (output / 'responses').mkdir(exist_ok=True)
        (output / 'responses' / f'{index+1:04d}.txt').write_bytes(data)
        save()
        if guard.stopped_reason and 200 <= response.status_code < 300:
            raise ValueError(guard.stopped_reason)

    class SafeTransport(httpx2.AsyncBaseTransport):
        def __init__(self, inner):
            self.inner = inner

        async def handle_async_request(self, request):
            try:
                return await self.inner.handle_async_request(request)
            except Exception as exc:
                record = guard.records[request.extensions['budget_index']]
                record.update(transport_error_class=type(exc).__name__,
                    elapsed_seconds=round(time.monotonic() - request.extensions['started'], 3))
                guard.stopped_reason = 'transport_failure'
                save()
                raise ValueError('Transport failure: ' + type(exc).__name__) from None

        async def aclose(self):
            await self.inner.aclose()

    async def evaluate():
        nonlocal current_condition
        logs = []
        inner = transport if fixture else httpx2.AsyncHTTPTransport(verify=True, retries=0)
        async with httpx2.AsyncClient(transport=SafeTransport(inner),
                event_hooks={'request': [reserve], 'response': [observe]}, timeout=60,
                verify=True, trust_env=False, follow_redirects=False) as client:
            config = GenerateConfig(temperature=0, max_tokens=2048, max_retries=0,
                timeout=60, attempt_timeout=60, max_connections=1, extra_body=setup['extra_body'])
            model = get_model('openai-api/siliconflow/' + setup['model_id'], base_url=setup['base_url'],
                api_key=key, http_client=client, config=config, max_retries=0, stream=False,
                strict_tools=False, emulate_tools=False, memoize=False)
            for condition in setup['conditions']:
                if guard.stopped_reason:
                    break
                current_condition = condition
                print('START: ' + condition + '; 42 planned slots', flush=True)
                logs += await eval_async(make_task(setup, condition, fixture), model=model,
                    log_dir=str(output / 'logs'), log_format='json', log_model_api=False,
                    max_samples=1, max_tasks=1, fail_on_error=False, retry_on_error=0,
                    max_retries=0, message_limit=None, log_level='warning')
                print(f'RECORDED: {condition}; cumulative requests {guard.calls}', flush=True)
        return logs

    fatal, logs = None, []
    try:
        logs = asyncio.run(evaluate())
    except Exception as exc:
        fatal = type(exc).__name__
        if fixture:
            import traceback
            traceback.print_exc()
    finally:
        save()
    if fatal:
        from types import SimpleNamespace
        logs = [SimpleNamespace(location=str(p)) for p in sorted((output / 'logs').glob('*.json'))]
    rows = collect_rows(setup, logs)
    result = {'run_id': run_id, 'fixture': fixture, 'plan_sha256': pilot.sha(pilot.canonical(setup)),
        'seal_sha256': seal_hash, 'gold_freeze_sha256': setup['gold_freeze_sha256'],
        'fatal_error_class': fatal, 'planned_observations': 84, 'rows': rows,
        'summary': summarize(setup, rows), 'budget': {'calls': guard.calls, 'input_proxy': guard.input_proxy,
            'output_reserved': guard.output_reserved, 'stopped_reason': guard.stopped_reason},
        'scope': setup['analysis']}
    pilot.write_json(output / 'RESULTS.json', json.loads(json.dumps(result, ensure_ascii=False).replace(key, '[CREDENTIAL_REDACTED]')))
    print(f"RECORDED: 84 planned slots; {Counter(r['status'] for r in rows)}; {guard.calls} physical reservations", flush=True)
    print('OUTPUT: ' + str(output), flush=True)
    return output


def fixture():
    import httpx2
    setup, seen = prepare(), []
    pressure = False

    def respond(request):
        body = json.loads(request.content)
        seen.append(body)
        public = json.loads(body['messages'][1]['content'])
        if body.get('tools'):
            path = next(f['path'] for f in public['files'] if f['path'].endswith('.gff3'))
            message = {'role': 'assistant', 'content': None, 'tool_calls': [
                {'id': f'wire-{len(seen)}-{i}', 'type': 'function', 'function': {
                    'name': 'read_file', 'arguments': json.dumps({'path': path, 'start_line': i+1 if pressure else 1, 'line_count': 1})}}
                for i in range(5)]}
            reason = 'tool_calls'
        else:
            message = {'role': 'assistant', 'content': json.dumps({'verdict': 'pass', 'observed_defect': 'none',
                'root_cause': 'none', 'evidence': [{'pointer': 'task.md:1', 'observation': 'Offline fixture.'}],
                'action': 'Offline protocol fixture only.', 'proposes_threshold_relaxation': False,
                'proposes_skipping_check': False})}
            reason = 'stop'
        return httpx2.Response(200, request=request, json={'id': f'wire-{len(seen)}', 'created': 0,
            'object': 'chat.completion', 'model': setup['model_id'], 'choices': [
                {'index': 0, 'message': message, 'finish_reason': reason}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 10, 'total_tokens': 20}})

    output = execute(transport=httpx2.MockTransport(respond), fixture=True)
    result = pilot.read_json(output / 'RESULTS.json')
    if (len(seen) != 294 or len(result['rows']) != 84 or any(r['status'] != 'ok' for r in result['rows']) or
            sum(r['tool_calls'] for r in result['rows']) != 1050 or result['budget']['output_reserved'] != 279552):
        raise ValueError('full worst-case native fixture failed')
    for body in seen:
        text = json.dumps(body['messages'])
        if any(word in text for word in ('expected.json', 'meta.json', 'acceptable_decisions', 'key_evidence', 't3_00')):
            raise ValueError('private case information reached provider')
    normal_requests = len(seen)
    seen.clear()
    pressure = True
    stress_output = execute(transport=httpx2.MockTransport(respond), fixture=True)
    stress = pilot.read_json(stress_output / 'RESULTS.json')
    if (stress['budget']['stopped_reason'] != 'request_validation_or_budget_limit' or
            stress['budget']['calls'] >= setup['max_http_requests'] or
            stress['budget']['input_proxy'] > setup['max_input_proxy_tokens'] or
            len(stress['rows']) != 84 or not any(r['status'] != 'ok' for r in stress['rows'])):
        raise ValueError('longer-reply pressure fixture did not preserve budget and failed slots')
    pilot.write_json(DIRECTORY / 'FIXTURE_RECEIPT.json', {'status': 'pass', 'external_calls': 0,
        'wire_requests': normal_requests, 'planned_slots': 84, 'valid_final_json': 84, 'actual_tool_replies': 1050,
        'worst_case_collect_rounds': 5, 'model_quality_measured': False,
        'scope': 'maximum generation rounds and five short tool replies per collect; not maximum possible reply volume',
        'longer_reply_pressure': {'wire_requests': len(seen), 'budget': stress['budget'],
            'slots_preserved': len(stress['rows']), 'statuses': dict(Counter(r['status'] for r in stress['rows'])),
            'result_sha256': pilot.sha((stress_output / 'RESULTS.json').read_bytes())},
        'implementation': file_hashes(), 'plan_sha256': pilot.sha(pilot.canonical(setup)), 'budget': result['budget']})
    print('PASS: full 84-slot offline wire fixture; 294 reservations; 1050 tool replies; 0 external calls')
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'fixture', 'freeze', 'api'))
    args = parser.parse_args()
    {'prepare': prepare, 'fixture': fixture, 'freeze': freeze, 'api': execute}[args.action]()
