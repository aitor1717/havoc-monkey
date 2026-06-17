"""Example pytest suite using the havoc-monkey plugin.

Run with: pytest examples/pytest_example/ --havoc-seed 42
"""
import pandas as pd
import pytest


def my_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    assert "category" in df.columns, "missing required column: category"
    assert df["amount"].notnull().all(), "amount column contains nulls"
    return df.groupby("category")["amount"].sum().reset_index()


@pytest.fixture
def my_df():
    return pd.DataFrame({
        "amount": [10.0, 20.0, 30.0, 40.0],
        "category": ["A", "B", "A", "B"],
    })


# Pattern A, fixture: attack a DataFrame directly and feed it to the pipeline.
def test_handles_nulls(havoc_monkey_instance, my_df):
    attacked = havoc_monkey_instance.null_flood(my_df, cols=["amount"], pct=0.5)
    with pytest.raises(AssertionError):
        my_pipeline(attacked)


def test_survives_schema_drop(havoc_monkey_instance, my_df):
    attacked = havoc_monkey_instance.schema_drift(my_df, attack="add")
    result = my_pipeline(attacked)
    assert result is not None


# Pattern B, marker: run a full campaign and assert on the report.
@pytest.mark.havoc_monkey(attacks=["null_flood", "schema_drift", "volume_shock"])
def test_pipeline_resilience(havoc_monkey_instance, my_df):
    def hc(df):
        result = my_pipeline(df)
        assert len(result) > 0, "empty output"
        return True

    report = havoc_monkey_instance.campaign(
        my_df,
        attacks=[
            {"name": "null_flood", "params": {"cols": ["amount"], "pct": 0.5}},
            {"name": "schema_drift", "params": {"attack": "drop", "col": "category"}},
            {"name": "volume_shock", "params": {"attack": "empty"}},
        ],
        health_check=hc,
    )
    # This pipeline has no guards, so every attack is expected to break it.
    assert report.failed + report.errors == report.total
