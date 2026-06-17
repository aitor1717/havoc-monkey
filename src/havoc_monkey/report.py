from dataclasses import dataclass, field, asdict
from html import escape
from typing import Literal, Optional

Severity = Literal['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']
HCResult = Literal['PASSED', 'FAILED', 'ERROR', 'SKIPPED']

_RED = '\033[91m'
_GREEN = '\033[92m'
_YELLOW = '\033[93m'
_GREY = '\033[90m'
_RESET = '\033[0m'

_SEVERITY_COLOR = {
    'CRITICAL': _RED,
    'HIGH': _RED,
    'MEDIUM': _YELLOW,
    'LOW': _GREEN,
    'UNKNOWN': _GREY,
}

_RECOMMENDATIONS = {
    'null_flood': "Add null guard or imputation upstream of pipeline entry.",
    'schema_drift': "Add explicit column existence check before processing.",
    'volume_shock': "Add empty-batch guard and volume cap in pipeline input layer.",
    'outlier_inject': "Add clipping or winsorization to numerical input features.",
    'temporal': "Add timestamp validation and sort before processing.",
    'type_coerce': "Add explicit dtype assertions at pipeline entry.",
}


def get_severity(attack: str, params: dict, hc_result: HCResult) -> Severity:
    if hc_result == 'FAILED':
        if attack == 'schema_drift' or (
            attack == 'volume_shock' and params.get('attack') == 'empty'
        ):
            return 'CRITICAL'
        return 'HIGH'
    if hc_result == 'ERROR':
        return 'MEDIUM'
    if hc_result == 'PASSED':
        return 'LOW'
    return 'UNKNOWN'


def get_recommendation(attack: str, hc_result: HCResult) -> str:
    if hc_result in ('FAILED', 'ERROR'):
        return _RECOMMENDATIONS.get(attack, "Investigate pipeline behavior under this attack.")
    if hc_result == 'PASSED':
        return "Pipeline handled this attack. No action required."
    return "Provide a health_check callable to measure impact."


@dataclass
class AttackResult:
    attack: str
    params: dict
    rows_before: int
    rows_after: int
    schema_before: list
    schema_after: list
    nulls_injected: int
    hc_result: HCResult
    hc_error: Optional[str]
    severity: Severity
    recommendation: str

    def __str__(self) -> str:
        color = _SEVERITY_COLOR.get(self.severity, '')
        tag = f"[{self.severity}]".ljust(11)
        header = f"{color}{tag}{_RESET}"

        subtype = self.params.get('attack')
        extra_params = {k: v for k, v in self.params.items() if k != 'attack'}
        name = f"{self.attack} / {subtype}" if subtype else self.attack
        param_str = "  ".join(f"{k}: {v}" for k, v in extra_params.items())
        line1 = f"{header}{name}"
        if param_str:
            line1 += f"  →  {param_str}"

        indent = " " * 11
        line2 = f"{indent}rows: {self.rows_before}→{self.rows_after}"
        if self.schema_before != self.schema_after:
            line2 += f"  schema: {len(self.schema_before)}→{len(self.schema_after)} cols"
        if self.nulls_injected:
            line2 += f"  nulls injected: {self.nulls_injected}"

        line3 = f"{indent}health_check: {self.hc_result}"
        if self.hc_error:
            line3 += f": {self.hc_error}"

        line4 = f"{indent}→ {self.recommendation}"

        return "\n".join([line1, line2, line3, line4])


@dataclass
class Report:
    seed: int
    total: int
    passed: int
    failed: int
    errors: int
    skipped: int
    results: list = field(default_factory=list)

    def __str__(self) -> str:
        sep = "─" * 60
        not_passed = self.failed + self.errors
        header = (
            f"HAVOC-MONKEY CAMPAIGN REPORT  seed={self.seed}  "
            f"attacks={self.total}  {not_passed}/{self.total} FAILED"
        )

        lines = [header, sep]
        for result in self.results:
            lines.append(str(result))
            lines.append("")
        if self.results:
            lines.pop()
        lines.append(sep)

        severity_counts: dict[str, int] = {}
        for result in self.results:
            severity_counts[result.severity] = severity_counts.get(result.severity, 0) + 1

        order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']
        summary_parts = [
            f"{sev}: {severity_counts[sev]}" for sev in order if sev in severity_counts
        ]
        summary = "  ".join(summary_parts)
        summary += f"  |  passed: {self.passed}/{self.total}"
        lines.append(summary)

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        not_passed = self.failed + self.errors
        lines = [
            f"## havoc-monkey report  `seed={self.seed}`",
            "",
            f"**{not_passed}/{self.total} attacks failed** · "
            f"passed: {self.passed} · failed: {self.failed} · "
            f"errors: {self.errors} · unknown: {self.skipped}",
            "",
            "| Attack | Subtype | Outcome | Severity | Rows | Recommendation |",
            "|--------|---------|---------|----------|------|----------------|",
        ]
        for r in self.results:
            subtype = r.params.get('attack', '-')
            rows = f"{r.rows_before}→{r.rows_after}"
            lines.append(
                f"| `{r.attack}` | {subtype} | **{r.hc_result}** | {r.severity} "
                f"| {rows} | {r.recommendation} |"
            )
        lines += ["", "---", f"*Generated by havoc-monkey · MIT License*"]
        return "\n".join(lines)

    def to_html(self) -> str:
        _OUTCOME_COLOR = {
            'PASSED': '#4caf7d',
            'FAILED': '#F9787C',
            'ERROR': '#FA0A6C',
            'SKIPPED': '#9E9A96',
        }
        _SEV_COLOR = {
            'CRITICAL': '#FA0A6C',
            'HIGH': '#F9787C',
            'MEDIUM': '#FBC990',
            'LOW': '#3DF2CC',
            'UNKNOWN': '#9E9A96',
        }

        not_passed = self.failed + self.errors

        rows_html = ""
        for r in self.results:
            attack = escape(str(r.attack))
            subtype = escape(str(r.params.get('attack', '-')))
            hc_result = escape(str(r.hc_result))
            severity = escape(str(r.severity))
            recommendation = escape(str(r.recommendation))
            row_change = f"{r.rows_before}→{r.rows_after}"
            oc = _OUTCOME_COLOR.get(r.hc_result, '#9E9A96')
            sc = _SEV_COLOR.get(r.severity, '#9E9A96')
            rows_html += f"""
        <tr>
          <td><code>{attack}</code></td>
          <td>{subtype}</td>
          <td><span class="chip" style="background:{oc}22;color:{oc};border:1px solid {oc}66">{hc_result}</span></td>
          <td><span class="chip" style="background:{sc}22;color:{sc};border:1px solid {sc}66">{severity}</span></td>
          <td>{row_change}</td>
          <td>{recommendation}</td>
        </tr>"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>havoc-monkey report · seed={self.seed}</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root{{--peach:#FBC990;--coral:#F9787C;--pink:#FA0A6C;--teal:#14C2C4;--mint:#3DF2CC;
    --charcoal:#1E1E1E;--cream:#FFFBF5;--muted:#9E9A96;
    --sans:'Space Grotesk',sans-serif;--mono:'IBM Plex Mono',monospace;}}
  *{{box-sizing:border-box;margin:0;padding:0;}}
  html,body{{height:100%;}}
  body{{font-family:var(--sans);background:var(--cream);color:var(--charcoal);line-height:1.6;
    min-height:100vh;display:flex;flex-direction:column;}}
  .header{{background:linear-gradient(155deg,var(--peach) 0%,var(--coral) 42%,var(--pink) 100%);
    padding:48px 60px 40px;}}
  .header h1{{font-size:36px;font-weight:800;letter-spacing:-.03em;color:#fff;margin-bottom:6px;}}
  .header .sub{{font-family:var(--mono);font-size:13px;color:rgba(255,255,255,.8);}}
  .stats{{display:flex;gap:32px;margin-top:20px;flex-wrap:wrap;}}
  .stat{{background:rgba(255,255,255,.18);backdrop-filter:blur(6px);border-radius:10px;
    padding:12px 20px;color:#fff;}}
  .stat .val{{font-size:28px;font-weight:800;line-height:1;}}
  .stat .lbl{{font-size:11px;opacity:.75;margin-top:2px;font-family:var(--mono);letter-spacing:.08em;}}
  .body{{flex:1;padding:40px 60px;max-width:1100px;}}
  table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px;}}
  th{{text-align:left;font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;
    color:var(--muted);padding:10px 14px;border-bottom:2px solid #E8E4DE;}}
  td{{padding:14px 14px;border-bottom:1px solid #EEE9E2;vertical-align:middle;}}
  td code{{font-family:var(--mono);font-size:13px;background:#EEE9E2;padding:2px 7px;border-radius:5px;}}
  .chip{{font-family:var(--mono);font-size:11px;font-weight:600;padding:3px 9px;border-radius:100px;
    white-space:nowrap;}}
  footer{{position:relative;background:var(--charcoal);padding:14px 60px;
    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;
    margin-top:24px;}}
  footer .ft{{font-size:12px;color:rgba(255,255,255,.4);font-family:var(--mono);}}
  @media(max-width:700px){{.header,.body,footer{{padding-left:20px;padding-right:20px;}}
    .stats{{gap:12px;}}.stat .val{{font-size:22px;}}}}
</style>
</head>
<body>
<div class="header">
  <h1>havoc<span style="opacity:.7">-monkey</span></h1>
  <div class="sub">seed={self.seed} · {self.total} attacks · {not_passed}/{self.total} failed</div>
  <div class="stats">
    <div class="stat"><div class="val">{self.passed}</div><div class="lbl">PASSED</div></div>
    <div class="stat"><div class="val">{self.failed}</div><div class="lbl">FAILED</div></div>
    <div class="stat"><div class="val">{self.errors}</div><div class="lbl">ERRORS</div></div>
    <div class="stat"><div class="val">{self.skipped}</div><div class="lbl">UNKNOWN</div></div>
  </div>
</div>
<div class="body">
  <table>
    <thead>
      <tr><th>Attack</th><th>Subtype</th><th>Outcome</th><th>Severity</th><th>Rows</th><th>Recommendation</th></tr>
    </thead>
    <tbody>{rows_html}
    </tbody>
  </table>
</div>
<footer>
  <span class="ft">Aitor Bazo · 2026</span>
  <span class="ft">havoc-monkey · MIT</span>
</footer>
</body>
</html>"""
