#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export UV_PROJECT_ENVIRONMENT=".venv-linux"

quick=false
mutation=false
for argument in "$@"; do
  case "$argument" in
    --quick) quick=true ;;
    --mutation) mutation=true ;;
    *) echo "unknown argument: $argument" >&2; exit 2 ;;
  esac
done

uv run python -m compileall -q src tools tests features
uv run ruff format --check .
uv run ruff check .
uv run mypy src tools
uv run lint-imports
uv run python -m tools.check_loop_policy

if "$quick"; then
  uv run pytest -q
else
  mkdir -p artifacts
  uv run pytest -q --cov=quality_gate_demo --cov-branch --cov-report=term-missing \
    --cov-report=json:artifacts/coverage.json --junitxml=artifacts/junit.xml
fi

uv run behave --no-capture
uv run python tools/qa_smoke.py
uv run xenon --max-absolute A --max-modules A --max-average A src
uv run xenon --max-absolute B --max-modules A --max-average A tools
uv run python tools/check_module_size.py src tools --max-lines 200

if ! "$quick"; then
  uv run python tools/check_docs.py
  uv run python -m tools.write_quality_summary
  uv run pip-audit
  uv build
fi

if "$mutation"; then
  bash tools/mutation_check.sh
fi

echo "DEVELOPMENT GATE GREEN"
