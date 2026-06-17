import pandas as pd
import pytest


def _hash(df):
    return pd.util.hash_pandas_object(df).sum()


# ── null_flood ──────────────────────────────────────────────────────

def test_null_flood_injects_expected_null_count(s, sample_df):
    out = s.null_flood(sample_df, cols=['amount'], pct=0.10)
    assert out['amount'].isna().sum() == int(len(sample_df) * 0.10)


def test_null_flood_does_not_mutate_input(s, sample_df):
    before = _hash(sample_df)
    _ = s.null_flood(sample_df, cols=['amount'], pct=0.10)
    assert _hash(sample_df) == before
    assert sample_df['amount'].isna().sum() == 0


def test_null_flood_pct_zero_no_nulls(s, sample_df):
    out = s.null_flood(sample_df, cols=['amount'], pct=0.0)
    assert out['amount'].isna().sum() == 0


def test_null_flood_pct_one_all_null(s, sample_df):
    out = s.null_flood(sample_df, cols=['amount'], pct=1.0)
    assert out['amount'].isna().all()


def test_null_flood_multiple_cols(s, sample_df):
    out = s.null_flood(sample_df, cols=['amount', 'score'], pct=0.10)
    expected = int(len(sample_df) * 0.10)
    assert out['amount'].isna().sum() == expected
    assert out['score'].isna().sum() == expected


# ── volume_shock ────────────────────────────────────────────────────

def test_volume_shock_empty(s, sample_df):
    out = s.volume_shock(sample_df, attack='empty')
    assert len(out) == 0
    assert list(out.columns) == list(sample_df.columns)


def test_volume_shock_overflow(s, sample_df):
    out = s.volume_shock(sample_df, attack='overflow', factor=10.0)
    assert len(out) == len(sample_df) * 10


def test_volume_shock_truncate(s, sample_df):
    out = s.volume_shock(sample_df, attack='truncate', ratio=0.5)
    assert len(out) == int(len(sample_df) * 0.5)


def test_volume_shock_does_not_mutate_input(s, sample_df):
    before = _hash(sample_df)
    _ = s.volume_shock(sample_df, attack='empty')
    _ = s.volume_shock(sample_df, attack='overflow', factor=2.0)
    _ = s.volume_shock(sample_df, attack='truncate', ratio=0.5)
    assert _hash(sample_df) == before


# ── type_coerce ─────────────────────────────────────────────────────

def test_type_coerce_changes_dtype(s, sample_df):
    out = s.type_coerce(sample_df, col='amount', target='str')
    assert out['amount'].dtype != sample_df['amount'].dtype
    assert isinstance(out['amount'].iloc[0], str)


def test_type_coerce_other_cols_unchanged(s, sample_df):
    out = s.type_coerce(sample_df, col='amount', target='str')
    assert out['count'].dtype == sample_df['count'].dtype
    assert out['score'].equals(sample_df['score'])


def test_type_coerce_int_to_float(s, sample_df):
    out = s.type_coerce(sample_df, col='count', target='float')
    assert out['count'].dtype == float


def test_type_coerce_invalid_target_raises_value_error(s, sample_df):
    import pytest
    with pytest.raises(ValueError, match="Unknown target dtype"):
        s.type_coerce(sample_df, col='amount', target='datetime')


def test_type_coerce_does_not_mutate_input(s, sample_df):
    before = _hash(sample_df)
    _ = s.type_coerce(sample_df, col='amount', target='str')
    assert _hash(sample_df) == before


# ── schema_drift ────────────────────────────────────────────────────

def test_schema_drift_drop(s, sample_df):
    out = s.schema_drift(sample_df, attack='drop', col='category')
    assert 'category' not in out.columns


def test_schema_drift_rename(s, sample_df):
    out = s.schema_drift(sample_df, attack='rename', col='id', new_name='user_id')
    assert 'user_id' in out.columns
    assert 'id' not in out.columns


def test_schema_drift_add(s, sample_df):
    out = s.schema_drift(sample_df, attack='add')
    assert len(out.columns) == len(sample_df.columns) + 1
    new_cols = set(out.columns) - set(sample_df.columns)
    assert len(new_cols) == 1
    new_col = new_cols.pop()
    assert new_col.startswith('injected_')


def test_schema_drift_reorder(s, sample_df):
    out = s.schema_drift(sample_df, attack='reorder')
    assert set(out.columns) == set(sample_df.columns)
    assert list(out.columns) != list(sample_df.columns)


def test_schema_drift_does_not_mutate_input(s, sample_df):
    before = _hash(sample_df)
    cols_before = list(sample_df.columns)
    _ = s.schema_drift(sample_df, attack='drop', col='category')
    _ = s.schema_drift(sample_df, attack='add')
    _ = s.schema_drift(sample_df, attack='reorder')
    assert _hash(sample_df) == before
    assert list(sample_df.columns) == cols_before


# ── outlier_inject ──────────────────────────────────────────────────

def test_outlier_inject_int64_column(s, sample_df):
    out = s.outlier_inject(sample_df, cols=['count'], sigma=5.0, pct=0.05)
    assert out['count'].dtype == float
    n_expected = int(len(sample_df) * 0.05)
    mean = sample_df['count'].mean()
    std = sample_df['count'].std()
    extreme = out['count'][
        (out['count'] > mean + 4 * std) | (out['count'] < mean - 4 * std)
    ]
    assert len(extreme) == n_expected


def test_outlier_inject_extreme_values(s, sample_df):
    out = s.outlier_inject(sample_df, cols=['amount'], sigma=5.0, pct=0.05)
    mean = sample_df['amount'].mean()
    std = sample_df['amount'].std()
    n_expected = int(len(sample_df) * 0.05)
    extreme = out['amount'][
        (out['amount'] > mean + 4 * std) | (out['amount'] < mean - 4 * std)
    ]
    assert len(extreme) == n_expected


def test_outlier_inject_other_cols_unchanged(s, sample_df):
    out = s.outlier_inject(sample_df, cols=['amount'], sigma=5.0, pct=0.05)
    assert out['score'].equals(sample_df['score'])


def test_outlier_inject_does_not_mutate_input(s, sample_df):
    before = _hash(sample_df)
    _ = s.outlier_inject(sample_df, cols=['amount'], sigma=5.0, pct=0.05)
    assert _hash(sample_df) == before


# ── temporal ────────────────────────────────────────────────────────

def test_temporal_out_of_order(s, sample_df):
    out = s.temporal(sample_df, col='timestamp', attack='out_of_order', pct=0.2)
    assert not out['timestamp'].is_monotonic_increasing


def test_temporal_late(s, sample_df):
    out = s.temporal(sample_df, col='timestamp', attack='late', pct=0.5, delta='1000h')
    assert out['timestamp'].min() < sample_df['timestamp'].min()


def test_temporal_future(s, sample_df):
    out = s.temporal(sample_df, col='timestamp', attack='future', pct=0.5, delta='1000h')
    assert out['timestamp'].max() > sample_df['timestamp'].max()


def test_temporal_missing_window(s, sample_df):
    out = s.temporal(
        sample_df, col='timestamp', attack='missing_window',
        window=('2024-01-03', '2024-01-05'),
    )
    in_window = out['timestamp'][
        (out['timestamp'] >= '2024-01-03') & (out['timestamp'] <= '2024-01-05')
    ]
    assert len(in_window) == 0
    assert len(out) < len(sample_df)


def test_temporal_duplicate_ts(s, sample_df):
    out = s.temporal(sample_df, col='timestamp', attack='duplicate_ts', pct=0.2)
    assert out['timestamp'].duplicated().sum() > sample_df['timestamp'].duplicated().sum()


def test_temporal_warns_and_converts_non_datetime(s, sample_df):
    df = sample_df.copy()
    df['timestamp'] = df['timestamp'].astype(str)
    with pytest.warns(UserWarning):
        out = s.temporal(df, col='timestamp', attack='late', pct=0.5, delta='6h')
    assert pd.api.types.is_datetime64_any_dtype(out['timestamp'])


def test_temporal_does_not_mutate_input(s, sample_df):
    before = _hash(sample_df)
    _ = s.temporal(sample_df, col='timestamp', attack='out_of_order', pct=0.2)
    _ = s.temporal(sample_df, col='timestamp', attack='late', pct=0.2)
    _ = s.temporal(sample_df, col='timestamp', attack='duplicate_ts', pct=0.2)
    assert _hash(sample_df) == before
