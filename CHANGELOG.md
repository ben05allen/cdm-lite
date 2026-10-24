# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.1] - 2026-10-24

Release automation hardening. No changes to the CLI or to the generated models.

### Changed

- The release workflow now checks whether every artifact for the version already exists on PyPI (by filename) and skips the upload entirely when the release is complete, making tag pushes and workflow re-runs idempotent. Partial uploads send only the files missing from the index. Hash-based duplicate detection does not work across build environments because the wheel embeds the `Generator: uv <version>` stamp.
- The release process documentation (bump script, tag flow, PyPI trusted publisher setup) moved from the README into CONTRIBUTING.md, which also covers local development commands.

## [0.6.0] - 2026-10-22

First stable (non-beta) release. The CLI surface, the on-disk cache layout and the layout of the
generated models are now covered by semantic versioning guarantees.

### Added

- `cdm-lite upgrade` installs the target CDM version (default: latest stable) and makes it active in one step, regenerating stale models along the way.
- Generated models are invalidated automatically when the installed `cdm-lite` or `datamodel-code-generator` version changes: `cdm-lite install` re-cleans and re-generates only the affected stages, and `cdm-lite status` warns when the local models are stale.
- Schema downloads are verified against the SHA-1 checksum published on Maven Central; when the index publishes none, verification is skipped. The digest is stored in `status.json` and shown by `cdm-lite status`.
- Version discovery works offline: the last Maven Central metadata response is cached in the cache directory and reused when the network is unavailable; `cdm-lite versions` says so when it serves the cached copy.
- CI now runs the `prek` hooks (`ruff`, `ruff format`, `ty`, `complexipy`) on every push and pull request, so the checks can no longer be bypassed by skipping local hooks.
- CI gained a build job that builds the sdist and wheel, installs the wheel into a clean environment and smoke tests `cdm-lite --version`.
- CI now tests Python 3.15, matching the versions advertised in the README and the trove classifiers.
- Coverage is measured in CI and enforced at a floor of 85% (`pytest-cov` added to the development dependencies).
- Dependabot configuration for the `uv` lock file and GitHub Actions.
- Releases are published to PyPI automatically from a `v*` tag using Trusted Publishing (OIDC), so no API token is stored in GitHub. The workflow verifies the tag matches the project version and that the CHANGELOG documents it, and skips files already present on PyPI so re-runs and manual-first releases cannot fail on duplicate uploads.
- `scripts/bump_version.py` updates the version, the development status classifier, the README status line and the CHANGELOG in a single command, so those references can no longer drift apart.
- CI fails when the CHANGELOG has no entry for the version in `pyproject.toml`.

### Fixed

- README: the example import used the distribution name `cdm-models` as a module name, which is not importable Python. It now shows the real path, `from cdm_models.models.cdm_event_common_TradeState_schema import TradeState`.
- README: the documented `PYTHONPATH` pointed at the models directory rather than its `src` directory, so the documented setup did not make the models importable. It now matches the path printed by `cdm-lite use`.
- The README generated inside the compiled model package now shows the correct import path.
- The "version not found in cache" error pointed at `cdm-lite init --version`, a command that does not exist. It now points at `cdm-lite install <version>`.
- Pre-release CDM versions are no longer reported as stable. `-dev`, `-test`, `-rc`, `-alpha`, `-beta` and `-SNAPSHOT` are all treated as pre-releases, so `cdm-lite versions` and `cdm-lite install` never pick one as the latest stable.
- `status.json` files written by a newer `cdm-lite` are now read without error. Unknown fields are ignored on read and preserved on write, so upgrading and later downgrading no longer breaks the local cache.

### Changed

- `cdm-lite use`, `install <version>` and `remove` resolve versions from the local cache before consulting Maven Central, so installed versions can be managed without network access.
- Transient download failures (connection errors, HTTP 5xx) are retried with backoff; 4xx responses still fail immediately.
- Schema archives unpack into a temporary directory and are swapped into place only on success, so a failed or corrupt download never leaves partial files in the cache and never destroys previously downloaded schemas.
- Development status classifier changed from `4 - Beta` to `5 - Production/Stable`.

## [0.5.0b4] - 2026-10-22

### Added

- `cdm-lite --version` (alias `-V`) prints the installed version, e.g. `cdm-lite 0.5.0b4`, and exits. Implemented as an eager app-level callback so it short-circuits before any command runs, and degrades to `unknown` when package metadata is unavailable.

## [0.5.0b3] - 2026-10-22

### Changed

- Switched the HTTP client from `httpx` to `httpx2` (>=2.16.0), the actively maintained fork of `httpx` 0.28.1 under Pydantic stewardship. `httpx` had not seen a stable release since December 2024. `httpx2` is API-compatible apart from the package rename, so the only source change is `import httpx` -> `import httpx2`. Note that `httpx2.alias_httpx()` is deliberately not used: it globally aliases `import httpx` process-wide and is documented for applications, not libraries.
- TLS certificate verification now uses the operating system trust store via `truststore` instead of a bundled `certifi` CA bundle. This drops `certifi` from the dependency tree entirely.
- `idna` constraint raised from `>=3.16` to `>=3.18` to match the floor required by `httpx2`.

### Security

- The `certifi>=2026.10.19` constraint was removed as `certifi` is no longer part of the dependency tree. TLS trust now comes from the OS trust store via `truststore`, which still honours `SSL_CERT_FILE` and `SSL_CERT_DIR` for custom CA bundles.

## [0.5.0b2] - 2026-10-22

### Changed

- Build backend `uv_build` minimum version bumped from 0.12.5 to 0.13.0.
- Dependency upgrades across the board: `platformdirs` 4.9.6 → 4.13.5, `pydantic` 2.14.0 → 2.14.1, `typer` 0.25.1 → 0.27.3, `pytest` 9.0.3 → 9.1.1, `complexipy` 7.0.1 → 8.1.0, `ruff` 0.16.3 → 0.17.1, `ty` 0.0.72 → 0.0.90.
- Dev dependency minimums raised to match: `ruff>=0.17.1`, `ty>=0.0.90`.

### Security

- Dependency constraints tightened: `idna>=3.16`, `anyio>=4.15.1`, `certifi>=2026.10.19` (resolved `idna` 3.20, `anyio` 4.15.1, `certifi` 2026.10.19).
- Removed the now-redundant direct `idna` dependency in favour of `[tool.uv]` constraints.

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
