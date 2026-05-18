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
from pathlib import Path

import pytest

from cdm_lite.cleaner import (
    CleanResult,
    _fix_control_chars,
    _is_enum_schema,
    _load_schema,
    _strip_redundant_one_of,
    clean_schemas,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def input_dir(tmp_path: Path) -> Path:
    d = tmp_path / "input"
    d.mkdir()
    return d


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "output"
    d.mkdir()
    return d


def write_schema(directory: Path, name: str, schema: dict) -> Path:
    """Helper to write a schema dict as a JSON file."""
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return path


ENUM_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "string",
    "title": "CounterpartyRoleEnum",
    "description": "Defines the counterparty roles.",
    "enum": ["Party1", "Party2"],
    "oneOf": [
        {"enum": ["Party1"], "title": "Party1"},
        {"enum": ["Party2"], "title": "Party2"},
    ],
}

NON_ENUM_SCHEMA = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "title": "TradeState",
    "description": "Represents the state of a trade.",
    "properties": {
        "trade": {"$ref": "Trade.json"},
    },
}


# ── _fix_control_chars ────────────────────────────────────────────────────────


class TestFixControlChars:
    def test_fixes_tab_in_description(self):
        content = '{"description": "Kommunalschuldverschreib\tungen (Municipal Bonds)."}'
        fixed = _fix_control_chars(content)
        assert "\t" not in fixed
        assert "Kommunalschuldverschreib ungen" in fixed
        assert json.loads(fixed)

    def test_fixes_newline_in_description(self):
        content = '{"description": "If set to Issuer, the rating in the \n  Issuer Criteria has priority."}'
        fixed = _fix_control_chars(content)
        assert "\n  " not in fixed
        assert json.loads(fixed)

    def test_does_not_corrupt_structural_whitespace(self):
        content = '{\n  "type": "string",\n  "title": "Test"\n}'
        fixed = _fix_control_chars(content)
        assert json.loads(fixed)
        assert "\n" in fixed

    def test_clean_content_unchanged(self):
        content = '{"description": "A clean description with no issues."}'
        assert _fix_control_chars(content) == content

    def test_fixes_multiple_issues_in_one_file(self):
        content = '{"description": "First\tissue.", "other": "Second\nissue."}'
        fixed = _fix_control_chars(content)
        assert "\t" not in fixed
        assert json.loads(fixed)


# ── _is_enum_schema ───────────────────────────────────────────────────────────


class TestIsEnumSchema:
    def test_detects_enum_schema(self):
        assert _is_enum_schema(ENUM_SCHEMA) is True

    def test_rejects_non_enum_schema(self):
        assert _is_enum_schema(NON_ENUM_SCHEMA) is False

    def test_rejects_enum_without_string_type(self):
        schema = {"type": "integer", "enum": [1, 2, 3]}
        assert _is_enum_schema(schema) is False

    def test_rejects_string_type_without_enum(self):
        schema = {"type": "string", "title": "SomeField"}
        assert _is_enum_schema(schema) is False

    def test_rejects_empty_schema(self):
        assert _is_enum_schema({}) is False


# ── _strip_redundant_one_of ───────────────────────────────────────────────────


class TestStripRedundantOneOf:
    def test_removes_one_of(self):
        result = _strip_redundant_one_of(ENUM_SCHEMA)
        assert "oneOf" not in result

    def test_preserves_other_fields(self):
        result = _strip_redundant_one_of(ENUM_SCHEMA)
        assert result["type"] == "string"
        assert result["title"] == "CounterpartyRoleEnum"
        assert result["description"] == "Defines the counterparty roles."
        assert result["enum"] == ["Party1", "Party2"]

    def test_no_one_of_unchanged(self):
        schema = {"type": "string", "enum": ["A", "B"]}
        result = _strip_redundant_one_of(schema)
        assert result == schema

    def test_does_not_mutate_original(self):
        original = {**ENUM_SCHEMA}
        _strip_redundant_one_of(original)
        assert "oneOf" in original


# ── _load_schema ──────────────────────────────────────────────────────────────


class TestLoadSchema:
    def test_loads_clean_file(self, tmp_path: Path):
        path = tmp_path / "clean.json"
        path.write_text(json.dumps(NON_ENUM_SCHEMA), encoding="utf-8")
        schema, was_fixed = _load_schema(path)
        assert schema == NON_ENUM_SCHEMA
        assert was_fixed is False

    def test_loads_file_with_tab_in_description(self, tmp_path: Path):
        dirty = {
            "type": "string",
            "description": "Kommunalschuldverschreib\tungen (Municipal Bonds).",
            "enum": ["DE-MUNI"],
        }
        path = tmp_path / "dirty_tab.json"
        path.write_bytes(json.dumps(dirty).encode("utf-8").replace(b"\\t", b"\t"))
        schema, was_fixed = _load_schema(path)
        assert was_fixed is True
        assert "description" in schema

    def test_loads_file_with_newline_in_description(self, tmp_path: Path):
        raw = b'{"type": "string", "description": "First line.\n  Second line.", "enum": ["A"]}'
        path = tmp_path / "dirty_newline.json"
        path.write_bytes(raw)
        schema, was_fixed = _load_schema(path)
        assert was_fixed is True
        assert "description" in schema


# ── clean_schemas ─────────────────────────────────────────────────────────────


class TestCleanSchemas:
    def test_processes_all_json_files(self, input_dir: Path, output_dir: Path):
        write_schema(input_dir, "EnumSchema.json", ENUM_SCHEMA)
        write_schema(input_dir, "NonEnumSchema.json", NON_ENUM_SCHEMA)
        result = clean_schemas(input_dir, output_dir)
        assert result.processed == 2

    def test_strips_one_of_from_enum_schemas(self, input_dir: Path, output_dir: Path):
        write_schema(input_dir, "EnumSchema.json", ENUM_SCHEMA)
        clean_schemas(input_dir, output_dir)
        output = json.loads((output_dir / "EnumSchema.json").read_text(encoding="utf-8"))
        assert "oneOf" not in output
        assert output["enum"] == ["Party1", "Party2"]

    def test_copies_non_enum_schemas_unchanged(self, input_dir: Path, output_dir: Path):
        write_schema(input_dir, "NonEnumSchema.json", NON_ENUM_SCHEMA)
        clean_schemas(input_dir, output_dir)
        output = json.loads((output_dir / "NonEnumSchema.json").read_text(encoding="utf-8"))
        assert output == NON_ENUM_SCHEMA

    def test_mirrors_directory_structure(self, input_dir: Path, output_dir: Path):
        write_schema(input_dir, "cdm/base/EnumSchema.json", ENUM_SCHEMA)
        write_schema(input_dir, "cdm/event/NonEnumSchema.json", NON_ENUM_SCHEMA)
        clean_schemas(input_dir, output_dir)
        assert (output_dir / "cdm" / "base" / "EnumSchema.json").exists()
        assert (output_dir / "cdm" / "event" / "NonEnumSchema.json").exists()

    def test_result_counts_cleaned(self, input_dir: Path, output_dir: Path):
        write_schema(input_dir, "EnumSchema.json", ENUM_SCHEMA)
        write_schema(input_dir, "NonEnumSchema.json", NON_ENUM_SCHEMA)
        result = clean_schemas(input_dir, output_dir)
        assert result.cleaned == 1

    def test_result_counts_fixed(self, input_dir: Path, output_dir: Path):
        raw = b'{"type": "string", "description": "Bad\ttab.", "enum": ["A"]}'
        path = input_dir / "dirty.json"
        path.write_bytes(raw.replace(b"\\t", b"\t"))
        result = clean_schemas(input_dir, output_dir)
        assert result.fixed == 1

    def test_empty_directory(self, input_dir: Path, output_dir: Path):
        result = clean_schemas(input_dir, output_dir)
        assert result.processed == 0
        assert result.cleaned == 0
        assert result.fixed == 0

    def test_result_str(self):
        result = CleanResult(processed=10, cleaned=3, fixed=1)
        s = str(result)
        assert "10" in s
        assert "3" in s
        assert "1" in s

    def test_output_files_are_valid_json(self, input_dir: Path, output_dir: Path):
        write_schema(input_dir, "EnumSchema.json", ENUM_SCHEMA)
        write_schema(input_dir, "NonEnumSchema.json", NON_ENUM_SCHEMA)
        clean_schemas(input_dir, output_dir)
        for out_file in output_dir.rglob("*.json"):
            assert json.loads(out_file.read_text(encoding="utf-8"))  # must not raise
