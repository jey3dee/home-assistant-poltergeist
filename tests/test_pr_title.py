"""The pull request title check accepts Conventional Commits titles and nothing else."""

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / ".github" / "scripts" / "check-pr-title.sh"


def check(title: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT)],
        env={"PR_TITLE": title, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
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
def test_accepts_conventional_titles(title: str) -> None:
    result = check(title)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "title",
    [
        "",
        "Add release automation",
        "14: Add release automation",
        "feature: add guests",
        "Feat: add guests",
        "feat add guests",
        "feat:add guests",
        "feat: ",
        "feat:  ",
        "feat(): add guests",
        "feat(panel: add guests",
        "feat!(panel): add guests",
        " feat: add guests",
        "feat: add guests\nsecond line",
    ],
)
def test_rejects_other_titles(title: str) -> None:
    result = check(title)
    assert result.returncode == 1
    assert "type(optional scope)!: description" in result.stdout


def test_rejects_a_missing_title() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        env={"PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
