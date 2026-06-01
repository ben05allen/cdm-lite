# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
