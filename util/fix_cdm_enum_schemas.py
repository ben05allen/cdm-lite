import json
import argparse
from pathlib import Path
import re
import shutil


def is_enum_schema(schema: dict) -> bool:
    return "enum" in schema and schema.get("type") == "string"


def clean_enum_schema(schema: dict) -> dict:
    """Remove the oneOf from enum schemas - it only carries title info
    which we preserve by keeping the top-level description."""
    cleaned = {k: v for k, v in schema.items() if k != "oneOf"}
    return cleaned


def process_directory(input_dir: str, output_dir: str):
    cleaned = 0
    copied = 0
    fixed = 0
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    for in_path in input_path.rglob("*.json"):
        rel_path = in_path.relative_to(input_path)
        out_path = output_path / rel_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with in_path.open(encoding="utf-8") as f:
            content = f.read()

            try:
                schema = json.loads(content)
            except json.JSONDecodeError:
                cleaned_content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", content)
                cleaned_content = cleaned_content.replace("\t", " ")
                cleaned_content = cleaned_content.replace("\n", " ")
                schema = json.loads(cleaned_content)
                fixed += 1

            if is_enum_schema(schema) and "oneOf" in schema:
                schema = clean_enum_schema(schema)
                cleaned += 1

                output_path.touch()
                with out_path.open("w") as f:
                    json.dump(schema, f, indent=2)
                copied += 1

            else:
                shutil.copy2(str(in_path), str(output_path))
                copied += 1

    print(f"Processed {copied} files, cleaned oneOf from {cleaned} enum schemas, fixed {fixed} deserialization errors.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="cdm-schema")
    parser.add_argument("--output", default="cdm-schema-clean")
    args = parser.parse_args()

    args_output = Path(args.output)
    if args_output.exists():
        if args_output.is_dir():
            shutil.rmtree(str(args_output))
        else:
            args_output.unlink()

    args_output.mkdir()

    process_directory(args.input, args.output)
