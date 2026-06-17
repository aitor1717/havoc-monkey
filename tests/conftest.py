import numpy as np
import pandas as pd
import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def sample_df():
    rng = np.random.default_rng(0)
    n = 200
    return pd.DataFrame({
        'id': range(n),
        'amount': rng.normal(100, 20, n),
        'category': rng.choice(['A', 'B', 'C'], n),
        'timestamp': pd.date_range('2024-01-01', periods=n, freq='h'),
        'score': rng.uniform(0, 1, n),
        'count': rng.integers(1, 50, n),
    })


@pytest.fixture
def s():
    from havoc_monkey import HavocMonkey
    return HavocMonkey(seed=42)
