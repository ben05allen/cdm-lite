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

import json
from pathlib import Path

import pytest

from cdm_lite.registry import CdmVersion
from cdm_lite.store import CdmStore, Config, VersionStatus


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def store(tmp_path: Path) -> CdmStore:
    """A CdmStore backed by a temporary directory."""
    return CdmStore(cache_dir=tmp_path / "cdm-lite")


@pytest.fixture
def version() -> CdmVersion:
    return CdmVersion("6.19.0")


@pytest.fixture
def other_version() -> CdmVersion:
    return CdmVersion("6.0.0")


@pytest.fixture
def initialised_store(store: CdmStore, version: CdmVersion) -> CdmStore:
    """A store with cache root and one version initialised."""
    store.init()
    store.init_version(version)
    return store


# ── VersionStatus ─────────────────────────────────────────────────────────────


class TestVersionStatus:
    def test_defaults(self):
        s = VersionStatus(version="6.19.0")
        assert s.downloaded is False
        assert s.cleaned is False
        assert s.generated is False
        assert s.downloaded_at is None
        assert s.cleaned_at is None
        assert s.generated_at is None
        assert s.cdm_lite_version is None

    def test_round_trip_json(self):
        s = VersionStatus(
            version="6.19.0", downloaded=True, downloaded_at="2026-01-01T00:00:00+00:00"
        )
        restored = VersionStatus.from_json(s.to_json())
        assert restored == s

    def test_to_json_is_valid_json(self):
        s = VersionStatus(version="6.19.0")
        parsed = json.loads(s.to_json())
        assert parsed["version"] == "6.19.0"


# ── Config ────────────────────────────────────────────────────────────────────


class TestConfig:
    def test_defaults(self):
        c = Config()
        assert c.current_version is None

    def test_round_trip_json(self):
        c = Config(current_version="6.19.0")
        restored = Config.from_json(c.to_json())
        assert restored == c

    def test_to_json_is_valid_json(self):
        c = Config(current_version="6.19.0")
        parsed = json.loads(c.to_json())
        assert parsed["current_version"] == "6.19.0"


# ── CdmStore.init ─────────────────────────────────────────────────────────────


class TestInit:
    def test_creates_cache_dir(self, store: CdmStore):
        assert not store.cache_dir.exists()
        store.init()
        assert store.cache_dir.exists()

    def test_init_idempotent(self, store: CdmStore):
        store.init()
        store.init()  # should not raise
        assert store.cache_dir.exists()

    def test_init_version_creates_subdirs(self, store: CdmStore, version: CdmVersion):
        store.init()
        store.init_version(version)
        assert store.schema_raw_dir(version).exists()
        assert store.schema_clean_dir(version).exists()
        assert store.models_dir(version).exists()

    def test_init_version_creates_status_json(self, store: CdmStore, version: CdmVersion):
        store.init()
        store.init_version(version)
        status_path = store._status_path(version)
        assert status_path.exists()
        status = VersionStatus.from_json(status_path.read_text())
        assert status.version == version.version
        assert status.downloaded is False

    def test_init_version_idempotent(self, initialised_store: CdmStore, version: CdmVersion):
        """Re-initialising should not overwrite existing status."""
        initialised_store.mark_downloaded(version)
        initialised_store.init_version(version)  # re-init
        assert initialised_store.is_downloaded(version)  # status preserved


# ── Path resolution ───────────────────────────────────────────────────────────


class TestPaths:
    def test_schema_raw_dir(self, store: CdmStore, version: CdmVersion):
        path = store.schema_raw_dir(version)
        assert path == store.cache_dir / "versions" / "6.19.0" / "schema-raw"

    def test_schema_clean_dir(self, store: CdmStore, version: CdmVersion):
        path = store.schema_clean_dir(version)
        assert path == store.cache_dir / "versions" / "6.19.0" / "schema-clean"

    def test_models_dir(self, store: CdmStore, version: CdmVersion):
        path = store.models_dir(version)
        assert path == store.cache_dir / "versions" / "6.19.0" / "models"

    def test_different_versions_have_different_paths(
        self, store: CdmStore, version: CdmVersion, other_version: CdmVersion
    ):
        assert store.models_dir(version) != store.models_dir(other_version)


# ── Status reads ──────────────────────────────────────────────────────────────


class TestStatusReads:
    def test_status_raises_if_not_initialised(self, store: CdmStore, version: CdmVersion):
        store.init()
        with pytest.raises(FileNotFoundError, match="not found in cache"):
            store.status(version)

    def test_is_downloaded_false_if_not_initialised(self, store: CdmStore, version: CdmVersion):
        assert store.is_downloaded(version) is False

    def test_is_cleaned_false_if_not_initialised(self, store: CdmStore, version: CdmVersion):
        assert store.is_cleaned(version) is False

    def test_is_generated_false_if_not_initialised(self, store: CdmStore, version: CdmVersion):
        assert store.is_generated(version) is False

    def test_status_returns_correct_version(self, initialised_store: CdmStore, version: CdmVersion):
        status = initialised_store.status(version)
        assert status.version == version.version


# ── Status writes ─────────────────────────────────────────────────────────────


class TestStatusWrites:
    def test_mark_downloaded(self, initialised_store: CdmStore, version: CdmVersion):
        assert not initialised_store.is_downloaded(version)
        initialised_store.mark_downloaded(version)
        assert initialised_store.is_downloaded(version)

    def test_mark_downloaded_sets_timestamp(self, initialised_store: CdmStore, version: CdmVersion):
        initialised_store.mark_downloaded(version)
        status = initialised_store.status(version)
        assert status.downloaded_at is not None

    def test_mark_cleaned(self, initialised_store: CdmStore, version: CdmVersion):
        initialised_store.mark_cleaned(version)
        assert initialised_store.is_cleaned(version)

    def test_mark_cleaned_sets_timestamp(self, initialised_store: CdmStore, version: CdmVersion):
        initialised_store.mark_cleaned(version)
        status = initialised_store.status(version)
        assert status.cleaned_at is not None

    def test_mark_generated(self, initialised_store: CdmStore, version: CdmVersion):
        initialised_store.mark_generated(version, cdm_lite_version="0.1.0")
        assert initialised_store.is_generated(version)

    def test_mark_generated_sets_timestamp_and_version(
        self, initialised_store: CdmStore, version: CdmVersion
    ):
        initialised_store.mark_generated(version, cdm_lite_version="0.1.0")
        status = initialised_store.status(version)
        assert status.generated_at is not None
        assert status.cdm_lite_version == "0.1.0"

    def test_marks_are_independent(self, initialised_store: CdmStore, version: CdmVersion):
        """Marking downloaded should not affect cleaned or generated."""
        initialised_store.mark_downloaded(version)
        status = initialised_store.status(version)
        assert status.downloaded is True
        assert status.cleaned is False
        assert status.generated is False


# ── Config ────────────────────────────────────────────────────────────────────


class TestConfigPersistence:
    def test_load_config_returns_defaults_if_missing(self, store: CdmStore):
        store.init()
        config = store.load_config()
        assert config.current_version is None

    def test_save_and_load_config(self, store: CdmStore):
        store.init()
        config = Config(current_version="6.19.0")
        store.save_config(config)
        restored = store.load_config()
        assert restored == config

    def test_set_current_version(self, initialised_store: CdmStore, version: CdmVersion):
        initialised_store.set_current_version(version)
        assert initialised_store.current_version() == version

    def test_current_version_returns_none_if_not_set(self, store: CdmStore):
        store.init()
        assert store.current_version() is None

    def test_cached_versions(
        self,
        initialised_store: CdmStore,
        version: CdmVersion,
        other_version: CdmVersion,
    ):
        initialised_store.init_version(other_version)
        cached = initialised_store.cached_versions()
        assert version in cached
        assert other_version in cached


# ── Sym Link Manangement  ──────────────────────────────────────────────────────────────


class TestSymLinkManagement:
    def test_update_current_symlink(self, initialised_store: CdmStore, version: CdmVersion):
        initialised_store.update_current_symlink(version)
        current = initialised_store.current_models_dir()
        assert current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction())
        assert current.resolve() == initialised_store.models_dir(version).resolve()

    def test_update_current_symlink_replaces_existing(
        self, initialised_store: CdmStore, version: CdmVersion, other_version: CdmVersion
    ):
        initialised_store.init_version(other_version)
        initialised_store.update_current_symlink(other_version)
        initialised_store.update_current_symlink(version)
        current = initialised_store.current_models_dir()
        assert current.resolve() == initialised_store.models_dir(version).resolve()
