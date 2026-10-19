# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0b1] - 2026-10-19

### Added

- Official support for Python 3.15 (trove classifier, README badge and `check_versions.sh` coverage).
- PEP 810 explicit lazy imports via `__lazy_modules__` in `cli.py`, `registry.py` and `downloader.py`. On Python 3.15+ the CLI defers `cdm_lite.generator` (and its `datamodel-code-generator` dependency tree), `cdm_lite.downloader`, `cdm_lite.cleaner` and `httpx` until first use, reducing `import cdm_lite.cli` time from ~360 ms to ~95 ms. On Python < 3.15 the declaration is ignored and imports remain eager, so behaviour is unchanged.

### Changed

- Minimum dependency versions raised for Python 3.15 support: `pydantic>=2.14.0` and `datamodel-code-generator[ruff]>=0.86.0`.
- Added `anyio>=4.14.2` constraint for downstream dependency resolution.

## [0.4.0b3] - 2026-08-18

### Changed

- Cyclomatic complexity threshold lowered from 18 to 10 (enforced by `ruff` `C901` and `complexipy`).
- `complexipy` pre-commit hook now uses a local `uv run` invocation, matching the `ruff` and `ty` hooks.
- Added `complexipy` to the dev dependency group.

### Fixed

- `install` no longer skips model generation for versions that are cleaned but not yet generated.

## [0.4.0b2] - 2026-08-17

### Added

- Cyclomatic complexity enforcement via `complexipy` and ruff `C901` in pre-commit hooks.
- Type-checking via `ty` in pre-commit hooks.

### Changed

- Pre-commit hooks for ruff and ty now use local `uv run` invocations, ensuring dev-dependency versions are used.
- Build backend `uv_build` minimum version bumped from 0.11.7 to 0.12.5.
- ruff configuration moved from `pyproject.toml` to dedicated `ruff.toml`; expanded default rule set from ruff 0.16 upgrade.
- Dev dependencies: `ruff` 0.15.12 → 0.16.3, `ty` 0.0.34 → 0.0.72.

### Fixed

- Blind `except Exception` warnings (`BLE001`) are now explicitly ignored — the pattern is deliberate in CLI code that calls `_abort()`.
- Added `.complexipy_cache/` to `.gitignore`.

## [0.4.0b1] - 2026-06-01

### Added

- Official Beta release.
- Added `CHANGELOG.md` to track project evolution.

## [0.3.2a1] - 2026-05-30

### Added

- Support for both `.zip` and `.tar` archives in downloader.
- `cdm-lite remove <version>` command to manage local cache.
- Comprehensive CI workflow for Python 3.11 through 3.14 across platforms.
- Pre-commit hooks for automated linting and formatting.

### Fixed

- Improved sanitization of illegal characters in JSON schemas.
- Pathing fixes for Windows compatibility.
- Resolved zip file detection logic in `downloader.py`.

### Changed

- Refined model output directory structure.
- Updated README with detailed Scope & Limitations for CDM deserialization.
