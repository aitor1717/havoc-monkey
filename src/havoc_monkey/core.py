from typing import Callable, List, Optional, Union

import numpy as np
import pandas as pd

from havoc_monkey.attacks import (
    null_flood,
    volume_shock,
    type_coerce,
    schema_drift,
    outlier_inject,
    temporal,
)
from havoc_monkey.report import AttackResult, HCResult, Report, get_recommendation, get_severity


class HavocMonkey:
    def __init__(self, seed: int = 42, verbose: bool = True) -> None:
        self.seed = seed
        self.verbose = verbose
        self.rng = np.random.default_rng(seed)
        self.last_report: Optional[Report] = None

    null_flood = null_flood
    volume_shock = volume_shock
    type_coerce = type_coerce
    schema_drift = schema_drift
    outlier_inject = outlier_inject
    temporal = temporal

    def __enter__(self) -> "HavocMonkey":
        return self

    def __exit__(self, *args) -> None:
        pass

    def campaign(
        self,
        df: pd.DataFrame,
        attacks: List[Union[str, dict]],
        health_check: Optional[Callable] = None,
    ) -> Report:
        results = []
        for spec in attacks:
            if isinstance(spec, dict):
                name, params = spec['name'], spec.get('params', {})
            else:
                name, params = spec, {}

            attacked = getattr(self, name)(df, **params)

            nulls_before = int(df.isna().sum().sum())
            nulls_after = int(attacked.isna().sum().sum())
            nulls_injected = max(0, nulls_after - nulls_before)

            hc_result: HCResult
            if health_check is None:
                hc_result, hc_error = 'SKIPPED', None
            else:
                try:
                    health_check(attacked)
                    hc_result, hc_error = 'PASSED', None
                except AssertionError as e:
                    hc_result = 'FAILED'
                    hc_error = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                except Exception as e:
                    hc_result = 'ERROR'
                    hc_error = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__

            severity = get_severity(name, params, hc_result)
            recommendation = get_recommendation(name, hc_result)

            results.append(AttackResult(
                attack=name,
                params=params,
                rows_before=len(df),
                rows_after=len(attacked),
                schema_before=list(df.columns),
                schema_after=list(attacked.columns),
                nulls_injected=nulls_injected,
                hc_result=hc_result,
                hc_error=hc_error,
                severity=severity,
                recommendation=recommendation,
            ))

        report = Report(
            seed=self.seed,
            total=len(results),
            passed=sum(r.hc_result == 'PASSED' for r in results),
            failed=sum(r.hc_result == 'FAILED' for r in results),
            errors=sum(r.hc_result == 'ERROR' for r in results),
            skipped=sum(r.hc_result == 'SKIPPED' for r in results),
            results=results,
        )
        self.last_report = report
        return report
