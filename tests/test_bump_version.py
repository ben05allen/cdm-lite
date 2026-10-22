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

"""Tests for the version bump helper (scripts/bump_version.py)."""

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bump_version.py"


def _load_module():
    """Import the helper script, which lives outside the package."""
    spec = importlib.util.spec_from_file_location("bump_version", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["bump_version"] = module
    spec.loader.exec_module(module)
    return module


bump_version = _load_module()


class TestClassifier:
    @pytest.mark.parametrize("version", ["0.6.0", "1.0.0", "2.1.3"])
    def test_stable_versions_use_the_stable_classifier(self, version: str):
        assert bump_version.classifier_for(version) == bump_version.STABLE_CLASSIFIER

    @pytest.mark.parametrize("version", ["0.7.0b1", "1.0.0rc1", "1.0.0a2", "1.0.0.dev1"])
    def test_prereleases_use_the_beta_classifier(self, version: str):
        assert bump_version.classifier_for(version) == bump_version.BETA_CLASSIFIER


class TestUpdatePyproject:
    def test_updates_version_and_classifier(self):
        text = 'version = "0.5.0b4"\nclassifiers = [\n  "Development Status :: 4 - Beta",\n]\n'
        result = bump_version.update_pyproject(text, "0.6.0")
        assert 'version = "0.6.0"' in result
        assert bump_version.STABLE_CLASSIFIER in result

    def test_downgrades_classifier_for_prereleases(self):
        text = 'version = "0.6.0"\nclassifiers = [\n  "Development Status :: 5 - Production/Stable",\n]\n'
        result = bump_version.update_pyproject(text, "0.7.0b1")
        assert bump_version.BETA_CLASSIFIER in result

    def test_raises_when_version_is_missing(self):
        with pytest.raises(bump_version.BumpError):
            bump_version.update_pyproject('name = "cdm-lite"\n', "1.0.0")


class TestUpdateReadme:
    def test_updates_the_status_line(self):
        text = "**Current Phase:** Stable (v0.6.0)\n"
        result = bump_version.update_readme(text, "0.6.1")
        assert "**Current Phase:** Stable (v0.6.1)" in result

    def test_marks_prereleases_as_beta(self):
        text = "**Current Phase:** Stable (v0.6.0)\n"
        result = bump_version.update_readme(text, "0.7.0b1")
        assert "**Current Phase:** Beta (v0.7.0b1)" in result

    def test_raises_when_status_line_is_missing(self):
        with pytest.raises(bump_version.BumpError):
            bump_version.update_readme("# cdm-lite\n", "1.0.0")


class TestUpdateChangelog:
    def test_inserts_a_new_section(self):
        text = "## [0.6.0] - 2026-10-22\n\n### Added\n\n- Old entry.\n"
        result = bump_version.update_changelog(text, "0.6.1", "2026-10-23", "Something new.")
        assert result.startswith("## [0.6.1] - 2026-10-23")
        assert "- Something new." in result
        # The previous section must survive, below the new one.
        assert result.index("## [0.6.1]") < result.index("## [0.6.0]")

    def test_refuses_to_duplicate_a_version(self):
        text = "## [0.6.0] - 2026-10-22\n"
        with pytest.raises(bump_version.BumpError):
            bump_version.update_changelog(text, "0.6.0", "2026-10-23", "note")

    def test_raises_when_no_sections_exist(self):
        with pytest.raises(bump_version.BumpError):
            bump_version.update_changelog("# Changelog\n", "1.0.0", "2026-10-23", "note")


class TestUnreleasedHandling:
    UNRELEASED = (
        "## [Unreleased]\n\n"
        "### Added\n\n"
        "- Existing entry.\n\n"
        "## [0.6.0] - 2026-10-22\n\n"
        "### Added\n\n"
        "- Old entry.\n"
    )

    def test_keeps_unreleased_above_the_new_release(self):
        result = bump_version.update_changelog(self.UNRELEASED, "0.7.0", "2026-10-24", "New thing.")

        assert result.startswith("## [Unreleased]")
        assert result.index("## [0.7.0]") > result.index("## [Unreleased]")
        assert result.index("## [0.7.0]") < result.index("## [0.6.0]")
        assert "## [0.6.0] - 2026-10-22" in result

    def test_moves_unreleased_entries_into_the_release(self):
        result = bump_version.update_changelog(self.UNRELEASED, "0.7.0", "2026-10-24", "New thing.")

        released = result[result.index("## [0.7.0]") : result.index("## [0.6.0]")]
        assert "- Existing entry." in released
        # The note is the first bullet of the released Added section
        assert released.index("- New thing.") < released.index("- Existing entry.")

    def test_leaves_an_empty_unreleased_section(self):
        result = bump_version.update_changelog(self.UNRELEASED, "0.7.0", "2026-10-24", "New thing.")

        unreleased_block = result[result.index("## [Unreleased]") : result.index("## [0.7.0]")]
        assert "- Existing entry." not in unreleased_block

    def test_creates_an_added_section_when_only_other_sections_exist(self):
        text = "## [Unreleased]\n\n### Changed\n\n- A change.\n\n## [0.6.0] - 2026-10-22\n"
        result = bump_version.update_changelog(text, "0.7.0", "2026-10-24", "New thing.")

        released = result[result.index("## [0.7.0]") : result.index("## [0.6.0]")]
        assert "### Added" in released
        assert "- New thing." in released
        assert "### Changed" in released
        assert "- A change." in released

    def test_empty_unreleased_still_produces_a_release_section(self):
        text = "## [Unreleased]\n\n## [0.6.0] - 2026-10-22\n\n### Added\n\n- Old.\n"
        result = bump_version.update_changelog(text, "0.7.0", "2026-10-24", "New thing.")

        released = result[result.index("## [0.7.0]") : result.index("## [0.6.0]")]
        assert "### Added" in released
        assert "- New thing." in released


class TestBump:
    def test_rejects_invalid_versions(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(bump_version, "_read", lambda path: 'version = "0.6.0"\n')
        with pytest.raises(bump_version.BumpError):
            bump_version.bump("not-a-version", dry_run=True)

    def test_rejects_bumping_to_the_current_version(self):
        current = bump_version.read_project_version(
            (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
        )
        with pytest.raises(bump_version.BumpError):
            bump_version.bump(current, dry_run=True)

    def test_dry_run_does_not_touch_the_files(self):
        root = Path(__file__).resolve().parents[1]
        before = {
            path: path.read_text(encoding="utf-8")
            for path in (root / "pyproject.toml", root / "README.md", root / "CHANGELOG.md")
        }
        bump_version.bump("99.0.0", note="Test note.", date="2026-10-23", dry_run=True)
        for path, text in before.items():
            assert path.read_text(encoding="utf-8") == text
