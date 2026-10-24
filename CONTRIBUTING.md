# Contributing to cdm-lite

Thanks for your interest in contributing. Comments, recommendations and bug reports are
welcomed via [issues](https://github.com/ben05allen/cdm-lite/issues).

## Development

This project uses [`uv`](https://docs.astral.sh/uv/) for everything:

```bash
uv sync                 # install dependencies (including the dev group)
uv run pytest           # unit tests
uv run pytest -m integration   # tests that hit external services
prek run --all-files    # ruff, ruff format, ty, complexipy (prek.toml)
```

CI runs the same checks on every push and pull request: linting via `prek`, a build smoke test,
the test matrix across Python 3.11–3.15 on Linux, Windows and macOS, and a coverage floor of 85%.

Any new feature or bug fix needs accompanying tests in `tests/`, and Python code must use
Python 3.12+ style type hints (`dict[K, V]`, `list[T]`, `T | None`).

## Releasing

Releases are published to PyPI automatically from a git tag, using
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC) — no API token is
stored in GitHub.

1. Bump the version and update every version reference in one command:

   ```bash
   uv run python scripts/bump_version.py 0.6.1 --note "Add a cdm-lite upgrade command."
   ```

   This updates `pyproject.toml` (version and development status classifier), the README status
   line and the CHANGELOG in a single commit.

2. Open a pull request. CI checks that the CHANGELOG documents the version in `pyproject.toml`.

3. Merge, then tag and push the tag:

   ```bash
   git tag v0.6.1
   git push origin v0.6.1
   ```

4. The `Release` workflow verifies the tag matches the project version, builds the sdist and
   wheel, and publishes them to PyPI (skipping files already present on the index).

**One-time PyPI setup:** on the [cdm-lite project page](https://pypi.org/manage/project/cdm-lite/settings/publishing),
add a GitHub trusted publisher with owner `ben05allen`, repository `cdm-lite`, workflow
`release.yml` and environment `pypi`. The `pypi` environment must therefore be referenced by the
release workflow; if you configure the publisher without an environment name, remove the
`environment:` block from `.github/workflows/release.yml`.