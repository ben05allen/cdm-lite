def generate_pyproject(cdm_version: str, python_version: str = "3.11"):
    template = r"""
[project]
name = "cdm-models"
version = "{cdm_version}"
description = "Pydantic v2 models generated from the FINOS CDM JSON Schema v{cdm_version}."
readme = "README.md"
requires-python = ">={python_version}"
license = {{ text = "Apache-2.0" }}
dependencies = [
    "pydantic>=2.0",
]

[project.urls]
Homepage = "https://github.com/finos/common-domain-model"
        """

    return template.format(cdm_version=cdm_version, python_version=python_version)
