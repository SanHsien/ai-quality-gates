"""Fail closed when mutmut reports incomplete or surviving mutations."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

PROBLEM_FIELDS = (
    "survived",
    "no_tests",
    "skipped",
    "suspicious",
    "timeout",
    "check_was_interrupted_by_user",
    "segfault",
)


def evaluate_mutation_stats(path: Path, *, minimum_score: float) -> dict[str, Any]:
    stats = json.loads(path.read_text(encoding="utf-8"))
    total = int(stats["total"])
    killed = int(stats["killed"])
    score = round(killed / total * 100, 2) if total else 0.0
    problematic = {name: int(stats.get(name, 0)) for name in PROBLEM_FIELDS}
    passed = total > 0 and score >= minimum_score and not any(problematic.values())
    return {
        "passed": passed,
        "score": score,
        "minimum_score": minimum_score,
        "killed": killed,
        "total": total,
        "problematic": problematic,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", type=Path, nargs="?", default=Path("mutants/mutmut-cicd-stats.json")
    )
    parser.add_argument("--minimum-score", type=float, default=100.0)
    args = parser.parse_args(argv)
    result = evaluate_mutation_stats(args.path, minimum_score=args.minimum_score)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
