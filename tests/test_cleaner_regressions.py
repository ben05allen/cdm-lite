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
