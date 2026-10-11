"""Report a preserved GLM run without changing its gold, errors, or denominators."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from bench.inspect_adapter import pilot, t3_live as live, t3_packets as packets


def ratio(n, d):
    return f'{n}/{d} ({100*n/d:.1f}%)' if d else '0/0（不适用）'


def qc_metrics(rows, case_types):
    faults = {cid for cid, kind in case_types.items() if kind == 'fault'}
    normals = {cid for cid, kind in case_types.items() if kind == 'normal'}
    nonpass = lambda r: r['status'] == 'ok' and r['parsed']['verdict'] != 'pass'
    repeats = {cid: [r for r in rows if r['case_id'] == cid] for cid in case_types}
    return {'fault_detection_cases': sum(sum(nonpass(r) for r in repeats[cid]) >= 2 for cid in faults),
        'fault_cases': len(faults),
        'false_positive_cases': sum(sum(nonpass(r) for r in repeats[cid]) >= 2 for cid in normals),
        'normal_cases': len(normals),
        'fault_detection_observations': sum(nonpass(r) for r in rows if r['case_id'] in faults),
        'fault_observations': len(faults) * 3,
        'false_positive_observations': sum(nonpass(r) for r in rows if r['case_id'] in normals),
        'normal_observations': len(normals) * 3,
        'inconsistent_cases': sum(len({r['parsed']['verdict'] for r in rs if r['status'] == 'ok'}) > 1
                                  for rs in repeats.values()),
        'incomplete_cases': sum(sum(r['status'] == 'ok' for r in rs) != 3 for rs in repeats.values())}


def write_report(output):
    output = Path(output).resolve()
    if not output.is_relative_to(live.WORK.resolve()):
        raise ValueError('report input must be the local GLM audit directory')
    result = packets.read_json(output / 'RESULTS.json')
    budget = packets.read_json(output / 'REQUEST_BUDGET.json')
    setup = live.approved()
    if result['fixture'] or result['seal_sha256'] != pilot.sha((live.DIRECTORY / 'FROZEN.json').read_bytes()):
        raise ValueError('not the authorized real run')
    if result['summary'] != live.summarize(setup, result['rows']):
        raise ValueError('saved summary differs from preserved observations')
    slots = {(r['condition'], r['case_id'], r['repetition']) for r in result['rows']}
    if len(slots) != 84 or len(result['rows']) != 84:
        raise ValueError('duplicate or omitted planned slot')
    records = budget['records']
    usages = [r['usage'] for r in records if isinstance(r.get('usage'), dict)]
    totals = {key: sum(u.get(key, 0) or 0 for u in usages)
              for key in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
    price = packets.read_json(packets.DIRECTORY / 'PRICE_GLM.draft.json')
    reference_cost = (totals['prompt_tokens'] * price['input_uncached_per_million'] +
                      totals['completion_tokens'] * price['output_per_million']) / 1000000
    public = {key: result[key] for key in ('run_id', 'fixture', 'gold_freeze_sha256',
        'seal_sha256', 'planned_observations', 'fatal_error_class', 'rows', 'summary', 'budget', 'scope')}
    request_summary = {}
    for condition in setup['conditions']:
        group = [r for r in records if r['condition'] == condition]
        known = [r for r in group if isinstance(r.get('usage'), dict)]
        request_summary[condition] = {'physical_requests': len(group), 'usage_records': len(known),
            'input_proxy': sum(r['input_proxy'] for r in group),
            'input_proxy_mean_per_request': sum(r['input_proxy'] for r in group) / len(group) if group else None,
            'prompt_tokens': sum(r['usage'].get('prompt_tokens', 0) or 0 for r in known),
            'completion_tokens': sum(r['usage'].get('completion_tokens', 0) or 0 for r in known)}
    public.update(usage_totals=totals, physical_request_summary=request_summary,
        uncached_reference_cost_cny=reference_cost,
        price_note='actual received usage at uncached snapshot price; cache discounts/failed billing unknown, not invoice',
        report_generator_sha256=pilot.sha(Path(__file__).read_bytes()))
    public['quality_comparison_valid'] = sum(r['status'] == 'ok' for r in result['rows']) > 0
    public['run_interpretation'] = ('protocol failure; no valid QC decisions, zeros describe pipeline failure, not model capability'
        if not public['quality_comparison_valid'] else 'exploratory QC decisions with preserved protocol errors')
    case_types = {cid: packets.read_json(packets.DIRECTORY / 'cases' / cid / 'meta.json')['type']
                  for cid in setup['case_ids']}
    public['qc_metrics'] = {condition: qc_metrics([r for r in result['rows'] if r['condition'] == condition], case_types)
                            for condition in setup['conditions']}
    pilot.write_json(live.DIRECTORY / 'RESULTS_PUBLIC.json', public)

    lines = ['# T3 GLM 七来源测试', '', '2026-10-11。原生 Inspect、冻结14题、inline/tools两条件、每题三次。', '',
        f"运行 `{result['run_id']}`，模型 `{setup['model_id']}`。HTTP预留 {budget['calls']}/{setup['max_http_requests']}，"
        f"输入代理 {budget['input_proxy']:,}/{setup['max_input_proxy_tokens']:,}，输出申请 {budget['output_reserved']:,}/{setup['max_output_token_reservation']:,}。", '',
        f"HTTP状态：{dict(Counter(str(r.get('status_code', '无响应')) for r in records))}；停止原因：{budget['stopped_reason'] or '无'}。自动重试0，未补跑、未改答案。", '',
        f"收到 {len(usages)} 份usage，输入 {totals['prompt_tokens']:,}、输出 {totals['completion_tokens']:,}、合计 {totals['total_tokens']:,} token。"
        f"按无缓存价格快照参考¥{reference_cost:.4f}，不是账单；无usage请求的成本未知。", '',
        '## 按题的主结果', '',
        '联合正确要求三次中至少两次完整可接受决定匹配，不能从不同错误答案拼接verdict/缺陷/根因。失败和缺失保留分母。', '',
        '| 条件 | 判定正确 | 观测缺陷正确 | 文件级根因正确 | 联合正确 | 同源题对成功 |',
        '|---|---|---|---|---|---|']
    if not public['quality_comparison_valid']:
        lines[2:2] = ['**本轮是协议兼容失败，0份有效QC决定。下表零分属于端到端运行失败，不能解释为GLM基因组QC能力差或工具访问无效。**', '']
    for condition, group in result['summary'].items():
        counts = group['case_counts']
        lines.append('| ' + condition + ' | ' + ' | '.join(ratio(counts[k], 14) for k in
            ('verdict_correct', 'observed_correct', 'root_correct', 'decision_joint_correct')) +
            ' | ' + ratio(group['pair_successes'], 7) + ' |')
    lines += ['', '| 条件 | 故障检出（题） | 正常误报（题） | 判定不一致 | 重复不完整 |',
        '|---|---|---|---|---|']
    for condition, qc in public['qc_metrics'].items():
        lines.append(f"| {condition} | {ratio(qc['fault_detection_cases'],qc['fault_cases'])} | "
            f"{ratio(qc['false_positive_cases'],qc['normal_cases'])} | {ratio(qc['inconsistent_cases'],14)} | "
            f"{ratio(qc['incomplete_cases'],14)} |")
    lines += ['', '检出只统计合法非pass决定，错误/缺失不算检出。误报只统计正常题的合法非pass决定；格式/执行错误另列，不能由低误报推导可用性。判定不一致使用合法重复，重复不完整单列。']
    lines += ['', '## 次要结果与来源拆分', '',
        '| 条件 | 合法输出 | 联合正确观测 | 实际工具回复 / 工具错误 | 状态 |', '|---|---|---|---|---|']
    for condition, group in result['summary'].items():
        counts = group['observation_counts']
        lines.append(f"| {condition} | {ratio(counts['valid_output'],42)} | {ratio(counts['decision_joint_correct'],42)} | "
            f"{group['tool_calls']} / {group['tool_errors']} | {group['statuses']} |")
    lines += ['', '| 条件 | 故障检出（观测） | 正常误报（观测） |', '|---|---|---|']
    for condition, qc in public['qc_metrics'].items():
        lines.append(f"| {condition} | {ratio(qc['fault_detection_observations'],qc['fault_observations'])} | "
                     f"{ratio(qc['false_positive_observations'],qc['normal_observations'])} |")
    lines += ['', '| 来源组 | inline 联合正确 | tools 联合正确 |', '|---|---|---|']
    groups = sorted({r['source_group'] for r in result['summary']['inline']['cases']})
    for source in groups:
        values = []
        for condition in setup['conditions']:
            cases = [r for r in result['summary'][condition]['cases'] if r['source_group'] == source]
            values.append(ratio(sum(r['decision_joint_correct'] for r in cases), len(cases)))
        lines.append('| ' + source + ' | ' + ' | '.join(values) + ' |')
    lines += ['', '| 条件 | 平均实际输入 token / 已有usage请求 | 平均输入代理 / 请求 | 累计输入代理 |',
        '|---|---|---|---|']
    for condition, stats in request_summary.items():
        mean = stats['prompt_tokens'] / stats['usage_records'] if stats['usage_records'] else None
        lines.append(f"| {condition} | {mean} | {stats['input_proxy_mean_per_request']} | {stats['input_proxy']:,} |")
    lines += ['', '工具条件可能多轮读取；每次请求平均与每题累计成本不是同一单位，不把访问方式效果归因于Skill。', '',
        '## 逐题输出', '', '保留全部观测，包括错误/缺失。下表引用模型原文；证据语义和action安全尚未独立复核。', '',
        '| 题 / 条件 / 重复 | 状态 | 模型决定 | 冻结决定 | 引用证据 | action |', '|---|---|---|---|---|---|']
    def cell(value):
        return str(value).replace('|', '&#124;').replace('\n', '<br>').replace('\r', '')
    for row in result['rows']:
        target = packets.read_json(packets.DIRECTORY / 'cases' / row['case_id'] / 'expected.json')
        parsed = row['parsed'] or {}
        decision = '/'.join(str(parsed.get(k, '—')) for k in ('verdict', 'observed_defect', 'root_cause'))
        expected = '; '.join('/'.join(d[k] for k in ('verdict', 'observed_defect', 'root_cause'))
                             for d in target['acceptable_decisions'])
        lines.append('| ' + ' | '.join(cell(v) for v in (
            f"{row['case_id']} / {row['condition']} / {row['repetition']}", row['status'], decision,
            expected, parsed.get('evidence', row['output']), parsed.get('action', row['execution_error']))) + ' |')
    lines += ['', '## 边界', '',
        '作者候选金标准经匿名AI核查与用户确认，不是独立真人专家盲审。独立来源只有7个，每来源两套小型编码gene块；重复和同源题对不视作独立来源，不能泛化到整基因组注释质量。', '',
        '允许partial、异构体和多片段；根因只代表公开文件级缺陷，不确证上游历史事故，也不证明某一侧修复方案正确。自动引用存在检查不验证其语义，建议安全和自报危险布尔字段需要单独复核。', '',
        '没有Skill知识注入，暴露轴不适用，不检验旧H1–H3，不与T1旧合同成绩合并。两条件输入量与工具调用次数不同；readonly函数仅操作运输公开子集，没有shell/网络或可变文件能力。', '',
        'API错误、超预算或缺失槽位保留，不能以剩余额度自动补跑。真实用量与输入代理不同，无缓存费用参考不等于实际账单。']
    (live.DIRECTORY / 'REPORT.md').write_bytes(('\n'.join(lines) + '\n').encode('utf-8'))
    pilot.write_json(live.DIRECTORY / 'RUN_RECEIPT.json', {'run_id': result['run_id'],
        'model_id': setup['model_id'], 'scope': setup['analysis'],
        'gold_freeze_sha256': result['gold_freeze_sha256'], 'seal_sha256': result['seal_sha256'],
        'private_artifact_sha256': {p.relative_to(output).as_posix(): pilot.sha(p.read_bytes())
            for p in sorted(output.rglob('*')) if p.is_file()},
        'public_files': {name: pilot.sha((live.DIRECTORY / name).read_bytes())
            for name in ('RESULTS_PUBLIC.json', 'REPORT.md')}})
    return public


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output')
    result = write_report(parser.parse_args().output)
    print('Reported preserved real slots: ' + str(result['planned_observations']))
