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

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
        """

    return template.format(cdm_version=cdm_version, python_version=python_version)
