#!/usr/bin/env bash
# Bash helper to create a GitHub repository using GitHub CLI (gh), commit local files,
# and push the current repository to the new remote.
#
# Usage:
#   In Git Bash, run:
#     /c/Users/VHome/push_with_gh.sh
#   Or make it executable and run from the working dir.

set -euo pipefail
IFS=$'\n\t'

REPO_NAME=""
OWNER=""
VISIBILITY="public"

# Change to the working directory
cd "/c/Users/VHome" || { echo "Failed to cd to /c/Users/VHome" >&2; exit 2; }

# Ensure git is present
if ! command -v git >/dev/null 2>&1; then
  echo "git not found in PATH. Install Git for Windows (include Git Bash) and retry." >&2
  exit 3
fi

# Ensure branch is main
git branch -M main 2>/dev/null || true

# Ensure README and .gitignore exist
if [ ! -f README.md ]; then
  printf "%s\n" "# WhatsHot QTSC Core" > README.md
fi
if [ ! -f .gitignore ]; then
  printf "%s\n%s\n" "__pycache__/" "WhatsHot_IP_Anchor_*.json" > .gitignore
fi

# Stage and commit
git add -A
if git diff --cached --quiet; then
  echo "No staged changes to commit."
else
  git commit -m "feat: Initialize WhatsHot, Inc. metadata anchoring and CI test suite" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>" || true
  echo "Committed staged changes."
fi

# Ensure gh is present
if ! command -v gh >/dev/null 2>&1; then
  echo "gh (GitHub CLI) not found in PATH. Install gh and authenticate (gh auth login) before running this script." >&2
  exit 4
fi

# Check auth status
if ! gh auth status >/dev/null 2>&1; then
  echo "gh not authenticated — running gh auth login (follow prompts)..."
  gh auth login || { echo "gh auth login failed or was not completed." >&2; exit 5; }
fi

# Prompt for repo name if needed
read -r -p "Repository name (e.g. WhatsHot-QTSC-Core): " REPO_NAME
if [ -z "$REPO_NAME" ]; then
  echo "Repository name is required." >&2
  exit 6
fi

read -r -p "Owner (user or org). Leave blank to create under your account: " OWNER
read -r -p "Visibility (public/private) [public]: " VIS_IN
if [ -n "$VIS_IN" ]; then
  VISIBILITY="$VIS_IN"
fi

if [ -n "$OWNER" ]; then
  FULL="$OWNER/$REPO_NAME"
else
  FULL="$REPO_NAME"
fi

echo "Creating repository: $FULL (visibility: $VISIBILITY)"

if [ "$VISIBILITY" = "public" ]; then
  gh repo create "$FULL" --public --source=. --remote=origin --push
else
  gh repo create "$FULL" --private --source=. --remote=origin --push
fi

echo "Repository created and pushed: https://github.com/$FULL"
exit 0
