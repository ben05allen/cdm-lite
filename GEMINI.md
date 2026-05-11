# CDM-Lite

A lightweight Python implementation of the Common Domain Model (CDM) using Pydantic v2.

## Project Overview

`cdm-lite` provides a type-safe, Pydantic-based representation of CDM objects. It is designed to be efficient and easy to use for financial application development, specifically targeting the FINOS ecosystem.

- **Main Technologies:** Python 3.14+, Pydantic v2, Ruff.
- **Source of Models:** Models are generated from CDM JSON schemas using `datamodel-code-generator`.

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) for Python package and environment management.

### Installation

```bash
uv sync
```

### Running the Demo

The project includes a sample script that demonstrates creating CDM objects like parties and interest rate payouts.

```bash
uv run try
```

### Code Generation

Models are located in `src/cdm_models/`. To regenerate them from the schemas:

1. Ensure the schemas are present in `lib/cdm-schema/`.
2. Run the cleaning script to prepare schemas for generation:
   ```bash
   uv run python util/fix_cdm_enum_schemas.py
   ```
3. Run the codegen script:
   ```bash
   ./run_codegen.sh
   ```

## Project Structure

- `src/cdm_lite/`: Contains the core logic and entry points for the application.
- `src/cdm_models/`: Auto-generated Pydantic models. **Do not edit these files manually.**
- `lib/`: Contains CDM JSON schemas (ignored by git).
- `util/`: Maintenance scripts for schema processing.
- `run_codegen.sh`: Shell script orchestrating the Pydantic model generation.

## Development Conventions

- **Python Version:** Always use modern Python 3.12+ type hinting (e.g., `dict[K, V]`, `list[T]`, and `T | None`). This project specifically targets Python 3.14.
- **Linting & Formatting:** Use Ruff for all linting and formatting tasks.
  ```bash
  uvx ruff check --fix && uvx ruff format
  ```
- **CDM Models:** Never manually modify files in `src/cdm_models/`. If changes are needed, update the generation process or the source schemas.
- **FinTech Focus:** The project focuses on FINOS (Fintech Open Source Foundation) standards.
