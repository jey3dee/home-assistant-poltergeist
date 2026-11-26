#!/usr/bin/env bash
# Fails unless PR_TITLE is a Conventional Commits title. The squash commit takes the pull
# request title, and release-please reads the next version from it.
set -euo pipefail

title="${PR_TITLE-}"
types='feat|fix|docs|chore|refactor|test|build|ci|perf|revert'
pattern="^(${types})(\([^()[:space:]][^()]*\))?!?: [^[:space:]].*$"

# In [[ =~ ]], . also matches a line break or other control character, so those are
# rejected first.
if [[ "$title" == *[[:cntrl:]]* || ! "$title" =~ $pattern ]]; then
    echo "Pull request title: ${title}"
    echo "It must read type(optional scope)!: description"
    echo "Types: ${types//|/, }"
    echo "fix raises the patch number, feat the minor number, ! a breaking change."
    exit 1
fi

echo "Pull request title is valid: ${title}"
