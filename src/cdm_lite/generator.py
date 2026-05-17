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

from dataclasses import dataclass
from pathlib import Path

from datamodel_code_generator import generate, GenerateConfig
from datamodel_code_generator.enums import DataModelType, InputFileType
from datamodel_code_generator.format import Formatter, PythonVersion

from cdm_lite.templates.pyproject_toml import generate_pyproject
from cdm_lite.templates.readme_md import generate_readme


MIN_PYTHON_VERSION = 3.11


def generate_package_metadata(
    models_dir: Path,
    cdm_version: str,
    python_version: str = f"{MIN_PYTHON_VERSION}",
) -> None:
    """
    Write pyproject.toml and README.md into the models directory
    so it can be used as a standalone installable package.
    """
    from datetime import datetime, timezone

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    pyproject = generate_pyproject(
        cdm_version=cdm_version,
        python_version=python_version,
    )
    readme = generate_readme(
        cdm_version=cdm_version,
        generated_at=generated_at,
    )

    (models_dir / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    (models_dir / "README.md").write_text(readme, encoding="utf-8")


class GenerationError(Exception):
    pass


@dataclass
class GenerateResult:
    success: bool
    stdout: str
    stderr: str

    def __str__(self) -> str:
        if self.success:
            return "Model generation completed successfully."
        return f"Model generation failed:\n{self.stderr}".strip()


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

    try:
        config = GenerateConfig(
            input_file_type=InputFileType.JsonSchema,
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=PythonVersion(python_version),
            reuse_model=True,
            use_standard_collections=True,
            snake_case_field=True,
            capitalise_enum_members=True,
            formatters=[Formatter.RUFF_FORMAT],
            output=output_dir,
        )

        # Datamodel-codegen's generate function handles reading input directory
        # and writing to the output directory specified in the config.
        generate(input_=input_dir, config=config)

    except Exception as e:
        return GenerateResult(
            success=False,
            stdout="",
            stderr=str(e),
        )

    return GenerateResult(
        success=True,
        stdout="Generation successful.",
        stderr="",
    )
