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
import tarfile
import zipfile
from collections.abc import Generator
from pathlib import Path

import httpx
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TransferSpeedColumn,
)

from cdm_lite.registry import CdmVersion


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


def download_schemas(version: CdmVersion, output_dir: Path) -> None:
    """
    Download the CDM JSON Schema zip for the given version and
    unpack it into output_dir.
    """
    url = version.schema_url
    unpack_total = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
    ) as progress:
        # ── Download ──────────────────────────────────────────────────────────

        task = progress.add_task(f"Downloading CDM {version} schemas...", total=None)

        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            try:
                response = client.get(url)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise DownloadError(
                    f"Failed to download CDM {version}: HTTP {e.response.status_code}"
                ) from e
            except httpx.RequestError as e:
                raise DownloadError(f"Failed to download CDM {version}: {e}") from e

            content_length = int(response.headers.get("content-length", 0))
            progress.update(task, total=content_length)

            data = response.content
            progress.update(task, completed=len(data))

        # ── Unpack ────────────────────────────────────────────────────────────

        unpack_task = progress.add_task("Unpacking schemas...", total=None)

        # Detect zip files otherwise fall back to tar files
        if zipfile.is_zipfile(io.BytesIO(data)):
            gen = unpack_zip(data, output_dir)
        else:
            # Default to tar (handles .tar.gz and .tar)
            gen = unpack_tar(data, output_dir)

        try:
            unpack_total = next(gen)
            progress.update(unpack_task, total=unpack_total)

            for _ in gen:
                progress.advance(unpack_task)
        except StopIteration:
            pass

    if unpack_total:
        print(f"✔ Downloaded and unpacked {unpack_total} schema files to {output_dir}")
