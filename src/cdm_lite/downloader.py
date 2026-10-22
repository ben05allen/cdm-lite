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

# PEP 810 explicit lazy imports: defer httpx2 until a download is attempted
# (Python 3.15+ only; ignored on older versions).
__lazy_modules__ = ["httpx2"]

import hashlib
import hmac
import io
import re
import shutil
import tarfile
import time
import zipfile
from collections.abc import Callable, Generator
from pathlib import Path

import httpx2
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TransferSpeedColumn,
)

from cdm_lite.registry import CdmVersion

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 0.5
_HEX_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


class DownloadError(Exception):
    pass


def unpack_tar(data: bytes, output_dir: Path) -> Generator[int, None, None]:
    try:
        # mode="r:*" handles transparent decompression (gz, bz2, xz) and plain tar
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
            json_members = [m for m in tf.getmembers() if m.name.endswith(".json")]
            yield len(json_members)
            for member in json_members:
                # Security: Manual path traversal protection for Python 3.11 compatibility
                rel_path = Path(member.name)
                if rel_path.is_absolute() or ".." in rel_path.parts:
                    yield 1
                    continue

                f = tf.extractfile(member)
                if f is None:
                    yield 1
                    continue

                output_path = output_dir / rel_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(f.read())
                yield 1

    except (tarfile.TarError, EOFError) as e:
        raise DownloadError(f"not a valid tar.gz file: {e}") from e


def unpack_zip(data: bytes, output_dir: Path) -> Generator[int, None, None]:
    try:
        with zipfile.ZipFile(io.BytesIO(data), mode="r") as zf:
            json_members = [m for m in zf.infolist() if m.filename.endswith(".json")]
            yield len(json_members)
            for member in json_members:
                # zipfile.extract strips dangerous path components by default
                zf.extract(member, path=output_dir)
                yield 1

    except (zipfile.BadZipFile, EOFError) as e:
        raise DownloadError(f"not a valid .zip file: {e}") from e


# ── Downloading ───────────────────────────────────────────────────────────────


def _get_with_retries(
    client: httpx2.Client,
    url: str,
    *,
    attempts: int = MAX_ATTEMPTS,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx2.Response:
    """
    GET with retries for transient failures.

    Connection errors and 5xx responses are retried with linear backoff.
    4xx responses are permanent and re-raised immediately.
    """
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = client.get(url)
            response.raise_for_status()
            return response
        except httpx2.HTTPStatusError as e:
            if e.response.status_code < 500:
                raise
            last_error = e
        except httpx2.RequestError as e:
            last_error = e

        if attempt < attempts:
            sleep(BACKOFF_SECONDS * attempt)

    assert last_error is not None
    raise last_error


def _fetch_checksum(client: httpx2.Client, checksum_url: str) -> str | None:
    """Fetch the published SHA-1 checksum, returning None if unavailable."""
    try:
        response = client.get(checksum_url, timeout=10.0)
        response.raise_for_status()
    except httpx2.HTTPError:
        return None

    tokens = response.text.split()
    if not tokens:
        return None

    digest = tokens[0].lower()
    return digest if _HEX_SHA1_RE.match(digest) else None


def _verify_checksum(data: bytes, expected: str | None, version: CdmVersion) -> None:
    """Raise DownloadError when the archive does not match the published digest."""
    if expected is None:
        return

    actual = hashlib.sha1(data).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise DownloadError(
            f"checksum mismatch for CDM {version}: published {expected}, downloaded {actual}"
        )


# ── Unpacking ─────────────────────────────────────────────────────────────────


def _unpack_atomically(data: bytes, output_dir: Path) -> int:
    """
    Unpack into a sibling ``*.partial`` directory and swap it in on success.

    A failed extraction never leaves partial files in ``output_dir``; any
    previously downloaded schemas there are left untouched until the new
    archive has been fully unpacked.
    """
    tmp_dir = output_dir.parent / f"{output_dir.name}.partial"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    unpack_total = 0
    try:
        if zipfile.is_zipfile(io.BytesIO(data)):
            gen = unpack_zip(data, tmp_dir)
        else:
            gen = unpack_tar(data, tmp_dir)

        unpack_total = next(gen, 0)
        for _ in gen:
            pass
    except Exception:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise

    if output_dir.exists():
        shutil.rmtree(output_dir)
    tmp_dir.rename(output_dir)
    return unpack_total


def _download_archive(
    client: httpx2.Client,
    version: CdmVersion,
    url: str,
    progress: Progress,
    sleep: Callable[[float], None],
) -> tuple[bytes, str | None]:
    """Download the schema archive, verifying the published checksum."""
    task = progress.add_task(f"Downloading CDM {version} schemas...", total=None)

    try:
        response = _get_with_retries(client, url, sleep=sleep)
    except httpx2.HTTPStatusError as e:
        raise DownloadError(
            f"Failed to download CDM {version}: HTTP {e.response.status_code}"
        ) from e
    except httpx2.RequestError as e:
        raise DownloadError(f"Failed to download CDM {version}: {e}") from e

    data = response.content
    content_length = int(response.headers.get("content-length", 0))
    progress.update(task, total=content_length or len(data), completed=len(data))

    checksum = _fetch_checksum(client, f"{url}.sha1")
    _verify_checksum(data, checksum, version)
    return data, checksum


def _unpack_with_progress(data: bytes, output_dir: Path, progress: Progress) -> int:
    """Unpack the archive atomically, driving the progress bar."""
    task = progress.add_task("Unpacking schemas...", total=None)
    files = _unpack_atomically(data, output_dir)
    progress.update(task, total=files, completed=files)
    return files


def download_schemas(
    version: CdmVersion,
    output_dir: Path,
    *,
    client: httpx2.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """
    Download the CDM JSON Schema archive for the given version and unpack it
    into output_dir, returning the verified SHA-1 digest (None if the index
    did not publish one).

    Transient failures are retried; checksums are verified when published; the
    unpack either lands completely or leaves output_dir unchanged.
    """
    url = version.schema_url
    owns_client = client is None
    if owns_client:
        client = httpx2.Client(follow_redirects=True, timeout=30.0)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        ) as progress:
            data, checksum = _download_archive(client, version, url, progress, sleep)
            unpacked = _unpack_with_progress(data, output_dir, progress)
    finally:
        if owns_client and client is not None:
            client.close()

    if unpacked:
        print(f"✔ Downloaded, verified and unpacked {unpacked} schema files to {output_dir}")
    return checksum
