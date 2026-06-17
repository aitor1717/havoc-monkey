def test_fixture_available_without_import(pytester):
    pytester.makepyfile("""
        def test_uses_fixture(havoc_monkey_instance):
            assert havoc_monkey_instance.seed == 42
    """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)


def test_havoc_seed_option_overrides_default(pytester):
    pytester.makepyfile("""
        def test_seed(havoc_monkey_instance):
            assert havoc_monkey_instance.seed == 99
    """)
    result = pytester.runpytest("--havoc-seed=99")
    result.assert_outcomes(passed=1)


def test_marker_registered_no_warning(pytester):
    pytester.makepyfile("""
        import pytest

        @pytest.mark.havoc_monkey(attacks=['null_flood'])
        def test_marked():
            assert True
    """)
    result = pytester.runpytest()
    result.assert_outcomes(passed=1)
    result.stdout.no_fnmatch_line("*PytestUnknownMarkWarning*")


def test_campaign_report_attached_on_failure(pytester):
    pytester.makepyfile("""
        import pytest
        import pandas as pd
        import numpy as np

        @pytest.fixture
        def df():
            return pd.DataFrame({'amount': np.arange(100, dtype=float)})

        @pytest.mark.havoc_monkey(attacks=['null_flood'])
        def test_campaign(havoc_monkey_instance, df):
            def hc(d):
                assert d['amount'].notnull().all()

            report = havoc_monkey_instance.campaign(
                df,
                attacks=[{'name': 'null_flood', 'params': {'cols': ['amount']}}],
                health_check=hc,
            )
            assert report.failed == 0
    """)
    result = pytester.runpytest("-rA")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*havoc-monkey campaign report*"])
