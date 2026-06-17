"""Run a full campaign against a DataFrame with a health_check callback."""
import pandas as pd

from havoc_monkey import HavocMonkey


def my_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """A toy pipeline that's intolerant of nulls and missing columns."""
    assert "category" in df.columns, "missing required column: category"
    assert df["amount"].notnull().all(), "amount column contains nulls"
    return df.groupby("category")["amount"].sum().reset_index()


def health_check(df: pd.DataFrame) -> bool:
    result = my_pipeline(df)
    assert len(result) > 0, "empty output"
    return True


df = pd.read_csv("sample.csv")
monkey = HavocMonkey(seed=42)

report = monkey.campaign(
    df,
    attacks=[
        {"name": "null_flood", "params": {"cols": ["amount"], "pct": 0.3}},
        {"name": "schema_drift", "params": {"attack": "drop", "col": "category"}},
        {"name": "volume_shock", "params": {"attack": "empty"}},
    ],
    health_check=health_check,
)

print(report)
