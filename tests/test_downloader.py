import io
import json
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from cdm_lite.downloader import DownloadError, download_schemas
from cdm_lite.registry import CdmVersion


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_tar_gz(*files: tuple[str, dict]) -> bytes:
    """
    Build an in-memory tar.gz containing the given (filename, schema_dict) pairs.
    Returns the raw bytes.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, schema in files:
            content = json.dumps(schema, indent=2).encode("utf-8")
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    return buf.getvalue()


def make_response(
    content: bytes,
    status_code: int = 200,
    content_type: str = "application/gzip",
) -> MagicMock:
    """Build a mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.content = content
    response.headers = {
        "content-length": str(len(content)),
        "content-type": content_type,
    }
    # raise_for_status raises on 4xx/5xx
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=response,
        )
    else:
        response.raise_for_status.return_value = None
    return response


SAMPLE_SCHEMAS = [
    (
        "cdm/base/staticdata/party/CounterpartyRoleEnum.json",
        {
            "type": "string",
            "title": "CounterpartyRoleEnum",
            "enum": ["Party1", "Party2"],
        },
    ),
    (
        "cdm/event/common/TradeState.json",
        {
            "type": "object",
            "title": "TradeState",
            "properties": {"trade": {"$ref": "Trade.json"}},
        },
    ),
    (
        "cdm/base/datetime/PeriodEnum.json",
        {
            "type": "string",
            "title": "PeriodEnum",
            "enum": ["D", "W", "M", "Y"],
        },
    ),
]


@pytest.fixture
def version() -> CdmVersion:
    return CdmVersion("6.19.0")


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "schema-raw"
    d.mkdir()
    return d


@pytest.fixture
def sample_tar_gz() -> bytes:
    return make_tar_gz(*SAMPLE_SCHEMAS)


# ── Mock context manager helper ───────────────────────────────────────────────


class MockHttpxClient:
    """
    Context manager that mimics httpx.Client, returning
    a pre-configured response from client.get().
    """

    def __init__(self, response: MagicMock):
        self._response = response
        self.get = MagicMock(return_value=response)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ── Happy path ────────────────────────────────────────────────────────────────


class TestDownloadSchemas:
    def test_unpacks_json_files(self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes):
        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        json_files = list(output_dir.rglob("*.json"))
        assert len(json_files) == len(SAMPLE_SCHEMAS)

    def test_mirrors_directory_structure(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        assert (output_dir / "cdm/base/staticdata/party/CounterpartyRoleEnum.json").exists()
        assert (output_dir / "cdm/event/common/TradeState.json").exists()
        assert (output_dir / "cdm/base/datetime/PeriodEnum.json").exists()

    def test_unpacked_files_are_valid_json(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        for path in output_dir.rglob("*.json"):
            assert json.loads(path.read_text())  # must not raise

    def test_unpacked_file_content_matches_source(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        schema = json.loads((output_dir / "cdm/event/common/TradeState.json").read_text())
        assert schema["title"] == "TradeState"

    def test_calls_correct_url(self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes):
        response = make_response(sample_tar_gz)
        mock_client = MockHttpxClient(response)
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = mock_client
            download_schemas(version, output_dir)

        mock_client.get.assert_called_once_with(version.schema_url)

    def test_ignores_non_json_files_in_archive(self, version: CdmVersion, output_dir: Path):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for name, content in [
                ("cdm/schema.json", json.dumps({"type": "object"})),
                ("README.md", "# CDM Schemas"),
                ("checksum.sha1", "abc123"),
            ]:
                encoded = content.encode("utf-8")
                info = tarfile.TarInfo(name=name)
                info.size = len(encoded)
                tf.addfile(info, io.BytesIO(encoded))

        response = make_response(buf.getvalue())
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        assert (output_dir / "cdm/schema.json").exists()
        assert not (output_dir / "README.md").exists()
        assert not (output_dir / "checksum.sha1").exists()


# ── Error handling ────────────────────────────────────────────────────────────


class TestDownloadErrors:
    def test_raises_on_404(self, version: CdmVersion, output_dir: Path):
        response = make_response(b"Not Found", status_code=404)
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="404"):
                download_schemas(version, output_dir)

    def test_raises_on_500(self, version: CdmVersion, output_dir: Path):
        response = make_response(b"Server Error", status_code=500)
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="500"):
                download_schemas(version, output_dir)

    def test_raises_on_network_error(self, version: CdmVersion, output_dir: Path):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.RequestError("Connection refused")

        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = mock_client
            with pytest.raises(DownloadError, match="Connection refused"):
                download_schemas(version, output_dir)

    def test_raises_on_bad_tar(self, version: CdmVersion, output_dir: Path):
        response = make_response(b"this is not a tar.gz file")
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="not a valid tar.gz"):
                download_schemas(version, output_dir)

    def test_raises_on_empty_response(self, version: CdmVersion, output_dir: Path):
        response = make_response(b"")
        with patch("cdm_lite.downloader.httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="not a valid tar.gz"):
                download_schemas(version, output_dir)


# ── Integration test ──────────────────────────────────────────────────────────


@pytest.mark.integration
def test_real_download(tmp_path: Path):
    """Downloads real schemas from Maven Central — run with: pytest -m integration"""
    version = CdmVersion("6.19.0")
    output_dir = tmp_path / "schema-raw"
    output_dir.mkdir()

    download_schemas(version, output_dir)

    json_files = list(output_dir.rglob("*.json"))
    assert len(json_files) > 100  # CDM has ~756 schema files
    assert (output_dir / "jsonschema/cdm-event-common-TradeState.schema.json").exists()
