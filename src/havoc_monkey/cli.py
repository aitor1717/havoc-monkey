import warnings

import click
import pandas as pd

from havoc_monkey.core import HavocMonkey

ATTACK_TABLE = [
    ("null_flood", "-", "cols: list[str], pct: float=0.10"),
    ("volume_shock", "empty / overflow / truncate", "factor: float=10.0, ratio: float=0.5"),
    ("type_coerce", "str / int / float / bool", "col: str, target: str"),
    ("schema_drift", "drop / rename / add / reorder", "col: str, new_name: str"),
    ("outlier_inject", "-", "cols: list[str], sigma: float=5.0, pct: float=0.05"),
    ("temporal", "out_of_order / late / future / missing_window / duplicate_ts",
     "col: str, pct: float=0.10, delta: str='2h', window: tuple"),
]


def _pick_datetime_col(df):
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                pd.to_datetime(df[col])
            return col
        except (ValueError, TypeError):
            continue
    return None


def _build_spec(name, df):
    if name == 'null_flood':
        return {'name': name, 'params': {'cols': list(df.columns)}}
    if name == 'outlier_inject':
        numeric = df.select_dtypes(include='number').columns.tolist()
        return {'name': name, 'params': {'cols': numeric}}
    if name in ('type_coerce', 'schema_drift'):
        return {'name': name, 'params': {'col': df.columns[0]}}
    if name == 'temporal':
        col = _pick_datetime_col(df)
        if col is None:
            return None
        return {'name': name, 'params': {'col': col}}
    return name


def _load_file(file_path: str) -> pd.DataFrame:
    ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''
    if ext in ('parquet', 'pq'):
        return pd.read_parquet(file_path)
    if ext == 'json':
        return pd.read_json(file_path)
    return pd.read_csv(file_path)


@click.group()
def main():
    """havoc-monkey: deliberate failure injection for data pipelines."""


@main.command()
@click.option('--file', 'file_path', required=True, type=click.Path(exists=True, dir_okay=False),
              help="CSV, JSON, or Parquet file to load.")
@click.option('--attacks', multiple=True, required=True,
              help="Attack(s) to run. May be given multiple times.")
@click.option('--seed', default=42, type=int, show_default=True, help="RNG seed.")
@click.option('--output', default=None, type=click.Path(dir_okay=False),
              help="Save report to file. Extension determines format: .html, .md, or plain text.")
def run(file_path, attacks, seed, output):
    """Run a document-only campaign against a CSV, JSON, or Parquet file (no health check)."""
    try:
        df = _load_file(file_path)
    except Exception as e:
        click.echo(f"Error loading {file_path}: {e}", err=True)
        raise SystemExit(1)

    s = HavocMonkey(seed=seed)

    specs = []
    for name in attacks:
        spec = _build_spec(name, df)
        if spec is None:
            click.echo(f"Skipping '{name}': no usable column found in {file_path}", err=True)
            continue
        specs.append(spec)

    try:
        report = s.campaign(df, attacks=specs)
    except Exception as e:
        click.echo(f"Campaign failed: {e}", err=True)
        raise SystemExit(1)

    if output:
        ext = output.rsplit('.', 1)[-1].lower() if '.' in output else ''
        if ext == 'html':
            content = report.to_html()
        elif ext == 'md':
            content = report.to_markdown()
        else:
            content = str(report)
        with open(output, 'w', encoding='utf-8') as f:
            f.write(content)
        click.echo(f"Report saved to {output}")
    else:
        click.echo(str(report))


@main.command(name='list-attacks')
def list_attacks():
    """Print a table of all available attacks with subtypes and params."""
    rows = [("ATTACK", "SUBTYPES", "PARAMS")] + ATTACK_TABLE
    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    for row in rows:
        click.echo("  ".join(cell.ljust(width) for cell, width in zip(row, widths)))
