from havoc_monkey.report import AttackResult, Report, get_severity, get_recommendation


def make_result(attack='null_flood', params=None, hc_result='FAILED', hc_error=None):
    params = params if params is not None else {}
    severity = get_severity(attack, params, hc_result)
    return AttackResult(
        attack=attack,
        params=params,
        rows_before=200,
        rows_after=200,
        schema_before=['a', 'b'],
        schema_after=['a', 'b'],
        nulls_injected=0,
        hc_result=hc_result,
        hc_error=hc_error,
        severity=severity,
        recommendation=get_recommendation(attack, hc_result),
    )


# ── severity logic ──────────────────────────────────────────────────

def test_schema_drift_failed_is_critical():
    assert get_severity('schema_drift', {'attack': 'drop'}, 'FAILED') == 'CRITICAL'


def test_volume_shock_empty_failed_is_critical():
    assert get_severity('volume_shock', {'attack': 'empty'}, 'FAILED') == 'CRITICAL'


def test_volume_shock_overflow_failed_is_high():
    assert get_severity('volume_shock', {'attack': 'overflow'}, 'FAILED') == 'HIGH'


def test_null_flood_failed_is_high():
    assert get_severity('null_flood', {}, 'FAILED') == 'HIGH'


def test_error_is_medium():
    assert get_severity('null_flood', {}, 'ERROR') == 'MEDIUM'


def test_passed_is_low():
    assert get_severity('null_flood', {}, 'PASSED') == 'LOW'


def test_skipped_is_unknown():
    assert get_severity('null_flood', {}, 'SKIPPED') == 'UNKNOWN'


# ── recommendations ─────────────────────────────────────────────────

def test_recommendation_failed_per_attack():
    assert get_recommendation('null_flood', 'FAILED') == \
        "Add null guard or imputation upstream of pipeline entry."
    assert get_recommendation('schema_drift', 'FAILED') == \
        "Add explicit column existence check before processing."


def test_recommendation_passed_is_generic():
    assert get_recommendation('null_flood', 'PASSED') == \
        "Pipeline handled this attack. No action required."


def test_recommendation_skipped_is_generic():
    assert get_recommendation('null_flood', 'SKIPPED') == \
        "Provide a health_check callable to measure impact."


# ── AttackResult / Report rendering ─────────────────────────────────

def test_attack_result_str_contains_key_info():
    result = make_result(attack='schema_drift', params={'attack': 'drop', 'col': 'user_id'},
                          hc_result='FAILED', hc_error="KeyError: 'user_id'")
    text = str(result)
    assert 'CRITICAL' in text
    assert 'schema_drift / drop' in text
    assert 'col: user_id' in text
    assert "KeyError: 'user_id'" in text
    assert result.recommendation in text


def test_report_str_contains_summary():
    results = [
        make_result(attack='schema_drift', params={'attack': 'drop', 'col': 'user_id'},
                     hc_result='FAILED', hc_error="KeyError: 'user_id'"),
        make_result(attack='null_flood', params={'cols': ['amount'], 'pct': 0.15},
                     hc_result='FAILED', hc_error="AssertionError: nulls leaked"),
        make_result(attack='temporal', params={'attack': 'out_of_order', 'pct': 0.2},
                     hc_result='PASSED'),
    ]
    report = Report(seed=42, total=3, passed=1, failed=2, errors=0, skipped=0, results=results)
    text = str(report)
    assert 'HAVOC-MONKEY CAMPAIGN REPORT' in text
    assert 'seed=42' in text
    assert 'attacks=3' in text
    assert '2/3 FAILED' in text
    assert 'CRITICAL: 1' in text
    assert 'HIGH: 1' in text
    assert 'LOW: 1' in text
    assert 'passed: 1/3' in text


def test_report_to_dict():
    results = [make_result()]
    report = Report(seed=42, total=1, passed=0, failed=1, errors=0, skipped=0, results=results)
    d = report.to_dict()
    assert d['seed'] == 42
    assert d['total'] == 1
    assert d['results'][0]['attack'] == 'null_flood'


def _make_report():
    results = [
        make_result(attack='schema_drift', params={'attack': 'drop', 'col': 'user_id'}, hc_result='FAILED'),
        make_result(attack='null_flood', params={'cols': ['amount'], 'pct': 0.15}, hc_result='PASSED'),
    ]
    return Report(seed=7, total=2, passed=1, failed=1, errors=0, skipped=0, results=results)


def test_to_markdown_structure():
    md = _make_report().to_markdown()
    assert '`seed=7`' in md
    assert '| Attack |' in md
    assert '`schema_drift`' in md
    assert '`null_flood`' in md
    assert '**FAILED**' in md
    assert '**PASSED**' in md


def test_to_html_structure():
    html = _make_report().to_html()
    assert '<!DOCTYPE html>' in html
    assert 'seed=7' in html
    assert 'schema_drift' in html
    assert 'null_flood' in html
    assert 'FAILED' in html
    assert 'PASSED' in html
    assert '--peach' in html
