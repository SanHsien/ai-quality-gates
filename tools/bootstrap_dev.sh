#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export UV_PROJECT_ENVIRONMENT=".venv-linux"

uv sync --frozen --python 3.12
echo "BOOTSTRAP GREEN: run bash tools/dev_check.sh --quick"
