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

import io
import json
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx2
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
    """Build a mock httpx2.Response."""
    response = MagicMock(spec=httpx2.Response)
    response.status_code = status_code
    response.content = content
    response.text = content.decode("utf-8", errors="replace")
    response.headers = {
        "content-length": str(len(content)),
        "content-type": content_type,
    }
    # raise_for_status raises on 4xx/5xx
    if status_code >= 400:
        response.raise_for_status.side_effect = httpx2.HTTPStatusError(
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
    Context manager that mimics httpx2.Client, returning
    a pre-configured response from client.get().
    """

    def __init__(self, response: MagicMock):
        self._response = response
        self.get = MagicMock(return_value=response)
        self.close = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


# ── Happy path ────────────────────────────────────────────────────────────────


class TestDownloadSchemas:
    def test_unpacks_json_files(self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes):
        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        json_files = list(output_dir.rglob("*.json"))
        assert len(json_files) == len(SAMPLE_SCHEMAS)

    def test_mirrors_directory_structure(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        assert (output_dir / "cdm/base/staticdata/party/CounterpartyRoleEnum.json").exists()
        assert (output_dir / "cdm/event/common/TradeState.json").exists()
        assert (output_dir / "cdm/base/datetime/PeriodEnum.json").exists()

    def test_unpacked_files_are_valid_json(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        for path in output_dir.rglob("*.json"):
            assert json.loads(path.read_text(encoding="utf-8"))  # must not raise

    def test_unpacked_file_content_matches_source(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        schema = json.loads(
            (output_dir / "cdm/event/common/TradeState.json").read_text(encoding="utf-8")
        )
        assert schema["title"] == "TradeState"

    def test_calls_correct_url(self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes):
        response = make_response(sample_tar_gz)
        mock_client = MockHttpxClient(response)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = mock_client
            download_schemas(version, output_dir)

        first_url = mock_client.get.call_args_list[0].args[0]
        assert first_url == version.schema_url

    def test_requests_the_published_checksum(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        """The .sha1 sidecar must be fetched so the archive can be verified."""
        response = make_response(sample_tar_gz)
        mock_client = MockHttpxClient(response)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = mock_client
            download_schemas(version, output_dir)

        requested = [c.args[0] for c in mock_client.get.call_args_list]
        assert f"{version.schema_url}.sha1" in requested

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
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        assert (output_dir / "cdm/schema.json").exists()
        assert not (output_dir / "README.md").exists()
        assert not (output_dir / "checksum.sha1").exists()


# ── Error handling ────────────────────────────────────────────────────────────


class TestDownloadErrors:
    def test_raises_on_404(self, version: CdmVersion, output_dir: Path):
        response = make_response(b"Not Found", status_code=404)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="404"):
                download_schemas(version, output_dir)

    def test_raises_on_500(self, version: CdmVersion, output_dir: Path):
        response = make_response(b"Server Error", status_code=500)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="500"):
                download_schemas(version, output_dir, sleep=lambda _s: None)

    def test_retries_transient_500_then_succeeds(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        """A 5xx is transient: the client must back off and retry."""
        good = make_response(sample_tar_gz)
        bad = make_response(b"Server Error", status_code=500)
        no_checksum = make_response(b"", status_code=404)
        mock_client = MockHttpxClient(good)
        # two 500s, then success, then the .sha1 sidecar request
        mock_client.get = MagicMock(side_effect=[bad, bad, good, no_checksum])

        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = mock_client
            download_schemas(version, output_dir, sleep=lambda _s: None)

        archive_calls = [
            c for c in mock_client.get.call_args_list if c.args[0] == version.schema_url
        ]
        assert len(archive_calls) == 3
        assert len(list(output_dir.rglob("*.json"))) == len(SAMPLE_SCHEMAS)

    def test_does_not_retry_4xx(self, version: CdmVersion, output_dir: Path):
        """A 404 is permanent; retrying would only delay the error."""
        mock_client = MockHttpxClient(make_response(b"nope", status_code=404))
        sleeps: list[float] = []

        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = mock_client
            with pytest.raises(DownloadError, match="404"):
                download_schemas(version, output_dir, sleep=sleeps.append)

        assert mock_client.get.call_count == 1
        assert sleeps == []

    def test_raises_on_network_error(self, version: CdmVersion, output_dir: Path):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx2.RequestError("Connection refused")

        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = mock_client
            with pytest.raises(DownloadError, match="Connection refused"):
                download_schemas(version, output_dir, sleep=lambda _s: None)

    def test_raises_on_bad_tar(self, version: CdmVersion, output_dir: Path):
        response = make_response(b"this is not a tar.gz file")
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="not a valid tar.gz"):
                download_schemas(version, output_dir)

    def test_raises_on_empty_response(self, version: CdmVersion, output_dir: Path):
        response = make_response(b"")
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="not a valid tar.gz"):
                download_schemas(version, output_dir)


# ── Checksum verification ───────────────────────────────────────────────────


def routed_client(archive: MagicMock, checksum: MagicMock) -> MockHttpxClient:
    """A client that serves the archive for the artifact URL and the sidecar for .sha1."""

    def get(url: str, **_kwargs):
        return checksum if url.endswith(".sha1") else archive

    client = MockHttpxClient(archive)
    client.get = MagicMock(side_effect=get)
    return client


class TestChecksumVerification:
    def test_verifies_and_returns_the_published_digest(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        import hashlib

        expected = hashlib.sha1(sample_tar_gz).hexdigest()
        archive = make_response(sample_tar_gz)
        client = routed_client(archive, make_response(expected.encode()))

        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = client
            digest = download_schemas(version, output_dir)

        assert digest == expected
        assert len(list(output_dir.rglob("*.json"))) == len(SAMPLE_SCHEMAS)

    def test_rejects_a_mismatched_digest(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        archive = make_response(sample_tar_gz)
        client = routed_client(archive, make_response(("0" * 40).encode()))

        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = client
            with pytest.raises(DownloadError, match="checksum mismatch"):
                download_schemas(version, output_dir)

        # Nothing must be unpacked when verification fails
        assert not list(output_dir.iterdir())

    def test_proceeds_when_no_checksum_is_published(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        archive = make_response(sample_tar_gz)
        missing = make_response(b"", status_code=404)
        client = routed_client(archive, missing)

        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = client
            digest = download_schemas(version, output_dir)

        assert digest is None
        assert len(list(output_dir.rglob("*.json"))) == len(SAMPLE_SCHEMAS)

    def test_ignores_a_malformed_checksum(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        archive = make_response(sample_tar_gz)
        client = routed_client(archive, make_response(b"this is not a digest"))

        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = client
            digest = download_schemas(version, output_dir)

        assert digest is None
        assert len(list(output_dir.rglob("*.json"))) == len(SAMPLE_SCHEMAS)


# ── Atomic unpack ───────────────────────────────────────────────────────────


class TestAtomicUnpack:
    def test_failed_unpack_leaves_existing_schemas_untouched(
        self, version: CdmVersion, output_dir: Path
    ):
        """A corrupt archive must not destroy what is already cached."""
        existing = output_dir / "keepme.json"
        existing.write_text('{"keep": true}', encoding="utf-8")

        response = make_response(b"this is not a tar.gz file")
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            with pytest.raises(DownloadError, match="not a valid tar.gz"):
                download_schemas(version, output_dir)

        assert existing.read_text(encoding="utf-8") == '{"keep": true}'
        # The partial directory must be cleaned up
        assert not (output_dir.parent / "schema-raw.partial").exists()

    def test_successful_unpack_replaces_previous_contents(
        self, version: CdmVersion, output_dir: Path, sample_tar_gz: bytes
    ):
        stale = output_dir / "stale.json"
        stale.write_text("{}", encoding="utf-8")

        response = make_response(sample_tar_gz)
        with patch("cdm_lite.downloader.httpx2.Client") as mock_client_cls:
            mock_client_cls.return_value = MockHttpxClient(response)
            download_schemas(version, output_dir)

        assert not stale.exists()
        assert (output_dir / "cdm/event/common/TradeState.json").exists()
        assert not (output_dir.parent / "schema-raw.partial").exists()


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
