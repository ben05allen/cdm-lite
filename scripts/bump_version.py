#!/usr/bin/env python3
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

"""Bump the project version and keep every version reference in sync.

A single command updates all four places the version lives:

* ``pyproject.toml``  - the ``project.version`` field
* ``pyproject.toml``  - the ``Development Status`` trove classifier
* ``README.md``       - the ``Current Phase`` status line
* ``CHANGELOG.md``    - a new section for the version

Usage::

    uv run python scripts/bump_version.py 0.6.1
    uv run python scripts/bump_version.py 0.7.0b1 --note "Add cdm-lite upgrade"
    uv run python scripts/bump_version.py 0.6.1 --dry-run
"""

from __future__ import annotations

import re
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
README = REPO_ROOT / "README.md"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

BETA_CLASSIFIER = "Development Status :: 4 - Beta"
STABLE_CLASSIFIER = "Development Status :: 5 - Production/Stable"

# PEP 440 versions we are willing to write, e.g. 1.0.0, 0.7.0b1, 1.0.0rc1, 1.0.0.dev1
VERSION_RE = re.compile(
    r"^\d+(\.\d+)*((a|b|rc)\d+)?(\.dev\d+)?$",
    re.IGNORECASE,
)

PRERELEASE_RE = re.compile(r"((a|b|rc)\d+)|(\.dev\d+)", re.IGNORECASE)


class BumpError(Exception):
    """Raised when the requested bump cannot be applied."""


def is_prerelease(version: str) -> bool:
    """Return True if the version carries a pre-release marker (a/b/rc/dev)."""
    return bool(PRERELEASE_RE.search(version))


def classifier_for(version: str) -> str:
    """Return the trove classifier matching the release stage of the version."""
    return BETA_CLASSIFIER if is_prerelease(version) else STABLE_CLASSIFIER


def read_project_version(text: str) -> str:
    """Extract ``project.version`` from pyproject.toml source."""
    data = tomllib.loads(text)
    return str(data["project"]["version"])


def update_pyproject(text: str, new_version: str) -> str:
    """Return pyproject.toml source with the version and classifier updated."""
    text, count = re.subn(
        r'^version = "[^"]+"$',
        f'version = "{new_version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise BumpError("Could not find the project version in pyproject.toml")

    text, count = re.subn(
        r'^  "Development Status :: [^"]+",$',
        f'  "{classifier_for(new_version)}",',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise BumpError("Could not find the Development Status classifier in pyproject.toml")

    return text


def update_readme(text: str, new_version: str) -> str:
    """Return README source with the status line pointing at the new version."""
    phase = "Beta" if is_prerelease(new_version) else "Stable"
    text, count = re.subn(
        r"^\*\*Current Phase:\*\* (?:Beta|Stable) \(v[^)]+\)$",
        f"**Current Phase:** {phase} (v{new_version})",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise BumpError("Could not find the 'Current Phase' status line in README.md")
    return text


def update_changelog(text: str, new_version: str, date: str, note: str) -> str:
    """Return CHANGELOG source with a new section for the new version.

    Entries sitting under ``## [Unreleased]`` are moved into the new release
    section (Keep a Changelog semantics) and a fresh empty ``[Unreleased]``
    section is recreated above it.
    """
    heading = f"## [{new_version}] - {date}"
    if f"## [{new_version}]" in text:
        raise BumpError(f"CHANGELOG.md already has a section for {new_version}")

    unreleased = re.search(r"^## \[Unreleased\]\s*$", text, flags=re.MULTILINE)
    if unreleased is not None:
        return _release_from_unreleased(text, unreleased, heading, note)

    body = f"{heading}\n\n### Added\n\n- {note}\n\n"
    match = re.search(r"^## \[", text, flags=re.MULTILINE)
    if match is None:
        raise BumpError("Could not find an existing release section in CHANGELOG.md")

    return text[: match.start()] + body + text[match.start() :]


def _release_from_unreleased(
    text: str,
    unreleased: re.Match[str],
    heading: str,
    note: str,
) -> str:
    """Turn the Unreleased block into a released section, keeping a fresh one."""
    following = re.search(r"^## \[", text[unreleased.end() :], flags=re.MULTILINE)
    end = unreleased.end() + following.start() if following else len(text)

    content = _add_note(text[unreleased.end() : end].strip("\n"), note)
    block = f"## [Unreleased]\n\n{heading}\n\n{content}\n\n"
    return text[: unreleased.start()] + block + text[end:]


def _add_note(content: str, note: str) -> str:
    """Prepend ``note`` to the Added subsection of an unreleased block."""
    if not content:
        return f"### Added\n\n- {note}"

    partitioned = content.partition("### Added")
    if partitioned[1]:
        head, _, tail = partitioned
        return f"{head}### Added\n\n- {note}\n{tail.lstrip(chr(10))}"

    return f"### Added\n\n- {note}\n\n{content}"


def _read(path: Path) -> str:
    if not path.is_file():
        raise BumpError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def bump(
    new_version: str,
    note: str = "Describe the changes in this release.",
    date: str | None = None,
    dry_run: bool = False,
) -> list[tuple[Path, str]]:
    """Apply the bump, returning the list of (path, new content) changes."""
    if not VERSION_RE.match(new_version):
        raise BumpError(f"'{new_version}' is not a valid PEP 440 version")

    release_date = date or datetime.now(UTC).strftime("%Y-%m-%d")

    pyproject_text = _read(PYPROJECT)
    current = read_project_version(pyproject_text)
    if current == new_version:
        raise BumpError(f"Project is already at version {new_version}")

    changes = [
        (PYPROJECT, update_pyproject(pyproject_text, new_version)),
        (README, update_readme(_read(README), new_version)),
        (CHANGELOG, update_changelog(_read(CHANGELOG), new_version, release_date, note)),
    ]

    if not dry_run:
        for path, text in changes:
            _write(path, text)

    return changes


def main(argv: list[str] | None = None) -> int:
    """Command line entry point."""
    args = list(sys.argv[1:] if argv is None else argv)

    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    note = "Describe the changes in this release."
    if "--note" in args:
        index = args.index("--note")
        try:
            note = args[index + 1]
        except IndexError:
            print("error: --note requires a value", file=sys.stderr)
            return 2
        del args[index : index + 2]

    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2

    try:
        changes = bump(args[0], note=note, dry_run=dry_run)
    except BumpError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    for path, _ in changes:
        print(f"{'would update' if dry_run else 'updated'} {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
