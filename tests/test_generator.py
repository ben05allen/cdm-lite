# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from unittest.mock import patch

import pytest

from cdm_lite.generator import (
    GenerateResult,
    generate_models,
    generate_package_metadata,
)
from datamodel_code_generator.format import Formatter
from datamodel_code_generator.enums import DataModelType, InputFileType


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def input_dir(tmp_path: Path) -> Path:
    d = tmp_path / "schema-clean"
    d.mkdir()
    return d


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "models"
    d.mkdir()
    return d


# ── GenerateResult ────────────────────────────────────────────────────────────


class TestGenerateResult:
    def test_success(self):
        result = GenerateResult(success=True, stdout="Generation successful.", stderr="")
        assert result.success is True

    def test_failure(self):
        result = GenerateResult(success=False, stdout="", stderr="Something went wrong")
        assert result.success is False

    def test_str_on_success(self):
        result = GenerateResult(success=True, stdout="Generation successful.", stderr="")
        assert "successfully" in str(result)

    def test_str_on_failure_includes_stderr(self):
        result = GenerateResult(success=False, stdout="", stderr="Bad argument")
        assert "Bad argument" in str(result)
        assert "failed" in str(result)


# ── generate_models ───────────────────────────────────────────────────────────


class TestGenerateModels:
    def test_returns_success_result(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.generate") as mock_generate:
            result = generate_models(input_dir, output_dir)

        assert result.success is True
        mock_generate.assert_called_once()

    def test_returns_failure_result_on_exception(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.generate") as mock_generate:
            mock_generate.side_effect = ValueError("Unknown argument")
            result = generate_models(input_dir, output_dir)

        assert result.success is False
        assert "Unknown argument" in result.stderr

    def test_creates_output_dir_if_missing(self, input_dir: Path, tmp_path: Path):
        output_dir = tmp_path / "does" / "not" / "exist"
        assert not output_dir.exists()

        with patch("cdm_lite.generator.generate"):
            generate_models(input_dir, output_dir)

        assert output_dir.exists()

    def test_passes_correct_config(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.generate") as mock_generate:
            generate_models(input_dir, output_dir)

        mock_generate.assert_called_once()
        kwargs = mock_generate.call_args.kwargs
        assert "input_" in kwargs
        assert kwargs["input_"] == input_dir

        config = kwargs["config"]
        assert config.output == output_dir / "src" / "cdm_models" / "models"
        assert config.input_file_type == InputFileType.JsonSchema
        assert config.output_model_type == DataModelType.PydanticV2BaseModel
        assert config.reuse_model is True
        assert config.use_standard_collections is True
        assert config.snake_case_field is True
        assert config.capitalise_enum_members is True
        assert Formatter.RUFF_FORMAT in config.formatters

    def test_resolves_inner_input_directory(self, input_dir: Path, output_dir: Path):
        # Create a single subdirectory 'jsonschema' inside input_dir
        inner_dir = input_dir / "jsonschema"
        inner_dir.mkdir()
        (inner_dir / "Schema.json").touch()

        with patch("cdm_lite.generator.generate") as mock_generate:
            generate_models(input_dir, output_dir)

        assert mock_generate.call_args.kwargs["input_"] == inner_dir

    def test_creates_init_files(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.generate"):
            generate_models(input_dir, output_dir)

        assert (output_dir / "src" / "cdm_models" / "__init__.py").exists()
        assert (output_dir / "src" / "cdm_models" / "models" / "__init__.py").exists()

    def test_custom_python_version(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.generate") as mock_generate:
            generate_models(input_dir, output_dir, python_version="3.12")

        config = mock_generate.call_args.kwargs["config"]
        assert config.target_python_version.value == "3.12"


# ── Generated Meta Data ──────────────────────────────────────────────────────────


class TestGeneratePackageMetadata:
    def test_creates_pyproject_toml(self, tmp_path: Path):
        generate_package_metadata(tmp_path, cdm_version="6.19.0")
        assert (tmp_path / "pyproject.toml").exists()

    def test_creates_readme(self, tmp_path: Path):
        generate_package_metadata(tmp_path, cdm_version="6.19.0")
        assert (tmp_path / "README.md").exists()

    def test_pyproject_contains_cdm_version(self, tmp_path: Path):
        generate_package_metadata(tmp_path, cdm_version="6.19.0")
        content = (tmp_path / "pyproject.toml").read_text()
        assert "6.19.0" in content

    def test_pyproject_contains_python_version(self, tmp_path: Path):
        generate_package_metadata(tmp_path, cdm_version="6.19.0", python_version="3.13")
        content = (tmp_path / "pyproject.toml").read_text()
        assert "3.13" in content

    def test_readme_contains_cdm_version(self, tmp_path: Path):
        generate_package_metadata(tmp_path, cdm_version="6.19.0")
        content = (tmp_path / "README.md").read_text()
        assert "6.19.0" in content

    def test_pyproject_is_valid_toml(self, tmp_path: Path):
        import tomllib

        generate_package_metadata(tmp_path, cdm_version="6.19.0")
        content = (tmp_path / "pyproject.toml").read_bytes()
        parsed = tomllib.loads(content.decode())
        assert parsed["project"]["name"] == "cdm-models"
        assert parsed["project"]["version"] == "6.19.0"


# ── Integration test ──────────────────────────────────────────────────────────


@pytest.mark.integration
def test_real_generation(tmp_path: Path):
    """Runs datamodel-codegen for real — run with: pytest -m integration"""
    import json

    input_dir = tmp_path / "schema-clean"
    input_dir.mkdir()
    output_dir = tmp_path / "models"

    # Write a minimal schema to generate from
    (input_dir / "CounterpartyRoleEnum.json").write_text(
        json.dumps(
            {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "type": "string",
                "title": "CounterpartyRoleEnum",
                "description": "Counterparty roles.",
                "enum": ["Party1", "Party2"],
            }
        )
    )

    result = generate_models(input_dir, output_dir)
    assert result.success, result.stderr
    generated = list(output_dir.rglob("*.py"))
    assert len(generated) > 0
