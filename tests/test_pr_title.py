"""The pull request title check accepts Conventional Commits titles and nothing else."""

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / ".github" / "scripts" / "check-pr-title.sh"
USAGE = "type(optional scope)!: description"


def check(title):
    """Run the check with PR_TITLE set to title, or unset when title is None."""
    env = {"PATH": os.environ["PATH"]}
    if title is not None:
        env["PR_TITLE"] = title
    return subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize(
    "title",
    [
        "feat: estimate room occupancy from motion and occupancy sensors",
        "fix(panel): keep the tab after a reload",
        "feat!: store rooms by area id",
        "refactor(model)!: split the filter",
        "docs: explain releases",
        "chore: update lockfiles",
        "test: cover renames",
        "build: pin numpy",
        "ci: add the title check",
        "perf: skip unchanged rooms",
        'revert: "feat: add guests"',
    ],
)
def test_accepts_conventional_titles(title):
    result = check(title)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "title",
    [
        None,
        "",
        "Add release automation",
        "14: Add release automation",
        "feature: add guests",
        "Feat: add guests",
        "feat add guests",
        "feat:add guests",
        "feat:  ",
        "feat(): add guests",
        "feat(panel: add guests",
        "feat!(panel): add guests",
        " feat: add guests",
        "feat: add guests\nsecond line",
        "feat: add guests\r",
        "feat: add\tguests",
    ],
)
def test_rejects_other_titles(title):
    result = check(title)
    assert result.returncode == 1
    assert USAGE in result.stdout
