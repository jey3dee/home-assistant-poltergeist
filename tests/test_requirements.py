"""What the integration imports must be guaranteed to be there on the user's Home Assistant."""

import ast
import json
import re
import sys
from importlib.metadata import requires
from pathlib import Path

INTEGRATION = Path(__file__).parent.parent / "custom_components/poltergeist"


def _name(requirement: str) -> str:
    return re.match(r"[A-Za-z0-9_.-]+", requirement).group().lower()


def test_every_imported_library_comes_with_home_assistant_or_is_declared():
    imported = set()
    for path in INTEGRATION.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                imported.add(node.module.split(".")[0])
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    # These libraries are named after their import; the test harness installs more than these.
    guaranteed = {_name(r) for r in requires("homeassistant") if "extra ==" not in r}
    declared = {_name(r) for r in manifest["requirements"]}
    missing = imported - sys.stdlib_module_names - {"homeassistant"} - guaranteed - declared
    assert missing == set()
