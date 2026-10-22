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

"""Tests for PEP 810 explicit lazy import declarations (``__lazy_modules__``)."""

import importlib
import subprocess
import sys

import pytest

_HAS_LAZY_IMPORTS = sys.version_info >= (3, 15)

# Modules that declare lazy imports, mapped to the module names they defer.
EXPECTED_LAZY_MODULES = {
    "cdm_lite.cli": {"cdm_lite.cleaner", "cdm_lite.downloader", "cdm_lite.generator"},
    "cdm_lite.registry": {"httpx2"},
    "cdm_lite.downloader": {"httpx2"},
}


def _run_in_subprocess(script: str) -> None:
    """Run ``script`` in a fresh interpreter so ``sys.modules`` starts clean."""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"subprocess failed:\n{result.stderr}"


@pytest.mark.parametrize(
    "module_name",
    sorted(EXPECTED_LAZY_MODULES),
    ids=sorted(EXPECTED_LAZY_MODULES),
)
def test_lazy_modules_declared(module_name: str) -> None:
    """Every module opts its deferred imports in via ``__lazy_modules__``."""
    module = importlib.import_module(module_name)
    declared = set(getattr(module, "__lazy_modules__", []))
    assert EXPECTED_LAZY_MODULES[module_name] <= declared


@pytest.mark.skipif(
    not _HAS_LAZY_IMPORTS,
    reason="PEP 810 lazy imports require Python 3.15+",
)
def test_cli_import_defers_heavy_modules() -> None:
    """Importing the CLI must not load generator, downloader or httpx2 on 3.15+."""
    _run_in_subprocess(
        """
import sys

import cdm_lite.cli

deferred = {
    "cdm_lite.cleaner",
    "cdm_lite.downloader",
    "cdm_lite.generator",
    "cdm_lite.templates.pyproject_toml",
    "datamodel_code_generator",
    "httpx2",
}
loaded = deferred & set(sys.modules)
assert not loaded, f"eagerly imported: {sorted(loaded)}"
"""
    )


@pytest.mark.skipif(
    not _HAS_LAZY_IMPORTS,
    reason="PEP 810 lazy imports require Python 3.15+",
)
def test_registry_import_defers_httpx2() -> None:
    """Importing the registry alone must not load httpx2 until a request is made."""
    _run_in_subprocess(
        """
import sys

import cdm_lite.registry

assert "httpx2" not in sys.modules, "httpx2 was eagerly imported"
"""
    )


@pytest.mark.skipif(
    not _HAS_LAZY_IMPORTS,
    reason="PEP 810 lazy imports require Python 3.15+",
)
def test_lazy_import_reifies_on_first_access() -> None:
    """First access to a lazy name resolves the module immediately."""
    _run_in_subprocess(
        """
import sys

import cdm_lite.cli

assert "cdm_lite.cleaner" not in sys.modules

clean_schemas = cdm_lite.cli.clean_schemas  # attribute access reifies the import

assert "cdm_lite.cleaner" in sys.modules, "cleaner did not reify on access"
assert callable(clean_schemas)
"""
    )
