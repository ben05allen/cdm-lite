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
from pathlib import Path
import tarfile

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


def download_schemas(version: CdmVersion, output_dir: Path) -> None:
    """
    Download the CDM JSON Schema zip for the given version and
    unpack it into output_dir.
    """
    url = version.schema_url

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

        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                json_members = [m for m in tf.getmembers() if m.name.endswith(".json")]
                unpack_task = progress.add_task("Unpacking schemas...", total=len(json_members))
                for member in json_members:
                    f = tf.extractfile(member)
                    if f is None:
                        continue
                    out_path = output_dir / member.name
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_bytes(f.read())
                    progress.advance(unpack_task)

        except tarfile.TarError as e:
            raise DownloadError(
                f"Downloaded file for CDM {version} is not a valid tar.gz: {e}"
            ) from e

    if json_members:
        print(f"✔ Downloaded and unpacked {len(json_members)} schema files to {output_dir}")
