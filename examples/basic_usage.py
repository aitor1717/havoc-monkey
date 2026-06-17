"""Standalone quickstart: run a single attack against a DataFrame."""
import pandas as pd

from havoc_monkey import HavocMonkey

df = pd.read_csv("sample.csv")

monkey = HavocMonkey(seed=42)

attacked = monkey.null_flood(df, cols=["amount"], pct=0.15)
print(f"Nulls injected into 'amount': {attacked['amount'].isna().sum()}")

attacked = monkey.schema_drift(df, attack="drop", col="category")
print(f"Columns after schema_drift: {list(attacked.columns)}")
