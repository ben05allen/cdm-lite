# cdm-lite

Python Pydantic models for the [FINOS Common Domain Model (CDM)](https://github.com/finos/common-domain-model).

`cdm-lite` provides a lightweight CLI to download, clean, and compile official FINOS CDM JSON schemas into Pydantic v2 models. This enables strict validation, autocompletion, and robust deserialization of CDM JSON payloads in Python codebases without heavy Java dependencies.

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
from TradeState import TradeState  # Exact import paths depend on the CDM schema

payload = '{"trade": {"tradeDate": {"date": "2023-10-25"}}}'

# Deserialize and strictly validate the JSON string
trade_state = TradeState.model_validate_json(payload)

# Access typed and autocompleted attributes
print(trade_state.trade.tradeDate.date)
```

## Reference Commands

- `cdm-lite versions`: View available versions on Maven Central.
- `cdm-lite install -v <version>`: Fetch schemas and compile models.
- `cdm-lite use -v <version>`: Set the active version for the `current` symlink.
- `cdm-lite list`: Show locally compiled versions.
- `cdm-lite status`: Print active version and system cache location.
- `cdm-lite clear`: Remove all local schemas and generated models.
