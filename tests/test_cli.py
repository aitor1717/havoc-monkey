import pytest
from click.testing import CliRunner

from havoc_monkey.cli import main


def _write_csv(tmp_path, df):
    path = tmp_path / "data.csv"
    df.to_csv(path, index=False)
    return str(path)


def _write_parquet(tmp_path, df):
    pytest.importorskip("pyarrow")
    path = tmp_path / "data.parquet"
    df.to_parquet(path, index=False)
    return str(path)


def _write_json(tmp_path, df):
    path = tmp_path / "data.json"
    df.to_json(path, orient='records')
    return str(path)


def test_list_attacks_shows_all_six(s):
    runner = CliRunner()
    result = runner.invoke(main, ["list-attacks"])
    assert result.exit_code == 0
    for attack in [
        'null_flood', 'volume_shock', 'type_coerce',
        'schema_drift', 'outlier_inject', 'temporal',
    ]:
        assert attack in result.output


def test_run_single_attack(tmp_path, sample_df):
    csv_path = _write_csv(tmp_path, sample_df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", csv_path, "--attacks", "null_flood", "--seed", "42"])
    assert result.exit_code == 0
    assert "HAVOC-MONKEY CAMPAIGN REPORT" in result.output
    assert "null_flood" in result.output


def test_run_multiple_attacks(tmp_path, sample_df):
    csv_path = _write_csv(tmp_path, sample_df)
    runner = CliRunner()
    result = runner.invoke(main, [
        "run", "--file", csv_path,
        "--attacks", "null_flood", "--attacks", "schema_drift", "--attacks", "temporal",
        "--seed", "42",
    ])
    assert result.exit_code == 0
    assert "attacks=3" in result.output


def test_run_missing_file(tmp_path):
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", str(tmp_path / "nope.csv"), "--attacks", "null_flood"])
    assert result.exit_code != 0


def test_run_parquet_file(tmp_path, sample_df):
    parquet_path = _write_parquet(tmp_path, sample_df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", parquet_path, "--attacks", "null_flood", "--seed", "42"])
    assert result.exit_code == 0
    assert "HAVOC-MONKEY CAMPAIGN REPORT" in result.output


def test_run_json_file(tmp_path, sample_df):
    json_path = _write_json(tmp_path, sample_df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", json_path, "--attacks", "null_flood", "--seed", "42"])
    assert result.exit_code == 0
    assert "HAVOC-MONKEY CAMPAIGN REPORT" in result.output


def test_run_output_html(tmp_path, sample_df):
    csv_path = _write_csv(tmp_path, sample_df)
    out_path = str(tmp_path / "report.html")
    runner = CliRunner()
    result = runner.invoke(main, [
        "run", "--file", csv_path, "--attacks", "null_flood", "--seed", "42",
        "--output", out_path,
    ])
    assert result.exit_code == 0
    assert "Report saved to" in result.output
    with open(out_path) as f:
        html = f.read()
    assert "<!DOCTYPE html>" in html
    assert "null_flood" in html


def test_run_output_markdown(tmp_path, sample_df):
    csv_path = _write_csv(tmp_path, sample_df)
    out_path = str(tmp_path / "report.md")
    runner = CliRunner()
    result = runner.invoke(main, [
        "run", "--file", csv_path, "--attacks", "null_flood", "--seed", "42",
        "--output", out_path,
    ])
    assert result.exit_code == 0
    with open(out_path) as f:
        md = f.read()
    assert "## havoc-monkey report" in md


def test_run_output_plain_text_for_unknown_extension(tmp_path, sample_df):
    csv_path = _write_csv(tmp_path, sample_df)
    out_path = str(tmp_path / "report.txt")
    runner = CliRunner()
    result = runner.invoke(main, [
        "run", "--file", csv_path, "--attacks", "null_flood", "--seed", "42",
        "--output", out_path,
    ])
    assert result.exit_code == 0
    with open(out_path) as f:
        text = f.read()
    assert "HAVOC-MONKEY CAMPAIGN REPORT" in text


def test_run_outlier_inject_via_cli(tmp_path, sample_df):
    csv_path = _write_csv(tmp_path, sample_df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", csv_path, "--attacks", "outlier_inject", "--seed", "42"])
    assert result.exit_code == 0
    assert "outlier_inject" in result.output


def test_run_attack_without_special_case_uses_defaults(tmp_path, sample_df):
    csv_path = _write_csv(tmp_path, sample_df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", csv_path, "--attacks", "volume_shock", "--seed", "42"])
    assert result.exit_code == 0
    assert "volume_shock" in result.output


def test_run_temporal_skipped_when_no_datetime_column(tmp_path):
    import pandas as pd
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    csv_path = _write_csv(tmp_path, df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", csv_path, "--attacks", "temporal", "--seed", "42"])
    assert result.exit_code == 0
    assert "Skipping 'temporal'" in result.output


def test_run_picks_up_string_datetime_column(tmp_path):
    import pandas as pd
    df = pd.DataFrame({
        "a": [1, 2, 3],
        "when": ["2024-01-01", "2024-01-02", "2024-01-03"],
    })
    csv_path = _write_csv(tmp_path, df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", csv_path, "--attacks", "temporal", "--seed", "42"])
    assert result.exit_code == 0
    assert "temporal" in result.output
    assert "Skipping" not in result.output


def test_run_picks_up_real_datetime_column_from_parquet(tmp_path, sample_df):
    parquet_path = _write_parquet(tmp_path, sample_df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", parquet_path, "--attacks", "temporal", "--seed", "42"])
    assert result.exit_code == 0
    assert "temporal" in result.output
    assert "Skipping" not in result.output


def test_run_unloadable_file_reports_error(tmp_path):
    bad_path = tmp_path / "data.parquet"
    bad_path.write_text("not actually parquet")
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", str(bad_path), "--attacks", "null_flood"])
    assert result.exit_code != 0
    assert "Error loading" in result.output


def test_run_campaign_failure_reports_error(tmp_path, sample_df):
    csv_path = _write_csv(tmp_path, sample_df)
    runner = CliRunner()
    result = runner.invoke(main, ["run", "--file", csv_path, "--attacks", "not_a_real_attack"])
    assert result.exit_code != 0
    assert "Campaign failed" in result.output
