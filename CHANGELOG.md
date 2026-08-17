# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
