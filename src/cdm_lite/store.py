import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path

from platformdirs import user_cache_dir

from cdm_lite.registry import CdmVersion

# ── Cache root ────────────────────────────────────────────────────────────────

CACHE_DIR = Path(user_cache_dir("cdm-lite"))
CONFIG_PATH = CACHE_DIR / "config.json"


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class VersionStatus:
    version: str
    downloaded: bool = False
    cleaned: bool = False
    generated: bool = False
    downloaded_at: str | None = None
    cleaned_at: str | None = None
    generated_at: str | None = None
    cdm_lite_version: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "VersionStatus":
        return cls(**json.loads(text))


@dataclass
class Config:
    current_version: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, text: str) -> "Config":
        data = json.loads(text)

        # Only pass kwargs that exist as fields on the dataclass
        valid_keys = {f.name for f in fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


# ── Store ─────────────────────────────────────────────────────────────────────


class CdmStore:
    """
    Manages the local CDM cache.

    Directory layout:
        <cache>/
        ├── config.json
        └── versions/
            └── 6.19.0/
                ├── status.json
                ├── schema-raw/
                ├── schema-clean/
                └── models/
    """

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.config_path = cache_dir / "config.json"

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _version_dir(self, version: CdmVersion) -> Path:
        return self.cache_dir / "versions" / version.version

    def _versions_base_dir(self) -> Path:
        return self.cache_dir / "versions"

    def _status_path(self, version: CdmVersion) -> Path:
        return self._version_dir(version) / "status.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Initialisation ────────────────────────────────────────────────────────

    def init(self) -> None:
        """Create the cache root directory if it doesn't exist."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._versions_base_dir().mkdir(parents=True, exist_ok=True)

    def init_version(self, version: CdmVersion) -> None:
        """Create the directory structure for a specific version."""
        base = self._version_dir(version)
        for subdir in ("schema-raw", "schema-clean", "models"):
            (base / subdir).mkdir(parents=True, exist_ok=True)

        # Write a fresh status.json if one doesn't exist yet
        status_path = self._status_path(version)
        if not status_path.exists():
            status = VersionStatus(version=version.version)
            status_path.write_text(status.to_json())

    # ── Path resolution ───────────────────────────────────────────────────────

    def schema_raw_dir(self, version: CdmVersion) -> Path:
        return self._version_dir(version) / "schema-raw"

    def schema_clean_dir(self, version: CdmVersion) -> Path:
        return self._version_dir(version) / "schema-clean"

    def models_dir(self, version: CdmVersion) -> Path:
        return self._version_dir(version) / "models"

    # ── Status reads ──────────────────────────────────────────────────────────

    def status(self, version: CdmVersion) -> VersionStatus:
        """Read the status for a version, raising if not initialised."""
        path = self._status_path(version)
        if not path.exists():
            raise FileNotFoundError(
                f"Version {version} not found in cache. Run `cdm-lite init --version {version}` first."
            )
        return VersionStatus.from_json(path.read_text())

    def is_downloaded(self, version: CdmVersion) -> bool:
        try:
            return self.status(version).downloaded
        except FileNotFoundError:
            return False

    def is_cleaned(self, version: CdmVersion) -> bool:
        try:
            return self.status(version).cleaned
        except FileNotFoundError:
            return False

    def is_generated(self, version: CdmVersion) -> bool:
        try:
            return self.status(version).generated
        except FileNotFoundError:
            return False

    # ── Status writes ─────────────────────────────────────────────────────────

    def _update_status(self, version: CdmVersion, **kwargs) -> None:
        """Read-modify-write the status file."""
        path = self._status_path(version)
        status = VersionStatus.from_json(path.read_text())
        for key, value in kwargs.items():
            setattr(status, key, value)
        path.write_text(status.to_json())

    def mark_downloaded(self, version: CdmVersion) -> None:
        self._update_status(
            version,
            downloaded=True,
            downloaded_at=self._now(),
        )

    def mark_cleaned(self, version: CdmVersion) -> None:
        self._update_status(
            version,
            cleaned=True,
            cleaned_at=self._now(),
        )

    def mark_generated(self, version: CdmVersion, cdm_lite_version: str) -> None:
        self._update_status(
            version,
            generated=True,
            generated_at=self._now(),
            cdm_lite_version=cdm_lite_version,
        )

    # ── Config ────────────────────────────────────────────────────────────────

    def load_config(self) -> Config:
        if not self.config_path.exists():
            return Config()
        return Config.from_json(self.config_path.read_text())

    def save_config(self, config: Config) -> None:
        self.config_path.write_text(config.to_json())

    def set_current_version(self, version: CdmVersion) -> None:
        config = self.load_config()
        config.current_version = version.version
        self.save_config(config)

    def current_version(self) -> CdmVersion | None:
        config = self.load_config()
        if config.current_version is None:
            return None
        return CdmVersion(config.current_version)

    def cached_versions(self) -> list[CdmVersion]:
        """Return all versions that have been initialised in the cache."""
        base = self._versions_base_dir()
        if not base.exists():
            return []

        versions = []
        for v_dir in base.iterdir():
            if v_dir.is_dir() and (v_dir / "status.json").exists():
                versions.append(CdmVersion(v_dir.name))

        return sorted(versions)

    def current_models_dir(self) -> Path:
        """The stable symlink path — always points to the active version's models."""
        return self.cache_dir / "current"

    # ── Symlink Management ────────────────────────────────────────────────────────

    def update_current_symlink(self, version: CdmVersion) -> None:
        """Point the current/ symlink at the given version's models directory."""
        import os
        import platform

        current = self.current_models_dir()
        target = self.models_dir(version)

        # Remove existing symlink, junction or directory
        if os.path.lexists(current):
            if os.path.islink(current):
                os.unlink(current)
            elif current.exists():
                raise RuntimeError(f"{current} exists and is not a symlink — refusing to overwrite.")

        if platform.system() == "Windows":
            import subprocess

            # Use junctions on Windows to avoid privilege issues with symlinks
            try:
                # cmd /c is required for mklink as it's a shell builtin
                subprocess.run(
                    ["cmd", "/c", "mklink", "/j", str(current), str(target)],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                # Fallback to standard symlink if junction fails
                try:
                    current.symlink_to(target, target_is_directory=True)
                except OSError:
                    raise RuntimeError(
                        f"Failed to create junction or symlink at {current}: {e.stderr.decode()}"
                    ) from e
        else:
            current.symlink_to(target)
