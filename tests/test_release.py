"""The release script derives the next version from the commit titles since the last tag."""

import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
SCRIPT = REPO / ".github" / "scripts" / "release.sh"

# Stands in for the GitHub CLI: records each call, one argument per line.
FAKE_GH = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "$GH_CALL"
cp "${@: -1}" "$GH_ZIP"
"""


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A repository with the integration's files and one non-conventional first commit."""
    path = tmp_path / "repo"
    shutil.copytree(
        REPO / "custom_components" / "poltergeist",
        path / "custom_components" / "poltergeist",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    git(path.parent, "init", "-q", "-b", "main", str(path))
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "config", "user.name", "Test")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "Initial commit")
    return path


def commit(repo, title):
    git(repo, "commit", "-q", "--allow-empty", "-m", title)


def tag(repo, name):
    git(repo, "tag", name)


def release(repo, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    call, zip_copy = tmp_path / "gh-call", tmp_path / "released.zip"
    call.unlink(missing_ok=True)
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=repo,
        env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "GH_CALL": str(call),
            "GH_ZIP": str(zip_copy),
            "RUNNER_TEMP": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    args = call.read_text().splitlines() if call.exists() else None
    return result.stdout, args, zip_copy


def released_version(args):
    assert args is not None, "no release was made"
    assert args[:2] == ["release", "create"]
    return args[2]


@pytest.mark.parametrize(
    ("last_tag", "titles", "expected"),
    [
        (None, ["feat: estimate room occupancy"], "v0.1.0"),
        ("v0.1.0", ["fix: keep the tab"], "v0.1.1"),
        ("v0.1.0", ["perf: skip unchanged rooms"], "v0.1.1"),
        ("v0.1.0", ['revert: "feat: add guests"'], "v0.1.1"),
        ("v0.1.3", ["feat(panel): add a map (#7)"], "v0.2.0"),
        ("v0.1.3", ["fix(model)!: drop the old store"], "v0.2.0"),
        ("v1.2.3", ["feat!: store rooms by area id"], "v2.0.0"),
        ("v1.2.3", ["fix: a", "refactor!: b", "feat: c"], "v2.0.0"),
        ("v0.9.0", ["fix: a", "feat: b"], "v0.10.0"),
    ],
)
def test_next_version(repo, tmp_path, last_tag, titles, expected):
    if last_tag:
        tag(repo, last_tag)
    for title in titles:
        commit(repo, title)
    _, args, _ = release(repo, tmp_path)
    assert released_version(args) == expected


def test_only_titles_since_the_last_tag_count(repo, tmp_path):
    commit(repo, "feat!: old breaking change")
    tag(repo, "v1.0.0")
    commit(repo, "fix: keep the tab")
    _, args, _ = release(repo, tmp_path)
    assert released_version(args) == "v1.0.1"


@pytest.mark.parametrize(
    "titles",
    [
        ["chore: a", "ci: b", "build: c", "test: d", "refactor: e", "docs: f"],
        ["Merge branch 'x'", "feature: not a type", "featx: not a type"],
    ],
)
def test_no_release_without_a_releasing_title(repo, tmp_path, titles):
    tag(repo, "v0.1.0")
    for title in titles:
        commit(repo, title)
    out, args, _ = release(repo, tmp_path)
    assert args is None
    assert "No release" in out


def test_no_release_when_the_commit_is_already_tagged(repo, tmp_path):
    commit(repo, "feat: add guests")
    tag(repo, "v0.1.0")
    out, args, _ = release(repo, tmp_path)
    assert args is None
    assert "already released as v0.1.0" in out


def test_release_targets_the_commit_with_notes_and_the_zip(repo, tmp_path):
    tag(repo, "v0.1.0")
    commit(repo, "fix(panel): keep the tab (#5)")
    commit(repo, "docs: explain releases (#6)")
    out, args, _ = release(repo, tmp_path)
    head = git(repo, "rev-parse", "HEAD")
    assert args[args.index("--target") + 1] == head
    assert args[args.index("--title") + 1] == "v0.1.1"
    notes = args[args.index("--notes") + 1 :]
    assert notes[:2] == ["- fix(panel): keep the tab (#5)", "- docs: explain releases (#6)"]
    assert Path(args[-1]).name == "poltergeist.zip"
    assert "v0.1.0 -> v0.1.1" in out


def test_zip_holds_the_integration_with_the_version(repo, tmp_path):
    commit(repo, "feat: add guests")
    _, _, zip_copy = release(repo, tmp_path)
    with zipfile.ZipFile(zip_copy) as archive:
        names = set(archive.namelist())
        manifest = json.loads(archive.read("manifest.json"))
    source = REPO / "custom_components" / "poltergeist"
    expected = {
        str(p.relative_to(source))
        for p in source.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }
    assert names == expected
    assert manifest["version"] == "0.1.0"
    assert manifest["domain"] == "poltergeist"
    in_git = json.loads(git(repo, "show", "HEAD:custom_components/poltergeist/manifest.json"))
    assert {k: v for k, v in manifest.items() if k != "version"} == {
        k: v for k, v in in_git.items() if k != "version"
    }
