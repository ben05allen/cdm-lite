# Project: CDM Lite

`cdm-lite` is a CLI tool designed to manage [FINOS CDM (Common Domain Model)](https://github.com/finos/common-domain-model) Pydantic model versions. It automates the process of fetching JSON schemas from Maven Central, cleaning them to ensure compatibility, and generating Pydantic v2 models.

## Project Overview

-   **Purpose:** Provide a lightweight way to consume CDM models in Python without manual generation or dependency on large Java artifacts.
-   **Architecture:**
    -   `cli.py`: Typer-based CLI interface.
    -   `registry.py`: Version discovery via Maven Central metadata.
    -   `downloader.py`: Asynchronous-capable downloads using `httpx`.
    -   `cleaner.py`: Surgical fixes for JSON schemas (illegal control characters, `oneOf` stripping for enums) to optimize `datamodel-codegen` output.
    -   `generator.py`: Wrapper for `datamodel-code-generator`.
    -   `store.py`: Local cache management using `platformdirs`.
-   **Main Technologies:** Python 3.12+, Pydantic v2, Typer, Rich, HTTPX, `datamodel-code-generator`.

## Building and Running

The project uses `uv` for dependency management and execution.

-   **Install dependencies:** `uv sync`
-   **Run CLI (Development):** `uv run cdm-lite --help`
-   **Available Commands:**
    -   `cdm-lite versions`: List available CDM versions on Maven Central.
    -   `cdm-lite list`: List locally installed/generated versions.
    -   `cdm-lite install --version <version>`: Download, clean, and generate models.
    -   `cdm-lite use --version <version>`: Set the active CDM version (updates symlinks).
    -   `cdm-lite status`: Show currently active version and cache location.
    -   `cdm-lite clear`: Remove all cached versions and models.

## Development Conventions

-   **Type Hinting:** Use modern Python 3.12+ type hinting (e.g., `dict[K, V]`, `list[T]`, and `T | None`). Avoid `Dict`, `List`, and `Optional` from the `typing` module.
-   **Formatting & Linting:** Adhere to `ruff` standards.
    -   Command: `uvx ruff check --fix && uvx ruff format`
-   **Testing:**
    -   Run unit tests: `uv run pytest`
    -   Run integration tests (requires network): `uv run pytest -m integration`
    -   Test against multiple Python versions: `./check_versions.sh` (requires 3.11-3.14 to be available).
-   **Generated Models:** Models are generated into a user-specific cache directory (managed by `platformdirs`). The `cdm-lite use` command manages a `current` symlink to make it easy to point `PYTHONPATH` or `uv` sources at the active models.
-   **Schema Cleaning:** The `cleaner.py` module is critical. It handles edge cases in FINOS schemas that otherwise cause `datamodel-codegen` to produce suboptimal or broken Pydantic code (e.g., duplicate enum classes).

## Architecture Details

-   **Registry:** Fetches `maven-metadata.xml` to find stable and development releases.
-   **Cleaning Logic:**
    -   Fixes literal tabs/newlines inside JSON string values.
    -   Strips `oneOf` from string enums to prevent `datamodel-codegen` from creating separate wrapper classes for each enum member.
-   **Storage:** Defaults to `~/.cache/cdm-lite` (on Linux) or platform equivalent.
