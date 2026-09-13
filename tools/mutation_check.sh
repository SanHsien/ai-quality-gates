#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export UV_PROJECT_ENVIRONMENT=".venv-mutation"

mutation_dir="$repo_root/mutants"
if [[ "$repo_root" == "/" || "$mutation_dir" != "$repo_root/mutants" ]]; then
  echo "refusing unsafe mutation-cache cleanup: $mutation_dir" >&2
  exit 2
fi
rm -rf -- "$mutation_dir"

uv sync --frozen --python 3.12
uv run mutmut run
uv run mutmut export-cicd-stats
uv run python tools/check_mutation_score.py --minimum-score 100
