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

import re
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from cdm_lite.cli import app
from cdm_lite.registry import CdmVersion
from cdm_lite.store import CdmStore


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*[mGKF]", "", text)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def temp_store(tmp_path: Path) -> CdmStore:
    """A real store pointing to a temporary directory."""
    store = CdmStore(cache_dir=tmp_path / "cdm-lite")
    store.init()
    return store


@pytest.mark.integration
def test_cli_lifecycle(runner: CliRunner, temp_store: CdmStore, tmp_path: Path):
    """
    Test the full CLI lifecycle: install -> use -> remove.
    We mock the registry and downloader to avoid network hits,
    but run the real CLI commands and verify the real filesystem.
    """
    version = CdmVersion("6.19.0")

    # 1. Mock registry to return our version
    # 2. Mock downloader to just create a dummy file
    # 3. Mock generator to just create a dummy package

    with (
        patch("cdm_lite.cli.store", temp_store),
        patch("cdm_lite.cli.registry") as mock_registry,
        patch("cdm_lite.cli.download_schemas"),
        patch("cdm_lite.cli.clean_schemas"),
        patch("cdm_lite.cli.generate_models") as mock_generate,
        patch("cdm_lite.cli.generate_package_metadata"),
    ):
        mock_registry.get.return_value = version
        mock_registry.latest_stable.return_value = version
        mock_registry.all_versions.return_value = [version]

        # Mocking generation result
        from unittest.mock import MagicMock

        mock_generate.return_value = MagicMock(success=True, __str__=lambda s: "Done.")

        # --- INSTALL ---
        result = runner.invoke(app, ["install", "6.19.0"])
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "installed successfully" in output
        assert temp_store.is_generated(version)
        assert (temp_store._version_dir(version) / "models").exists()

        # --- USE ---
        result = runner.invoke(app, ["use", "6.19.0"])
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Now using CDM 6.19.0" in output
        assert temp_store.current_version() == version
        assert temp_store.current_models_dir().exists()
        assert temp_store.current_models_dir().is_symlink()

        # --- STATUS ---
        result = runner.invoke(app, ["status"])
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "6.19.0" in output
        assert "Current version" in output

        # --- REMOVE ---
        # First try without force and say 'no'
        result = runner.invoke(app, ["remove", "6.19.0"], input="n\n")
        output = strip_ansi(result.output)
        assert "Aborted" in output
        assert temp_store.current_version() == version

        # Now remove with force
        result = runner.invoke(app, ["remove", "6.19.0", "--force"])
        output = strip_ansi(result.output)
        assert result.exit_code == 0
        assert "Removed CDM 6.19.0" in output

        # Verify cleanup
        assert not temp_store._version_dir(version).exists()
        assert temp_store.current_version() is None
        assert not temp_store.current_models_dir().exists()

        # --- LIST (should be empty) ---
        result = runner.invoke(app, ["list"])
        output = strip_ansi(result.output)
        assert "No versions installed yet" in output
