# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2026-06-19

First stable release. The public API (`HavocMonkey`, the six attacks, `campaign()`, `Report`, the pytest plugin, and the CLI) is considered settled; breaking changes will land behind a major version bump going forward.

### Changed
- PyPI classifier bumped from "4 - Beta" to "5 - Production/Stable"
- README, docs site, and cover assets polished for launch (mobile layout fixes, lighter-weight cover GIF, unified nav styling across pages)
- `sdist` build now excludes `docs/` (the GitHub Pages source and generated assets), which had been bloating the source distribution with files irrelevant to an installed package

## [0.9.0] - 2026-06-17

Signals production-readiness: builds on 0.1.2's type-checking, 100% coverage, and widened CI matrix.

### Changed
- `Report.to_html()` stat tiles (PASSED/FAILED/ERRORS/UNKNOWN) now use a charcoal tint instead of a pale white overlay, which washed out against the gradient header
- PyPI classifier bumped from "3 - Alpha" to "4 - Beta"

## [0.1.2] - 2026-06-17

### Fixed
- `@pytest.mark.havoc_monkey`'s registered description no longer claims it runs the campaign for you; it only attaches the last report on failure, matching actual behavior
- `outlier_inject` now warns and skips columns with zero or undefined standard deviation instead of silently no-opping or injecting `NaN` (and mislabeling it as "nulls injected")
- `temporal(attack='missing_window')` now raises a clear `ValueError` when `window` is omitted, instead of crashing with `TypeError: 'NoneType' object is not subscriptable`
- `null_flood`, `outlier_inject`, and `temporal` now raise a clear `ValueError` for an out-of-range `pct`, instead of a raw, unrelated numpy error
- `Report.to_html()` now HTML-escapes all interpolated fields, closing a latent stored-HTML-injection risk
- Coverage measurement: CI and local runs now use `coverage run -m pytest` instead of `pytest --cov`, which was undercounting coverage by 20+ points due to the package's own `pytest11` entry point importing it before `pytest-cov` could attach
- 5 `mypy` errors fixed across `attacks.py`, `core.py`, and `report.py`; the package now type-checks cleanly, which `py.typed` had been implicitly promising but not delivering
- `audit_report_2.html` (an internal, untracked audit artifact) was being picked up by the sdist build; added to `.gitignore` before it could ship inside a published package

### Changed
- `dev` extras: `pytest-cov` replaced with `coverage` (used directly, no longer through pytest-cov's integration); added `mypy`
- README: added a "Development" section documenting the correct local test/coverage/type-check commands
- CI: now runs on `ubuntu-latest`, `windows-latest`, and `macos-latest` (previously Linux only); added a `typecheck` job (`mypy`) and a `minimum-versions` job verifying the package against its declared floors (`pandas==1.5.3`, `numpy==1.23.5`)
- Test suite expanded to 84 tests (from 65), reaching 100% line coverage on `src/havoc_monkey/`
- Docs manual: documents the `pct` range contract, the `outlier_inject` zero-variance warning, and `missing_window`'s required `window` argument

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
