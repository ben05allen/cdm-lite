from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

import pytest

from cdm_lite.generator import GenerateResult, GenerationError, generate_models, MIN_PYTHON_VERSION


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


def make_completed_process(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> MagicMock:
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ── GenerateResult ────────────────────────────────────────────────────────────


class TestGenerateResult:
    def test_success_when_returncode_zero(self):
        result = GenerateResult(returncode=0, stdout="", stderr="")
        assert result.success is True

    def test_failure_when_nonzero_returncode(self):
        result = GenerateResult(returncode=1, stdout="", stderr="Something went wrong")
        assert result.success is False

    def test_str_on_success(self):
        result = GenerateResult(returncode=0, stdout="", stderr="")
        assert "successfully" in str(result)

    def test_str_on_failure_includes_stderr(self):
        result = GenerateResult(returncode=1, stdout="", stderr="Bad argument")
        assert "Bad argument" in str(result)
        assert "1" in str(result)


# ── generate_models ───────────────────────────────────────────────────────────


class TestGenerateModels:
    def test_returns_success_result(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.return_value = make_completed_process(returncode=0)
            result = generate_models(input_dir, output_dir)

        assert result.success is True

    def test_returns_failure_result_on_nonzero_exit(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.return_value = make_completed_process(returncode=1, stderr="Unknown argument")
            result = generate_models(input_dir, output_dir)

        assert result.success is False
        assert "Unknown argument" in result.stderr

    def test_creates_output_dir_if_missing(self, input_dir: Path, tmp_path: Path):
        output_dir = tmp_path / "does" / "not" / "exist"
        assert not output_dir.exists()

        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.return_value = make_completed_process()
            generate_models(input_dir, output_dir)

        assert output_dir.exists()

    def test_calls_correct_command(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.return_value = make_completed_process()
            generate_models(input_dir, output_dir)

        cmd = mock_run.call_args[0][0]
        assert "-m" in cmd
        assert "datamodel_code_generator" in cmd
        assert "--input" in cmd
        assert str(input_dir) in cmd
        assert "--output" in cmd
        assert str(output_dir) in cmd

    def test_passes_correct_flags(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.return_value = make_completed_process()
            generate_models(input_dir, output_dir)

        cmd = mock_run.call_args[0][0]
        assert "--reuse-model" in cmd
        assert "--snake-case-field" in cmd
        assert "--capitalise-enum-members" in cmd
        assert "--use-standard-collections" in cmd

    def test_default_python_version(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.return_value = make_completed_process()
            generate_models(input_dir, output_dir)

        cmd = mock_run.call_args[0][0]
        assert "--target-python-version" in cmd
        idx = cmd.index("--target-python-version")
        assert cmd[idx + 1] == f"{MIN_PYTHON_VERSION}"

    def test_custom_python_version(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.return_value = make_completed_process()
            generate_models(input_dir, output_dir, python_version="3.14")

        cmd = mock_run.call_args[0][0]
        idx = cmd.index("--target-python-version")
        assert cmd[idx + 1] == "3.14"

    def test_raises_generation_error_if_not_found(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("No such file")
            with pytest.raises(GenerationError, match="datamodel-codegen not found"):
                generate_models(input_dir, output_dir)

    def test_captures_stdout_and_stderr(self, input_dir: Path, output_dir: Path):
        with patch("cdm_lite.generator.subprocess.run") as mock_run:
            mock_run.return_value = make_completed_process(
                stdout="some output",
                stderr="some warning",
            )
            result = generate_models(input_dir, output_dir)

        assert result.stdout == "some output"
        assert result.stderr == "some warning"


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
