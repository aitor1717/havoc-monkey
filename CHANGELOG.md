# Changelog

All notable changes to this project will be documented in this file.

## [0.1.1] - 2026-06-17

### Changed
- `Report.to_html()` footer redesigned to match the docs site's footer band (thinner, no icons, `havoc-monkey · MIT`)

### Fixed
- Grammatical run-ons (comma splices) left over from an earlier em-dash cleanup pass, across the README and docs site

## [0.1.0] - 2026-06-17

### Added
- Six attacks: `null_flood`, `volume_shock`, `type_coerce`, `schema_drift`, `outlier_inject`, `temporal`
- `HavocMonkey` class with seeded, reproducible RNG (`np.random.default_rng`)
- `campaign()` runner with `health_check` callback and `AttackResult`/`Report` dataclasses
- Context manager support (`with HavocMonkey(seed=42) as monkey`)
- Severity classification (CRITICAL/HIGH/MEDIUM/LOW/UNKNOWN) and per-attack recommendations
- `Report.to_dict()`, `Report.to_markdown()`, `Report.to_html()` export methods
- Pytest plugin: `havoc_monkey_instance` fixture, `--havoc-seed` option, `@pytest.mark.havoc_monkey` marker
- Click CLI: `havoc-monkey run` (CSV, JSON, Parquet) and `havoc-monkey list-attacks`
- CLI `--output` flag: saves report as `.html`, `.md`, or plain text by extension
- PEP 561 `py.typed` marker and type hints on all public methods
- Examples: `basic_usage.py`, `with_health_check.py`, `pytest_example/`
- Full test suite (65 tests) with GitHub Actions CI on Python 3.9–3.13
- Docs site (`docs/`) with landing page, examples, and API manual

### Fixed
- `outlier_inject` crashed on `int64` columns with pandas 3.0+ (now casts to float before assignment)
- `type_coerce` raised a bare `KeyError` for unknown targets (now raises `ValueError` with valid options)
- Pytest plugin `hookwrapper=True` migrated to `wrapper=True` for pytest 8+ compatibility
