#!/usr/bin/env bash
# Validate Agent Skills with pinned skills-ref.
# Usage: validate_skills.sh [SKILLS_ROOT]
# SKILLS_ROOT defaults to $SKILLS_ROOT or the current working directory (caller checkout).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-${SKILLS_ROOT:-$(pwd)}}"

# Pin agentskills/skills-ref for reproducible CI (do not float on @main).
# SHA from https://github.com/agentskills/agentskills when the pin was set.
SKILLS_REF_SHA="69ef37e9424c0a7ea9dd2293b559e43ec8176379"
SKILLS_REF_SPEC="git+https://github.com/agentskills/agentskills.git@${SKILLS_REF_SHA}#subdirectory=skills-ref"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required (https://docs.astral.sh/uv/). Install it or use astral-sh/setup-uv in CI." >&2
  exit 1
fi

# Python >=3.11 required by skills-ref; pyyaml rebuilds frontmatter after
# stripping Cursor-only keys (see validate_skills.py).
exec uv run --python 3.13 --with "$SKILLS_REF_SPEC" --with "pyyaml>=6" \
  python "$SCRIPT_DIR/validate_skills.py" "$ROOT"
