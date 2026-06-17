import pandas as pd

from havoc_monkey.report import Report


def _hash(df):
    return pd.util.hash_pandas_object(df).sum()


def test_campaign_no_health_check_is_skipped(s, sample_df):
    report = s.campaign(
        sample_df,
        attacks=[
            {'name': 'null_flood', 'params': {'cols': ['amount']}},
            {'name': 'schema_drift', 'params': {'attack': 'drop', 'col': 'category'}},
        ],
    )
    assert isinstance(report, Report)
    assert report.total == 2
    assert report.skipped == 2
    assert all(r.hc_result == 'SKIPPED' for r in report.results)
    assert all(r.severity == 'UNKNOWN' for r in report.results)


def test_campaign_health_check_passes(s, sample_df):
    def hc(df):
        return True

    report = s.campaign(
        sample_df, attacks=[{'name': 'null_flood', 'params': {'cols': ['amount']}}],
        health_check=hc,
    )
    assert report.passed == 1
    assert report.results[0].hc_result == 'PASSED'
    assert report.results[0].severity == 'LOW'


def test_campaign_health_check_assertion_failure(s, sample_df):
    def hc(df):
        assert df['amount'].notnull().all(), "nulls leaked"

    report = s.campaign(
        sample_df, attacks=[{'name': 'null_flood', 'params': {'cols': ['amount']}}],
        health_check=hc,
    )
    assert report.failed == 1
    result = report.results[0]
    assert result.hc_result == 'FAILED'
    assert 'nulls leaked' in result.hc_error
    assert result.severity == 'HIGH'


def test_campaign_health_check_error(s, sample_df):
    def hc(df):
        raise KeyError('user_id')

    report = s.campaign(
        sample_df,
        attacks=[{'name': 'schema_drift', 'params': {'attack': 'drop', 'col': 'category'}}],
        health_check=hc,
    )
    assert report.errors == 1
    result = report.results[0]
    assert result.hc_result == 'ERROR'
    assert 'KeyError' in result.hc_error
    assert result.severity == 'MEDIUM'


def test_campaign_schema_drift_drop_failed_is_critical(s, sample_df):
    def hc(df):
        assert 'category' in df.columns

    report = s.campaign(
        sample_df,
        attacks=[{'name': 'schema_drift', 'params': {'attack': 'drop', 'col': 'category'}}],
        health_check=hc,
    )
    assert report.results[0].severity == 'CRITICAL'


def test_campaign_parameterized_attacks(s, sample_df):
    report = s.campaign(
        sample_df,
        attacks=[
            {'name': 'null_flood', 'params': {'cols': ['amount'], 'pct': 0.3}},
        ],
    )
    result = report.results[0]
    assert result.params == {'cols': ['amount'], 'pct': 0.3}
    assert result.nulls_injected == int(len(sample_df) * 0.3)


def test_campaign_does_not_mutate_input(s, sample_df):
    before = _hash(sample_df)
    s.campaign(
        sample_df,
        attacks=[
            {'name': 'null_flood', 'params': {'cols': ['amount']}},
            {'name': 'volume_shock', 'params': {'attack': 'empty'}},
            {'name': 'schema_drift', 'params': {'attack': 'drop', 'col': 'category'}},
        ],
    )
    assert _hash(sample_df) == before


def test_campaign_rows_and_schema_tracked(s, sample_df):
    report = s.campaign(sample_df, attacks=[{'name': 'volume_shock', 'params': {'attack': 'empty'}}])
    result = report.results[0]
    assert result.rows_before == len(sample_df)
    assert result.rows_after == 0
    assert result.schema_before == list(sample_df.columns)
    assert result.schema_after == list(sample_df.columns)
