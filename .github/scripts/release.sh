#!/usr/bin/env bash
# Releases the checked-out commit. The next version follows from the commit titles since
# the last v* tag; the tag and the GitHub release are made on this commit, and the release
# carries poltergeist.zip, the integration with that version in its manifest.json. Nothing
# is committed back: in git, manifest.json keeps version 0.0.0.
set -euo pipefail

types_patch='fix|perf|revert'
types_none='docs|chore|refactor|test|build|ci'
title_pattern="^(feat|${types_patch}|${types_none})(\([^()]+\))?(!)?: "

head=$(git rev-parse HEAD)
done_tag=$(git tag --points-at HEAD --list 'v[0-9]*' | head -n 1)
if [[ -n "$done_tag" ]]; then
    echo "Commit ${head} is already released as ${done_tag}. Nothing to do."
    exit 0
fi

if last_tag=$(git describe --tags --abbrev=0 --match 'v[0-9]*' HEAD 2>/dev/null); then
    range="${last_tag}..HEAD"
else
    last_tag="v0.0.0"
    range="HEAD"
fi
echo "Last release: ${last_tag}. Commits since then:"

# 3 = breaking, 2 = feature, 1 = patch, 0 = no release.
level=0
titles=()
while IFS= read -r title; do
    titles+=("$title")
    this=0 bump="none, not a Conventional Commits title"
    if [[ "$title" =~ $title_pattern ]]; then
        type="${BASH_REMATCH[1]}"
        if [[ -n "${BASH_REMATCH[3]}" ]]; then
            this=3 bump=breaking
        elif [[ "$type" == feat ]]; then
            this=2 bump=minor
        elif [[ "$type" =~ ^(${types_patch})$ ]]; then
            this=1 bump=patch
        else
            bump=none
        fi
    fi
    echo "  [${bump}] ${title}"
    if ((this > level)); then
        level=$this
    fi
done < <(git log --reverse --format=%s "$range")

if ((level == 0)); then
    echo "No release: no fix, perf, revert, feat or breaking change since ${last_tag}."
    exit 0
fi

IFS=. read -r major minor patch <<<"${last_tag#v}"
if ((level == 3 && major >= 1)); then
    major=$((major + 1)) minor=0 patch=0
elif ((level >= 2)); then
    # Below 1.0.0 a breaking change raises the minor number.
    minor=$((minor + 1)) patch=0
else
    patch=$((patch + 1))
fi
version="${major}.${minor}.${patch}"
echo "Next release: ${last_tag} -> v${version} on ${head}"

work=$(mktemp -d "${RUNNER_TEMP:-/tmp}/release.XXXXXX")
mkdir "$work/content"
git archive HEAD custom_components/poltergeist | tar -x -C "$work/content"
content="$work/content/custom_components/poltergeist"
jq --indent 2 --arg v "$version" '.version = $v' "$content/manifest.json" >"$work/manifest.json"
mv "$work/manifest.json" "$content/manifest.json"
zip_file="$work/poltergeist.zip"
(cd "$content" && zip -q -r -X -D "$zip_file" .)
echo "Built poltergeist.zip ($(stat -c %s "$zip_file") bytes)."

notes=$(printf -- '- %s\n' "${titles[@]}")
gh release create "v${version}" --target "$head" --title "v${version}" --notes "$notes" "$zip_file"
echo "Released v${version}."
