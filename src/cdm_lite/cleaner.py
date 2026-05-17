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

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

# Control characters that are illegal unescaped in JSON strings.
# Excludes \n (0x0a) and \r (0x0d) which are valid between tokens.
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x09\x0b\x0c\x0e-\x1f]")

# Matches literal tabs and newlines inside JSON string values
_STRING_CONTENT_RE = re.compile(r'"(?:[^"\\]|\\.)*"', re.DOTALL)

# ── Schema cleaning functions ─────────────────────────────────────────────────


def _fix_control_chars(content: str) -> str:
    """
    Replace illegal control characters inside JSON string values only.
    Tabs and newlines between tokens are left untouched.
    """

    def clean_string(match: re.Match) -> str:
        s = match.group(0)
        s = s.replace("\t", " ")
        s = s.replace("\n", " ")
        s = _CONTROL_CHAR_RE.sub(" ", s)
        return s

    return _STRING_CONTENT_RE.sub(clean_string, content)


def _is_enum_schema(schema: dict) -> bool:
    return "enum" in schema and schema.get("type") == "string"


def _strip_redundant_one_of(schema: dict) -> dict:
    """
    Remove the oneOf from enum schemas.
    The oneOf only carries per-value titles which datamodel-codegen
    mishandles, generating multiple spurious classes per enum.
    The top-level description is preserved.
    """
    return {k: v for k, v in schema.items() if k != "oneOf"}


def _load_schema(path: Path) -> tuple[dict, bool]:
    """
    Load a JSON schema file, applying control character fixes if needed.
    Returns (schema, was_fixed).
    """
    content = path.read_text(encoding="utf-8")
    try:
        return json.loads(content), False
    except json.JSONDecodeError:
        return json.loads(_fix_control_chars(content)), True


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class CleanResult:
    processed: int = 0
    fixed: int = 0  # control character fixes applied
    cleaned: int = 0  # oneOf stripped from enum schemas

    def __str__(self) -> str:
        return (
            f"Processed {self.processed} files: "
            f"{self.cleaned} enum schemas cleaned, "
            f"{self.fixed} files had encoding fixes applied."
        )


# ── Main entry point ──────────────────────────────────────────────────────────


def clean_schemas(input_dir: Path, output_dir: Path) -> CleanResult:
    """
    Clean all JSON schema files from input_dir, writing to output_dir.
    The output directory structure mirrors the input.
    """
    result = CleanResult()

    for in_path in sorted(input_dir.rglob("*.json")):
        rel_path = in_path.relative_to(input_dir)
        out_path = output_dir / rel_path

        # Ensure the output subdirectory exists
        out_path.parent.mkdir(parents=True, exist_ok=True)

        schema, was_fixed = _load_schema(in_path)
        if was_fixed:
            result.fixed += 1

        if _is_enum_schema(schema) and "oneOf" in schema:
            schema = _strip_redundant_one_of(schema)
            result.cleaned += 1
            out_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        else:
            shutil.copy2(in_path, out_path)

        result.processed += 1

    return result
