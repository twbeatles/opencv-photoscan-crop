#!/usr/bin/env bash
# Install git pre-push hook that runs scripts/verify.sh (same path as CI).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -d .git && ! -f .git ]]; then
  echo "Not a git repository: $REPO_ROOT" >&2
  exit 1
fi

GIT_DIR="$(git rev-parse --git-dir)"
HOOKS_DIR="$GIT_DIR/hooks"
mkdir -p "$HOOKS_DIR"

cp -f scripts/pre-push "$HOOKS_DIR/pre-push"
chmod +x "$HOOKS_DIR/pre-push"

echo "Installed pre-push hook -> $HOOKS_DIR/pre-push"
echo "Push will now run scripts/verify (compileall + selftest + pytest + pyright)."
