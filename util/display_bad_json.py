import json

path = "./lib/cdm-schema/cdm-product-collateral-RatingPriorityResolutionEnum.schema.json"  # put the failing file path here

with open(path, encoding="utf-8") as f:
    content = f.read()

try:
    json.loads(content)
except json.JSONDecodeError as e:
    # e.lineno and e.colno are 1-based
    lines = content.splitlines()
    bad_line = lines[e.lineno - 1]
    bad_char = bad_line[e.colno - 1]
    print(f"Line {e.lineno}, col {e.colno}")
    print(f"Character: {repr(bad_char)}")
    print(f"Ordinal:   {ord(bad_char)}")
    print(f"Context:   {repr(bad_line[max(0, e.colno - 20) : e.colno + 20])}")
