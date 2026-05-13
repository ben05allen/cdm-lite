import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

MIN_PYTHON_VERSION = 3.11


class GenerationError(Exception):
    pass


@dataclass
class GenerateResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0

    def __str__(self) -> str:
        if self.success:
            return "Model generation completed successfully."
        return f"Model generation failed (exit code {self.returncode}).\n{self.stderr}".strip()


def generate_models(
    input_dir: Path,
    output_dir: Path,
    python_version: str = f"{MIN_PYTHON_VERSION}",
) -> GenerateResult:
    """
    Run datamodel-codegen against the cleaned schema directory,
    writing Pydantic v2 models to output_dir.

    Raises GenerationError if the process cannot be started.
    """
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input",
        str(input_dir),
        "--input-file-type",
        "jsonschema",
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--output",
        str(output_dir),
        "--reuse-model",
        "--use-standard-collections",
        "--snake-case-field",
        "--capitalise-enum-members",
        "--formatter",
        "ruff-format",
        "--target-python-version",
        python_version,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as e:
        raise GenerationError(
            "datamodel-codegen not found. Is it installed? Try: uv add datamodel-code-generator"
        ) from e

    return GenerateResult(
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
