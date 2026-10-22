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

# PEP 810 explicit lazy imports: defer httpx2 until a network request is made
# (Python 3.15+ only; ignored on older versions).
__lazy_modules__ = ["httpx2"]

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import httpx2

MAVEN_BASE = "https://repo1.maven.org/maven2/org/finos/cdm/cdm-json-schema"
METADATA_URL = f"{MAVEN_BASE}/maven-metadata.xml"

# Maven pre-release markers used by the FINOS CDM project. Only "-dev" is
# observed in practice, but the others are treated as pre-releases too so a
# pre-release is never advertised as "latest stable".
_DEV_RE = re.compile(r"-(?:dev|test|rc|alpha|beta|snapshot)\b", re.IGNORECASE)


@dataclass(frozen=True)
class CdmVersion:
    version: str

    @cached_property
    def pep440(self) -> str:
        """
        Sanitize Maven-style versions to be PEP 440 compliant.
        Example: 0.0.0-test.1 -> 0.0.0.dev1
        """
        # Replace common Maven/FINOS pre-release markers with PEP 440 equivalents
        s = self.version.replace("-test.", ".dev")
        s = s.replace("-dev.", ".dev")
        s = s.replace("-SNAPSHOT", ".dev0")

        # Handle hyphenated pre-release keywords (e.g., -rc.1 -> .rc1)
        # PEP 440 prefers .rc1, .dev1, .a1 over -rc.1
        s = re.sub(r"-(?P<pre>rc|alpha|beta|dev|a|b)\.?", r".\g<pre>", s, flags=re.IGNORECASE)

        return s

    @cached_property
    def is_stable(self) -> bool:
        return not bool(_DEV_RE.search(self.version))

    @cached_property
    def schema_url(self) -> str:
        return f"{MAVEN_BASE}/{self.version}/cdm-json-schema-{self.version}.zip"

    def __str__(self) -> str:
        return self.version

    def __lt__(self, other: "CdmVersion") -> bool:
        return self.version < other.version


class CdmRegistry:
    """Queries Maven Central for available CDM JSON Schema versions.

    The last successful metadata response is cached on disk so that version
    discovery, ``latest_stable`` and version lookups keep working offline.
    """

    def __init__(self, timeout: float = 10.0, metadata_cache: Path | None = None):
        self._timeout = timeout
        self._metadata: ET.Element | None = None
        self._metadata_cache = metadata_cache
        self.served_from_cache = False

    def _fetch_metadata(self) -> ET.Element:
        if self._metadata is not None:
            return self._metadata

        try:
            response = httpx2.get(METADATA_URL, timeout=self._timeout, follow_redirects=True)
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except (httpx2.HTTPError, ET.ParseError) as e:
            text = self._read_cache(error=e)
            try:
                root = ET.fromstring(text)
            except ET.ParseError as cache_error:
                raise RuntimeError(
                    "The cached Maven metadata is corrupt. Delete "
                    f"{self._metadata_cache} or run cdm-lite with network access."
                ) from cache_error
            self.served_from_cache = True
            self._metadata = root
            return root

        self._write_cache(response.text)
        self.served_from_cache = False
        self._metadata = root
        return root

    def _read_cache(self, error: Exception) -> str:
        """Read the cached metadata, raising a helpful error when unavailable."""
        if self._metadata_cache is not None and self._metadata_cache.is_file():
            return self._metadata_cache.read_text(encoding="utf-8")
        raise RuntimeError(
            f"Could not reach Maven Central ({error}) and no cached metadata is available. "
            "Run cdm-lite once with network access."
        ) from error

    def _write_cache(self, text: str) -> None:
        if self._metadata_cache is None:
            return
        try:
            self._metadata_cache.parent.mkdir(parents=True, exist_ok=True)
            self._metadata_cache.write_text(text, encoding="utf-8")
        except OSError:
            pass  # a read-only cache must not break version discovery

    def all_versions(self, include_dev: bool = False) -> list[CdmVersion]:
        """Return all available versions, sorted ascending."""
        root = self._fetch_metadata()
        versions = [
            CdmVersion(v.text.strip())
            for v in root.findall("./versioning/versions/version")
            if v.text
        ]
        if not include_dev:
            versions = [v for v in versions if v.is_stable]
        return sorted(versions)

    def latest_stable(self) -> CdmVersion:
        """Return the latest stable (non-dev) release."""
        stable = self.all_versions(include_dev=False)
        if not stable:
            raise RuntimeError("No stable CDM versions found on Maven Central")
        return stable[-1]

    def latest(self) -> CdmVersion:
        """Return the latest version including dev releases."""
        root = self._fetch_metadata()
        latest = root.findtext("./versioning/latest")
        if not latest:
            raise RuntimeError("Could not determine latest CDM version")
        return CdmVersion(latest.strip())

    def get(self, version: str) -> CdmVersion:
        """Look up a specific version, raising ValueError if not found."""
        all_v = self.all_versions(include_dev=True)
        matches = [v for v in all_v if v.version == version]
        if not matches:
            available = ", ".join(str(v) for v in all_v[-5:])
            raise ValueError(
                f"Version '{version}' not found on Maven Central. Recent versions: {available}"
            )
        return matches[0]
