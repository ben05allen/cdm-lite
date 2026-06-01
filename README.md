# cdm-lite

[![CI](https://github.com/ben05allen/cdm-lite/actions/workflows/ci.yml/badge.svg)](https://github.com/ben05allen/cdm-lite/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

Python Pydantic models for the [FINOS Common Domain Model (CDM)](https://github.com/finos/common-domain-model).

`cdm-lite` provides a lightweight CLI to download, clean, and compile official FINOS CDM JSON
schemas into Pydantic v2 models. This enables strict validation, autocompletion, and robust
deserialization of CDM JSON payloads in Python codebases without heavy Java dependencies.

## Status

**Current Phase:** Beta

`cdm-lite` is currently in a beta development stage. While the core functionality is stable, we are actively refining the cleaning and generation logic based on community feedback.

**Feedback Welcome:** We gratefully encourage users to provide comments, recommendations, or report any issues found during usage. Your input
will help in reaching a stable 1.0 release.

## Scope & Limitations

**⚠️ Disclaimer:** `cdm-lite` is intended primarily as a lightweight **deserializer**. The generated
Python models are derived directly from the published JSON Schemas. While they provide close
structural validation, we cannot guarantee that the generated models perfectly match the
behavioral constraints of the full Common Domain Model.

Pydantic classes inherently cannot capture the full extent of the CDM's functionality,
such as complex cross-field cardinality checks, conditions, or rosetta-injected logic.
For robust **serialization** and comprehensive domain validation, we strongly recommend using the [official, full CDM project implementations](https://github.com/finos/common-domain-model) (e.g., the Java distribution).

## Installation

```bash
uv tool install cdm-lite
```

## Workflow

Download and compile the CDM models for your required schema version:

```bash
# List available FINOS CDM versions from Maven Central
cdm-lite versions

# Download schemas and compile Pydantic models locally
cdm-lite install 6.19.0

# Activate the version (updates a local symlink)
cdm-lite use 6.19.0
```

_Note: Models are compiled into a user-level cache directory (e.g., `~/.cache/cdm-lite/`). Run `cdm-lite status` to view your specific path._

## Project Integration

To use the compiled models in your application, point your environment to the active models directory.

**Using `uv` (`pyproject.toml`):**

```toml
[tool.uv.sources]
# Use the exact absolute path returned by `cdm-lite use`
cdm-models = { path = "/home/user/.cache/cdm-lite/current" }

[project]
dependencies = ["cdm-models"]
```

**Using PYTHONPATH:**

```bash
# Use the exact absolute path returned by `cdm-lite use`
export PYTHONPATH="/home/user/.cache/cdm-lite/current:$PYTHONPATH"
```

## Deserializing JSON

Once the models are available in your path, use standard Pydantic APIs to parse, validate, and interact with incoming JSON objects:

```python
from cdm-models.models.cdm_event_common_TradeState_schema import TradeState  # Exact import paths depend on the CDM schema

payload = '{"trade": {"tradeDate": {"value": "2023-10-25"}}}'

# Deserialize and strictly validate the JSON string
trade_state = TradeState.model_validate_json(payload)

# Access typed and autocompleted attributes
print(trade_state.trade.trade_date.value)
```

## Reference Commands

- `cdm-lite versions`: View available versions on Maven Central.
- `cdm-lite install <version>`: Fetch schemas and compile models.
- `cdm-lite use <version>`: Set the active version for the `current` symlink.
- `cdm-lite list`: Show locally compiled versions.
- `cdm-lite status`: Print active version and system cache location.
- `cdm-lite remove <version>`: Delete a specific version from the local cache.
- `cdm-lite clear`: Remove all local schemas and generated models.
