# havoc-monkey

[![Tests](https://github.com/aitor1717/havoc-monkey/actions/workflows/test.yml/badge.svg)](https://github.com/aitor1717/havoc-monkey/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/havoc-monkey)](https://pypi.org/project/havoc-monkey/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> Deliberate failure injection for data pipelines.

## Why

Pipelines fail silently. A renamed column, a batch of nulls, a late timestamp: none of these raise an exception, they just quietly corrupt your output. havoc-monkey applies the same idea as Chaos Monkey to data: a seeded, reproducible injector that breaks your pipeline's input on purpose, so you find the gaps before production does.

Requires Python 3.9+.

## Install

```bash
pip install havoc-monkey
```

## Quickstart

```python
import pandas as pd
from havoc_monkey import HavocMonkey

df = pd.read_csv("data.csv")
monkey = HavocMonkey(seed=42)

attacked = monkey.null_flood(df, cols=["amount"], pct=0.15)

report = monkey.campaign(
    df,
    attacks=["null_flood", "schema_drift"],
    health_check=lambda d: my_pipeline(d) is not None,
)
print(report)
```

## Attacks

| Attack | What | Subtypes / Params |
| --- | --- | --- |
| `null_flood` | Inject `pct`% nulls into specified columns. | `cols: list[str]`, `pct: float=0.10` |
| `volume_shock` | Return an empty DataFrame, an N× overflow, or a truncated batch. | `attack: empty/overflow/truncate`, `factor: float=10.0`, `ratio: float=0.5` |
| `type_coerce` | Silently change a column's dtype. | `col: str`, `target: str/int/float/bool` |
| `schema_drift` | Drop, rename, add, or reorder columns. | `attack: drop/rename/add/reorder`, `col: str`, `new_name: str` |
| `outlier_inject` | Push `pct`% of values to `sigma` standard deviations beyond the column's distribution. | `cols: list[str]`, `sigma: float=5.0`, `pct: float=0.05` |
| `temporal` | Out-of-order, late, future, missing-window, or duplicate timestamps. | see below |

All attacks return `df.copy()`. The input DataFrame is never mutated.

## Temporal Attacks

`temporal()` requires a datetime column. If the column isn't already datetime, havoc-monkey will warn and convert it with `pd.to_datetime`.

```python
monkey.temporal(df, col="timestamp", attack="out_of_order", pct=0.2)
monkey.temporal(df, col="timestamp", attack="late", delta="6h")
monkey.temporal(df, col="timestamp", attack="future", delta="6h")
monkey.temporal(df, col="timestamp", attack="missing_window", window=("2024-03-01", "2024-03-07"))
monkey.temporal(df, col="timestamp", attack="duplicate_ts", pct=0.1)
```

| Subtype | Effect |
| --- | --- |
| `out_of_order` | Shuffles `pct`% of timestamps. |
| `late` | Subtracts `delta` from `pct`% of rows. |
| `future` | Adds `delta` to `pct`% of rows. |
| `missing_window` | Drops all rows with a timestamp inside `window`. |
| `duplicate_ts` | Duplicates `pct`% of timestamps onto other rows. |

## Health Check Pattern

A `health_check` is a callable that takes the attacked DataFrame and defines what "working" means for your pipeline:

```python
def health_check(df: pd.DataFrame) -> bool:
    result = my_pipeline(df)
    assert result["amount"].notnull().all(), "nulls leaked"
    assert len(result) > 0, "empty output"
    return True

report = monkey.campaign(df, attacks=["null_flood", "schema_drift"], health_check=health_check)
```

Each attack in a campaign runs against the **original** DataFrame, not the output of the previous attack. This is intentional: it lets each attack measure pipeline resilience to a single failure mode in isolation.

Each attack's outcome is classified as:

- **FAILED**: `health_check` raised `AssertionError`. Your pipeline's own guard caught the bad data and stopped, which is the assertion doing its job, but the run still broke.
- **ERROR**: `health_check` raised any other exception. Your pipeline crashed outright, with no assertion catching it first.
- **PASSED**: `health_check` returned without error. Your pipeline handled the attack.
- **SKIPPED**: no `health_check` was provided. Severity is reported as `UNKNOWN`; havoc-monkey only documents the change, it can't measure impact without one.

## Pytest Plugin

Installing havoc-monkey auto-registers a pytest plugin. No imports needed.

**Pattern A, fixture (direct attack):**

```python
def test_handles_nulls(havoc_monkey_instance, my_df):
    attacked = havoc_monkey_instance.null_flood(my_df, cols=["amount"])
    result = my_pipeline(attacked)
    assert result["total"].notnull().all()
```

**Pattern B, marker (full campaign):**

```python
import pytest

@pytest.mark.havoc_monkey(attacks=["null_flood", "schema_drift", "volume_shock"])
def test_pipeline_resilience(havoc_monkey_instance, my_df):
    def hc(df):
        return my_pipeline(df) is not None

    report = havoc_monkey_instance.campaign(
        my_df,
        attacks=["null_flood", "schema_drift", "volume_shock"],
        health_check=hc,
    )
    assert report.failed == 0
```

When a `@pytest.mark.havoc_monkey` test fails, the campaign report is attached to the test output.

Override the seed with `--havoc-seed`:

```bash
pytest --havoc-seed 99
```

## Report Export

```python
print(report)            # ANSI-coloured terminal summary
report.to_dict()         # serialisable dict
report.to_markdown()     # GitHub-flavoured Markdown table, paste into PR comments or CI artifacts
report.to_html()         # self-contained branded HTML file, open in a browser or share as-is
```

## CLI

Accepts CSV, JSON, and Parquet files; format is detected from the extension.

```bash
havoc-monkey run --file data.csv --attacks null_flood --attacks schema_drift --seed 42
havoc-monkey run --file data.parquet --attacks null_flood --output report.md
havoc-monkey run --file data.json --attacks schema_drift --output report.html
```

`run` is document-only: no `health_check` is run, so every result is `UNKNOWN` severity. Use `--output` to save the report: `.html` for a shareable file, `.md` for a CI artifact, anything else for plain text.

```bash
havoc-monkey list-attacks
```

Prints a table of every attack with its subtypes and parameters.

## Documentation

Full docs, including the API reference and worked examples, are at [aitor1717.github.io/havoc-monkey](https://aitor1717.github.io/havoc-monkey/).

## Development

```bash
pip install -e ".[dev]"
coverage run -m pytest tests/
coverage report -m
mypy src/havoc_monkey --ignore-missing-imports
```

Use `coverage run`, not `pytest --cov`: havoc-monkey registers itself as a pytest plugin via a `pytest11` entry point, so it gets imported before `pytest-cov` attaches, which makes `pytest --cov` undercount coverage by 20+ points and warn about an unmeasured module. `coverage run -m pytest` measures from process start and doesn't have this problem.

CI also runs on Windows and macOS across the full Python 3.9-3.13 matrix, type-checks with `mypy`, and verifies the package against its declared minimum dependency versions (`pandas==1.5.3`, `numpy==1.23.5`).

## License

MIT
