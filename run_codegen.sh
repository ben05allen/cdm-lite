

uv run datamodel-codegen \
  --input ./lib/cdm-schema-clean/ \
  --input-file-type jsonschema \
  --output-model-type pydantic_v2.BaseModel \
  --output ./src/cdm_models/ \
  --reuse-model \
  --use-standard-collections \
  --snake-case-field \
  --formatter ruff-format \
  --target-python-version 3.14
