from __future__ import annotations

import json
from pathlib import Path

from tools.check_mutation_score import evaluate_mutation_stats


def _write_stats(tmp_path: Path, **overrides: int) -> Path:
    values = {
        "killed": 10,
        "survived": 0,
        "total": 10,
        "no_tests": 0,
        "skipped": 0,
        "suspicious": 0,
        "timeout": 0,
        "check_was_interrupted_by_user": 0,
        "segfault": 0,
    }
    values.update(overrides)
    path = tmp_path / "mutmut-cicd-stats.json"
    path.write_text(json.dumps(values), encoding="utf-8")
    return path


def test_mutation_gate_accepts_a_fully_killed_run(tmp_path: Path) -> None:
    result = evaluate_mutation_stats(_write_stats(tmp_path), minimum_score=100.0)

    assert result["passed"] is True
    assert result["score"] == 100.0


def test_mutation_gate_rejects_survivors_even_with_lower_score_threshold(tmp_path: Path) -> None:
    result = evaluate_mutation_stats(
        _write_stats(tmp_path, killed=9, survived=1),
        minimum_score=80.0,
    )

    assert result["passed"] is False
    assert result["problematic"]["survived"] == 1


def test_mutation_gate_fails_when_no_mutants_were_measured(tmp_path: Path) -> None:
    result = evaluate_mutation_stats(
        _write_stats(tmp_path, killed=0, total=0),
        minimum_score=100.0,
    )

    assert result["passed"] is False
    assert result["score"] == 0.0
