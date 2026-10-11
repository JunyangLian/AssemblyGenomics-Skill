from bench.inspect_adapter.t3_report import qc_metrics, ratio


def test_failures_are_not_detection_and_low_false_positive_does_not_hide_errors():
    rows = [
        {'case_id': 'fault', 'status': 'ok', 'parsed': {'verdict': 'block'}},
        {'case_id': 'fault', 'status': 'parse_error', 'parsed': None},
        {'case_id': 'fault', 'status': 'missing', 'parsed': None},
        {'case_id': 'normal', 'status': 'ok', 'parsed': {'verdict': 'pass'}},
        {'case_id': 'normal', 'status': 'ok', 'parsed': {'verdict': 'warn'}},
        {'case_id': 'normal', 'status': 'execution_error', 'parsed': None},
    ]
    metrics = qc_metrics(rows, {'fault': 'fault', 'normal': 'normal'})
    assert metrics['fault_detection_cases'] == metrics['false_positive_cases'] == 0
    assert metrics['fault_detection_observations'] == metrics['false_positive_observations'] == 1
    assert metrics['fault_observations'] == metrics['normal_observations'] == 3
    assert metrics['inconsistent_cases'] == 1 and metrics['incomplete_cases'] == 2
    assert ratio(1, 3) == '1/3 (33.3%)'
