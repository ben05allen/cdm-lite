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

from unittest.mock import MagicMock

import httpx2
import pytest

from cdm_lite.registry import CdmRegistry, CdmVersion

# ── Unit tests (no network) ───────────────────────────────────────────────────

SAMPLE_METADATA = """<?xml version="1.0" encoding="UTF-8"?>
<metadata>
  <groupId>org.finos.cdm</groupId>
  <artifactId>cdm-json-schema</artifactId>
  <versioning>
    <latest>7.0.0-dev.99</latest>
    <release>6.19.0</release>
    <versions>
      <version>6.0.0</version>
      <version>6.1.0</version>
      <version>6.19.0</version>
      <version>7.0.0-dev.1</version>
      <version>7.0.0-dev.99</version>
    </versions>
    <lastUpdated>20260101000000</lastUpdated>
  </versioning>
</metadata>"""


@pytest.fixture
def registry(monkeypatch):
    """Registry with network call replaced by sample XML."""
    import xml.etree.ElementTree as ET

    reg = CdmRegistry()
    monkeypatch.setattr(reg, "_fetch_metadata", lambda: ET.fromstring(SAMPLE_METADATA))
    return reg


class TestCdmVersion:
    def test_stable_version(self):
        assert CdmVersion("6.19.0").is_stable is True

    def test_dev_version(self):
        assert CdmVersion("7.0.0-dev.99").is_stable is False

    @pytest.mark.parametrize(
        "version",
        [
            "7.0.0-dev.1",
            "6.19.0-dev.5",
            "0.0.0-test.1",
            "6.19.0-SNAPSHOT",
            "6.19.0-rc.1",
            "6.19.0-alpha",
            "6.19.0-beta",
        ],
    )
    def test_pre_release_versions_are_not_stable(self, version: str):
        assert CdmVersion(version).is_stable is False

    @pytest.mark.parametrize(
        "version",
        ["6.19.0", "7.7.0", "8.0.0", "1.0.0-1", "2024.1.2"],
    )
    def test_release_versions_are_stable(self, version: str):
        assert CdmVersion(version).is_stable is True

    def test_str(self):
        assert str(CdmVersion("6.19.0")) == "6.19.0"

    def test_ordering(self):
        versions = [CdmVersion("6.19.0"), CdmVersion("6.0.0"), CdmVersion("6.1.0")]
        assert min(versions) == CdmVersion("6.0.0")

    def test_schema_url(self):
        v = CdmVersion("6.19.0")
        assert v.schema_url == (
            "https://repo1.maven.org/maven2/org/finos/cdm/cdm-json-schema/6.19.0/cdm-json-schema-6.19.0.zip"
        )

    def test_frozen(self):
        v = CdmVersion("6.19.0")
        with pytest.raises(AttributeError):
            v.version = "7.0.0"  # type: ignore

    @pytest.mark.parametrize(
        "maven,pep440",
        [
            ("6.19.0", "6.19.0"),
            ("0.0.0-test.1", "0.0.0.dev1"),
            ("0.0.0-dev.1", "0.0.0.dev1"),
            ("6.19.0-dev.5", "6.19.0.dev5"),
            ("6.19.0-SNAPSHOT", "6.19.0.dev0"),
            ("6.0.0-rc.1", "6.0.0.rc1"),
        ],
    )
    def test_pep440_sanitization(self, maven, pep440):
        assert CdmVersion(maven).pep440 == pep440


class TestCdmRegistry:
    def test_all_versions_excludes_dev_by_default(self, registry):
        versions = registry.all_versions()
        assert all(v.is_stable for v in versions)
        assert len(versions) == 3

    def test_all_versions_includes_dev(self, registry):
        versions = registry.all_versions(include_dev=True)
        assert len(versions) == 5

    def test_all_versions_sorted(self, registry):
        versions = registry.all_versions(include_dev=True)
        assert versions == sorted(versions)

    def test_latest_stable(self, registry):
        assert registry.latest_stable() == CdmVersion("6.19.0")

    def test_latest_includes_dev(self, registry):
        assert registry.latest() == CdmVersion("7.0.0-dev.99")

    def test_get_known_version(self, registry):
        v = registry.get("6.1.0")
        assert v == CdmVersion("6.1.0")

    def test_get_unknown_version_raises(self, registry):
        with pytest.raises(ValueError, match="not found"):
            registry.get("99.0.0")

    def test_get_dev_version(self, registry):
        v = registry.get("7.0.0-dev.1")
        assert v.is_stable is False


# ── Offline metadata cache ────────────────────────────────────────────────────


class TestOfflineMetadata:
    @staticmethod
    def _fake_get(text: str):
        def get(*_args, **_kwargs):
            response = MagicMock()
            response.text = text
            response.raise_for_status.return_value = None
            return response

        return get

    @staticmethod
    def _offline(*_args, **_kwargs):
        raise httpx2.RequestError("Connection refused")

    def test_caches_metadata_after_a_successful_fetch(self, monkeypatch, tmp_path):

        monkeypatch.setattr("cdm_lite.registry.httpx2.get", self._fake_get(SAMPLE_METADATA))
        cache = tmp_path / "maven-metadata.xml"
        registry = CdmRegistry(metadata_cache=cache)

        registry.all_versions()

        assert registry.served_from_cache is False
        assert cache.is_file()
        assert "6.19.0" in cache.read_text(encoding="utf-8")

    def test_falls_back_to_the_cache_when_offline(self, monkeypatch, tmp_path):

        cache = tmp_path / "maven-metadata.xml"
        cache.write_text(SAMPLE_METADATA, encoding="utf-8")
        monkeypatch.setattr("cdm_lite.registry.httpx2.get", self._offline)
        registry = CdmRegistry(metadata_cache=cache)

        versions = registry.all_versions()

        assert registry.served_from_cache is True
        assert CdmVersion("6.19.0") in versions
        assert registry.latest_stable() == CdmVersion("6.19.0")
        # A cached response must also serve version lookups
        assert registry.get("6.19.0").version == "6.19.0"

    def test_reports_a_helpful_error_without_cache_or_network(self, monkeypatch, tmp_path):

        monkeypatch.setattr("cdm_lite.registry.httpx2.get", self._offline)
        registry = CdmRegistry(metadata_cache=tmp_path / "missing.xml")

        with pytest.raises(RuntimeError, match="Maven Central"):
            registry.all_versions()

    def test_survives_a_corrupt_cache(self, monkeypatch, tmp_path):

        cache = tmp_path / "maven-metadata.xml"
        cache.write_text("<<< not xml", encoding="utf-8")
        monkeypatch.setattr("cdm_lite.registry.httpx2.get", self._fake_get(SAMPLE_METADATA))
        registry = CdmRegistry(metadata_cache=cache)

        # The corrupt cache is overwritten by the fresh fetch
        assert registry.all_versions()
        assert "6.19.0" in cache.read_text(encoding="utf-8")

    def test_corrupt_cache_falls_back_to_a_parse_error_offline(self, monkeypatch, tmp_path):

        cache = tmp_path / "maven-metadata.xml"
        cache.write_text("<<< not xml", encoding="utf-8")
        monkeypatch.setattr("cdm_lite.registry.httpx2.get", self._offline)
        registry = CdmRegistry(metadata_cache=cache)

        with pytest.raises(RuntimeError, match="corrupt"):
            registry.all_versions()


# ── Integration test (real network, skipped in CI) ───────────────────────────


@pytest.mark.integration
def test_real_maven_central():
    """Hits Maven Central — run with: pytest -m integration"""
    reg = CdmRegistry()
    versions = reg.all_versions()
    assert len(versions) > 0
    latest = reg.latest_stable()
    assert latest.is_stable
    assert latest in versions
    print(f"\nLatest stable: {latest}")
    print(f"All stable versions: {[str(v) for v in versions]}")
