import warnings
from typing import Optional

import pandas as pd


def null_flood(self, df: pd.DataFrame, cols: list[str], pct: float = 0.10) -> pd.DataFrame:
    out = df.copy()
    n = int(len(out) * pct)
    for col in cols:
        idx = self.rng.choice(len(out), size=n, replace=False)
        out.iloc[idx, out.columns.get_loc(col)] = None
    return out


def volume_shock(self, df: pd.DataFrame, attack: str = 'empty', factor: float = 10.0, ratio: float = 0.5) -> pd.DataFrame:
    out = df.copy()
    if attack == 'empty':
        return out.iloc[0:0]
    if attack == 'overflow':
        return pd.concat([out] * int(factor), ignore_index=True)
    if attack == 'truncate':
        return out.iloc[:int(len(out) * ratio)]
    raise ValueError(f"Unknown volume_shock attack: {attack!r}")


_TYPE_MAP = {'str': str, 'int': int, 'float': float, 'bool': bool}


def type_coerce(self, df: pd.DataFrame, col: str, target: str = 'str') -> pd.DataFrame:
    if target not in _TYPE_MAP:
        raise ValueError(f"Unknown target dtype {target!r}. Choose from: {list(_TYPE_MAP)}")
    out = df.copy()
    out[col] = out[col].astype(_TYPE_MAP[target])
    return out


def schema_drift(self, df: pd.DataFrame, attack: str = 'drop', col: Optional[str] = None, new_name: Optional[str] = None) -> pd.DataFrame:
    out = df.copy()
    if attack == 'drop':
        return out.drop(columns=[col])
    if attack == 'rename':
        return out.rename(columns={col: new_name})
    if attack == 'add':
        new_col = f"injected_{self.rng.integers(0, 1_000_000)}"
        out[new_col] = self.rng.random(len(out))
        return out
    if attack == 'reorder':
        shuffled = self.rng.permutation(out.columns)
        return out[shuffled]
    raise ValueError(f"Unknown schema_drift attack: {attack!r}")


def outlier_inject(self, df: pd.DataFrame, cols: list[str], sigma: float = 5.0, pct: float = 0.05) -> pd.DataFrame:
    out = df.copy()
    n = int(len(out) * pct)
    for col in cols:
        mean = df[col].mean()
        std = df[col].std()
        idx = self.rng.choice(len(out), size=n, replace=False)
        signs = self.rng.choice([-1, 1], size=n)
        out[col] = out[col].astype(float)  # pandas 3.0+ requires explicit cast before float assignment
        out.iloc[idx, out.columns.get_loc(col)] = mean + signs * sigma * std
    return out


def temporal(self, df: pd.DataFrame, col: str, attack: str = 'out_of_order', pct: float = 0.10, delta: str = '2h', window: Optional[tuple] = None) -> pd.DataFrame:
    out = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(out[col]):
        warnings.warn(
            f"Column '{col}' is not datetime dtype; converting with pd.to_datetime.",
            UserWarning,
        )
        out[col] = pd.to_datetime(out[col])

    loc = out.columns.get_loc(col)
    n = int(len(out) * pct)

    if attack == 'out_of_order':
        idx = self.rng.choice(len(out), size=n, replace=False)
        values = out.iloc[idx, loc].to_numpy()
        out.iloc[idx, loc] = self.rng.permutation(values)
        return out

    if attack == 'late':
        idx = self.rng.choice(len(out), size=n, replace=False)
        out.iloc[idx, loc] = out.iloc[idx, loc] - pd.Timedelta(delta)
        return out

    if attack == 'future':
        idx = self.rng.choice(len(out), size=n, replace=False)
        out.iloc[idx, loc] = out.iloc[idx, loc] + pd.Timedelta(delta)
        return out

    if attack == 'missing_window':
        start, end = pd.Timestamp(window[0]), pd.Timestamp(window[1])
        mask = (out[col] >= start) & (out[col] <= end)
        return out[~mask]

    if attack == 'duplicate_ts':
        idx = self.rng.choice(len(out), size=n, replace=False)
        source_idx = self.rng.choice(len(out), size=n)
        out.iloc[idx, loc] = out.iloc[source_idx, loc].to_numpy()
        return out

    raise ValueError(f"Unknown temporal attack: {attack!r}")
