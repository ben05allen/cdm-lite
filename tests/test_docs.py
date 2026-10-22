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

"""Regression tests for the documentation.

The README and the generated package README are the only places users learn
how to import the generated models and how to put them on ``PYTHONPATH``.
Both have shipped broken examples before, so they are pinned here.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from cdm_lite.templates.readme_md import generate_readme

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"


@pytest.fixture(scope="module")
def readme_text() -> str:
    return README.read_text(encoding="utf-8")


class TestReadme:
    def test_readme_exists(self):
        assert README.is_file()

    def test_import_example_is_valid_python(self, readme_text: str):
        """``cdm-models`` is a distribution name, not an importable module."""
        assert "from cdm_models.models." in readme_text
        assert "from cdm-models" not in readme_text

    def test_pythonpath_points_at_the_src_directory(self, readme_text: str):
        """The generated package uses a ``src`` layout under ``current/``."""
        export_lines = [
            line for line in readme_text.splitlines() if line.startswith("export PYTHONPATH=")
        ]
        assert export_lines, "README no longer documents the PYTHONPATH setup"
        for line in export_lines:
            assert "/cdm-lite/current/src:" in line


class TestVersionConsistency:
    def test_changelog_documents_the_current_version(self):
        """The release workflow refuses to publish an undocumented version."""
        version = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
        assert f"## [{version}]" in CHANGELOG.read_text(encoding="utf-8")

    def test_readme_status_matches_the_current_version(self):
        version = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
        assert f"(v{version})" in README.read_text(encoding="utf-8")


class TestGeneratedReadme:
    def test_import_example_uses_the_package_prefix(self):
        text = generate_readme(cdm_version="6.19.0", generated_at="2026-01-01")
        assert "from cdm_models.models.cdm_event_common_TradeState_schema import TradeState" in text

    def test_import_example_is_valid_python(self):
        text = generate_readme(cdm_version="6.19.0")
        assert "from cdm_event_common_TradeState_schema" not in text
