from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from cdm_lite.cli import app
from cdm_lite.registry import CdmVersion
from cdm_lite.store import CdmStore, VersionStatus


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_store(tmp_path: Path) -> CdmStore:
    store = CdmStore(cache_dir=tmp_path / "cdm-lite")
    store.init()
    return store


@pytest.fixture
def version() -> CdmVersion:
    return CdmVersion("6.19.0")


@pytest.fixture
def other_version() -> CdmVersion:
    return CdmVersion("6.0.0")


SAMPLE_VERSIONS = [
    CdmVersion("6.0.0"),
    CdmVersion("6.1.0"),
    CdmVersion("6.19.0"),
    CdmVersion("7.0.0-dev.1"),
]


def make_full_status(version: CdmVersion) -> VersionStatus:
    """A fully installed version status."""
    return VersionStatus(
        version=version.version,
        downloaded=True,
        cleaned=True,
        generated=True,
        downloaded_at="2026-01-01T00:00:00+00:00",
        cleaned_at="2026-01-01T00:00:01+00:00",
        generated_at="2026-01-01T00:00:02+00:00",
        cdm_lite_version="0.1.0",
    )


# ── versions command ──────────────────────────────────────────────────────────


class TestVersionsCommand:
    def test_lists_stable_versions(self, runner: CliRunner):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
        ):
            mock_registry.all_versions.return_value = [CdmVersion("6.0.0"), CdmVersion("6.19.0")]
            mock_registry.latest_stable.return_value = CdmVersion("6.19.0")
            mock_store.cached_versions.return_value = []
            mock_store.current_version.return_value = None

            result = runner.invoke(app, ["versions"])

        assert result.exit_code == 0
        assert "6.0.0" in result.output
        assert "6.19.0" in result.output

    def test_shows_installed_marker(self, runner: CliRunner):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
        ):
            mock_registry.all_versions.return_value = [CdmVersion("6.19.0")]
            mock_registry.latest_stable.return_value = CdmVersion("6.19.0")
            mock_store.cached_versions.return_value = [CdmVersion("6.19.0")]
            mock_store.current_version.return_value = CdmVersion("6.19.0")

            result = runner.invoke(app, ["versions"])

        assert result.exit_code == 0
        assert "installed" in result.output

    def test_excludes_dev_by_default(self, runner: CliRunner):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
        ):
            mock_registry.all_versions.return_value = [CdmVersion("6.19.0")]
            mock_registry.latest_stable.return_value = CdmVersion("6.19.0")
            mock_store.cached_versions.return_value = []
            mock_store.current_version.return_value = None

            runner.invoke(app, ["versions"])

        mock_registry.all_versions.assert_called_once_with(include_dev=False)

    def test_includes_dev_with_flag(self, runner: CliRunner):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
        ):
            mock_registry.all_versions.return_value = SAMPLE_VERSIONS
            mock_registry.latest_stable.return_value = CdmVersion("6.19.0")
            mock_store.cached_versions.return_value = []
            mock_store.current_version.return_value = None

            runner.invoke(app, ["versions", "--dev"])

        mock_registry.all_versions.assert_called_once_with(include_dev=True)

    def test_shows_current_marker(self, runner: CliRunner):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
        ):
            mock_registry.all_versions.return_value = [CdmVersion("6.19.0")]
            mock_registry.latest_stable.return_value = CdmVersion("6.19.0")
            mock_store.cached_versions.return_value = [CdmVersion("6.19.0")]
            mock_store.current_version.return_value = CdmVersion("6.19.0")

            result = runner.invoke(app, ["versions"])

        assert "current" in result.output

    def test_aborts_on_registry_error(self, runner: CliRunner):
        with patch("cdm_lite.cli.registry") as mock_registry:
            mock_registry.all_versions.side_effect = Exception("Network error")
            result = runner.invoke(app, ["versions"])

        assert result.exit_code == 1
        assert "Error" in result.output


# ── list command ──────────────────────────────────────────────────────────────


class TestListCommand:
    def test_shows_message_when_nothing_installed(self, runner: CliRunner):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.cached_versions.return_value = []
            mock_store.current_version.return_value = None

            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "No versions installed" in result.output

    def test_lists_installed_versions(self, runner: CliRunner, version: CdmVersion):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.cached_versions.return_value = [version]
            mock_store.current_version.return_value = version
            mock_store.status.return_value = make_full_status(version)
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        assert "6.19.0" in result.output

    def test_shows_step_status(self, runner: CliRunner, version: CdmVersion):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.cached_versions.return_value = [version]
            mock_store.current_version.return_value = version
            mock_store.status.return_value = make_full_status(version)
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["list"])

        assert result.exit_code == 0
        # All three steps should show as complete
        assert result.output.count("✔") >= 3

    def test_shows_current_path_when_version_active(self, runner: CliRunner, version: CdmVersion):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.cached_versions.return_value = [version]
            mock_store.current_version.return_value = version
            mock_store.status.return_value = make_full_status(version)
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["list"])

        assert "/home/user/.cache/cdm-lite/current" in result.output


# ── install command ───────────────────────────────────────────────────────────


class TestInstallCommand:
    def test_full_install_success(self, runner: CliRunner, version: CdmVersion):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
            patch("cdm_lite.cli.download_schemas"),
            patch("cdm_lite.cli.clean_schemas") as mock_clean,
            patch("cdm_lite.cli.generate_models") as mock_generate,
            patch("cdm_lite.cli.generate_package_metadata"),
        ):
            mock_registry.get.return_value = version
            mock_registry.latest_stable.return_value = version
            mock_store.status.return_value = VersionStatus(version=version.version)
            mock_store.schema_raw_dir.return_value = Path("/tmp/raw")
            mock_store.schema_clean_dir.return_value = Path("/tmp/clean")
            mock_store.models_dir.return_value = Path("/tmp/models")
            mock_clean.return_value = MagicMock(__str__=lambda s: "Cleaned.")
            mock_generate.return_value = MagicMock(success=True, __str__=lambda s: "Done.")

            result = runner.invoke(app, ["install", "--version", "6.19.0"])

        assert result.exit_code == 0
        assert "successfully" in result.output

    def test_uses_latest_stable_if_no_version_specified(
        self, runner: CliRunner, version: CdmVersion
    ):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
            patch("cdm_lite.cli.download_schemas"),
            patch("cdm_lite.cli.clean_schemas") as mock_clean,
            patch("cdm_lite.cli.generate_models") as mock_generate,
        ):
            mock_registry.get.return_value = version
            mock_registry.latest_stable.return_value = version
            mock_store.status.return_value = VersionStatus(version=version.version)
            mock_store.schema_raw_dir.return_value = Path("/tmp/raw")
            mock_store.schema_clean_dir.return_value = Path("/tmp/clean")
            mock_store.models_dir.return_value = Path("/tmp/models")
            mock_clean.return_value = MagicMock(__str__=lambda s: "Cleaned.")
            mock_generate.return_value = MagicMock(success=True, __str__=lambda s: "Done.")

            runner.invoke(app, ["install"])

        mock_registry.latest_stable.assert_called_once()

    def test_skips_download_if_already_done(self, runner: CliRunner, version: CdmVersion):
        status = VersionStatus(
            version=version.version, downloaded=True, cleaned=False, generated=False
        )
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
            patch("cdm_lite.cli.download_schemas") as mock_download,
            patch("cdm_lite.cli.clean_schemas") as mock_clean,
            patch("cdm_lite.cli.generate_models") as mock_generate,
            patch("cdm_lite.cli.generate_package_metadata"),
        ):
            mock_registry.get.return_value = version
            mock_store.status.return_value = status
            mock_store.schema_raw_dir.return_value = Path("/tmp/raw")
            mock_store.schema_clean_dir.return_value = Path("/tmp/clean")
            mock_store.models_dir.return_value = Path("/tmp/models")
            mock_clean.return_value = MagicMock(__str__=lambda s: "Cleaned.")
            mock_generate.return_value = MagicMock(success=True, __str__=lambda s: "Done.")

            result = runner.invoke(app, ["install", "--version", "6.19.0"])

        mock_download.assert_not_called()
        assert result.exit_code == 0

    def test_skips_all_steps_if_fully_installed(self, runner: CliRunner, version: CdmVersion):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
            patch("cdm_lite.cli.download_schemas") as mock_download,
            patch("cdm_lite.cli.clean_schemas") as mock_clean,
            patch("cdm_lite.cli.generate_models") as mock_generate,
        ):
            mock_registry.get.return_value = version
            mock_store.status.return_value = make_full_status(version)
            mock_store.schema_raw_dir.return_value = Path("/tmp/raw")
            mock_store.schema_clean_dir.return_value = Path("/tmp/clean")
            mock_store.models_dir.return_value = Path("/tmp/models")

            result = runner.invoke(app, ["install", "--version", "6.19.0"])

        mock_download.assert_not_called()
        mock_clean.assert_not_called()
        mock_generate.assert_not_called()
        assert result.exit_code == 0

    def test_aborts_on_download_error(self, runner: CliRunner, version: CdmVersion):
        from cdm_lite.downloader import DownloadError

        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
            patch("cdm_lite.cli.download_schemas") as mock_download,
            patch("cdm_lite.cli.clean_schemas"),
            patch("cdm_lite.cli.generate_models"),
        ):
            mock_registry.get.return_value = version
            mock_store.status.return_value = VersionStatus(version=version.version)
            mock_store.schema_raw_dir.return_value = Path("/tmp/raw")
            mock_download.side_effect = DownloadError("Timeout")

            result = runner.invoke(app, ["install", "--version", "6.19.0"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_aborts_on_generation_failure(self, runner: CliRunner, version: CdmVersion):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
            patch("cdm_lite.cli.download_schemas"),
            patch("cdm_lite.cli.clean_schemas") as mock_clean,
            patch("cdm_lite.cli.generate_models") as mock_generate,
        ):
            mock_registry.get.return_value = version
            mock_store.status.return_value = VersionStatus(version=version.version)
            mock_store.schema_raw_dir.return_value = Path("/tmp/raw")
            mock_store.schema_clean_dir.return_value = Path("/tmp/clean")
            mock_store.models_dir.return_value = Path("/tmp/models")
            mock_clean.return_value = MagicMock(__str__=lambda s: "Cleaned.")
            mock_generate.return_value = MagicMock(success=False, stderr="Unknown flag")

            result = runner.invoke(app, ["install", "--version", "6.19.0"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_custom_python_version(self, runner: CliRunner, version: CdmVersion):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
            patch("cdm_lite.cli.download_schemas"),
            patch("cdm_lite.cli.clean_schemas") as mock_clean,
            patch("cdm_lite.cli.generate_models") as mock_generate,
        ):
            mock_registry.get.return_value = version
            mock_store.status.return_value = VersionStatus(version=version.version)
            mock_store.schema_raw_dir.return_value = Path("/tmp/raw")
            mock_store.schema_clean_dir.return_value = Path("/tmp/clean")
            mock_store.models_dir.return_value = Path("/tmp/models")
            mock_clean.return_value = MagicMock(__str__=lambda s: "Cleaned.")
            mock_generate.return_value = MagicMock(success=True, __str__=lambda s: "Done.")

            runner.invoke(app, ["install", "--version", "6.19.0", "--python", "3.13"])

        mock_generate.assert_called_once_with(
            Path("/tmp/clean"),
            Path("/tmp/models"),
            python_version="3.13",
        )


# ── use command ───────────────────────────────────────────────────────────────


class TestUseCommand:
    def test_activates_installed_version(self, runner: CliRunner, version: CdmVersion):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
        ):
            mock_registry.get.return_value = version
            mock_store.is_generated.return_value = True
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["use", "--version", "6.19.0"])

        assert result.exit_code == 0
        assert "6.19.0" in result.output
        mock_store.set_current_version.assert_called_once_with(version)
        mock_store.update_current_symlink.assert_called_once_with(version)

    def test_shows_models_path(self, runner: CliRunner, version: CdmVersion):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
        ):
            mock_registry.get.return_value = version
            mock_store.is_generated.return_value = True
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["use", "--version", "6.19.0"])

        assert "/home/user/.cache/cdm-lite/current" in result.output

    def test_aborts_if_not_installed(self, runner: CliRunner, version: CdmVersion):
        with (
            patch("cdm_lite.cli.registry") as mock_registry,
            patch("cdm_lite.cli.store") as mock_store,
        ):
            mock_registry.get.return_value = version
            mock_store.is_generated.return_value = False

            result = runner.invoke(app, ["use", "--version", "6.19.0"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_aborts_on_unknown_version(self, runner: CliRunner):
        with patch("cdm_lite.cli.registry") as mock_registry:
            mock_registry.get.side_effect = ValueError("Version not found")

            result = runner.invoke(app, ["use", "--version", "99.0.0"])

        assert result.exit_code == 1
        assert "Error" in result.output


# ── status command ────────────────────────────────────────────────────────────


class TestStatusCommand:
    def test_shows_status_of_current_version(self, runner: CliRunner, version: CdmVersion):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.current_version.return_value = version
            mock_store.status.return_value = make_full_status(version)
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "6.19.0" in result.output

    def test_shows_all_steps_complete(self, runner: CliRunner, version: CdmVersion):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.current_version.return_value = version
            mock_store.status.return_value = make_full_status(version)
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["status"])

        assert result.output.count("✔") >= 3

    def test_shows_models_path(self, runner: CliRunner, version: CdmVersion):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.current_version.return_value = version
            mock_store.status.return_value = make_full_status(version)
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["status"])

        assert "/home/user/.cache/cdm-lite/current" in result.output

    def test_shows_message_when_no_current_version(self, runner: CliRunner):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.current_version.return_value = None

            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0
        assert "No active" in result.output

    def test_shows_generated_at_timestamp(self, runner: CliRunner, version: CdmVersion):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.current_version.return_value = version
            mock_store.status.return_value = make_full_status(version)
            mock_store.current_models_dir.return_value = Path("/home/user/.cache/cdm-lite/current")

            result = runner.invoke(app, ["status"])

        assert "2026-01-01" in result.output


# ── clear command ─────────────────────────────────────────────────────────────


class TestClearCommand:
    def test_prompts_for_confirmation(self, runner: CliRunner, tmp_path: Path):
        cache_dir = tmp_path / "cdm-lite"
        cache_dir.mkdir()

        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.cache_dir = cache_dir
            mock_store.cached_versions.return_value = [CdmVersion("6.19.0")]

            # Respond "n" to the confirmation prompt
            result = runner.invoke(app, ["clear"], input="n\n")

        assert result.exit_code == 0
        assert "Aborted" in result.output
        # Directory should still exist since we said no
        assert cache_dir.exists()

    def test_clears_cache_on_confirmation(self, runner: CliRunner, tmp_path: Path):
        cache_dir = tmp_path / "cdm-lite"
        cache_dir.mkdir()
        (cache_dir / "config.json").write_text("{}")

        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.cache_dir = cache_dir
            mock_store.cached_versions.return_value = [CdmVersion("6.19.0")]

            result = runner.invoke(app, ["clear"], input="y\n")

        assert result.exit_code == 0
        assert not cache_dir.exists()
        assert "cleared" in result.output

    def test_force_flag_skips_prompt(self, runner: CliRunner, tmp_path: Path):
        cache_dir = tmp_path / "cdm-lite"
        cache_dir.mkdir()

        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.cache_dir = cache_dir
            mock_store.cached_versions.return_value = []

            result = runner.invoke(app, ["clear", "--force"])

        assert result.exit_code == 0
        assert "cleared" in result.output

    def test_handles_empty_cache_gracefully(self, runner: CliRunner, tmp_path: Path):
        with patch("cdm_lite.cli.store") as mock_store:
            mock_store.cache_dir = tmp_path / "does-not-exist"

            result = runner.invoke(app, ["clear"])

        assert result.exit_code == 0
        assert "already empty" in result.output
