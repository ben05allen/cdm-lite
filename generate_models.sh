#!/usr/bin/env bash
set -euo pipefail

INPUT_DIR="./lib/cdm-schema-clean/"
OUTPUT_DIR="./src/cdm_models"

# clean output folder
rm -rf "{OUTPUT_DIR}"
mkdir -p "{OUTPUT_DIR}"

# run code gen
# (needs uv and dev deps installed)
uv run datamodel-codegen \
  --input "{INPUT_DIR}" \
  --input-file-type jsonschema \
  --output-model-type pydantic_v2.BaseModel \
  --output "{OUTPUT_DIR}" \
  --reuse-model \
  --use-standard-collections \
  --snake-case-field \
  --capitalise-enum-members \
  --formatter ruff-format \
  --target-python-version 3.14
