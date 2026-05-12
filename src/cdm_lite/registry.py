from dataclasses import dataclass
import httpx
from functools import cached_property
import re
import xml.etree.ElementTree as ET

MAVEN_BASE = "https://repo1.maven.org/maven2/org/finos/cdm/cdm-json-schema"
METADATA_URL = f"{MAVEN_BASE}/maven-metadata.xml"

_DEV_RE = re.compile(r"-dev", re.IGNORECASE)


@dataclass(frozen=True)
class CdmVersion:
    version: str

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
    """Queries Maven Central for available CDM JSON Schema versions."""

    def __init__(self, timeout: float = 10.0):
        self._timeout = timeout
        self._metadata: ET.Element | None = None

    def _fetch_metadata(self) -> ET.Element:
        if self._metadata is None:
            response = httpx.get(METADATA_URL, timeout=self._timeout, follow_redirects=True)
            response.raise_for_status()
            self._metadata = ET.fromstring(response.text)
        return self._metadata

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
