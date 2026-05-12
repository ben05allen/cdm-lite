import json

from cdm_lite.cleaner import _fix_control_chars


def test_fixes_tab_in_description():
    content = '{"description": "Kommunalschuldverschreib\tungen (Municipal Bonds)."}'
    fixed = _fix_control_chars(content)
    assert "\t" not in fixed
    assert "Kommunalschuldverschreib ungen" in fixed
    assert json.loads(fixed)  # valid JSON


def test_fixes_newline_in_description():
    content = '{"description": "If set to \'Issuer\', the rating in the \n  Issuer Criteria has priority."}'
    fixed = _fix_control_chars(content)
    assert "\n  " not in fixed
    assert json.loads(fixed)  # valid JSON


def test_does_not_corrupt_structural_whitespace():
    content = '{\n  "type": "string",\n  "title": "Test"\n}'
    fixed = _fix_control_chars(content)
    # Structural newlines preserved — still valid and still has newlines
    assert json.loads(fixed)
    assert "\n" in fixed
