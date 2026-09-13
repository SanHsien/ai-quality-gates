from __future__ import annotations

import json
from pathlib import Path

from tools.write_quality_summary import build_summary


def _write_reports(tmp_path: Path, coverage: float, failures: int = 0) -> tuple[Path, Path]:
    coverage_path = tmp_path / "coverage.json"
    coverage_path.write_text(
        json.dumps(
            {
                "totals": {
                    "covered_lines": 19,
                    "num_statements": 20,
                    "percent_covered": coverage,
                    "num_branches": 8,
                    "missing_branches": 0,
                }
            }
        ),
        encoding="utf-8",
    )
    junit_path = tmp_path / "junit.xml"
    junit_path.write_text(
        f'<testsuites tests="5" failures="{failures}" errors="0" skipped="0" time="0.1" />',
        encoding="utf-8",
    )
    return coverage_path, junit_path


def test_summary_reports_coverage_tests_complexity_and_module_size(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "policy.py").write_text(
        "def choose(value: bool) -> int:\n    if value:\n        return 1\n    return 0\n",
        encoding="utf-8",
    )
    coverage_path, junit_path = _write_reports(tmp_path, coverage=95.0)

    summary = build_summary(
        coverage_path=coverage_path,
        junit_path=junit_path,
        source_paths=[source],
        minimum_coverage=95.0,
        maximum_complexity=5,
        maximum_module_lines=200,
    )

    assert summary["passed"] is True
    assert summary["coverage"]["percent"] == 95.0
    assert summary["tests"]["total"] == 5
    assert summary["complexity"]["maximum"] == 2
    assert summary["modules"]["maximum_lines"] == 4


def test_summary_fails_closed_when_a_threshold_or_test_fails(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "policy.py").write_text("value = 1\n", encoding="utf-8")
    coverage_path, junit_path = _write_reports(tmp_path, coverage=94.9, failures=1)

    summary = build_summary(
        coverage_path=coverage_path,
        junit_path=junit_path,
        source_paths=[source],
        minimum_coverage=95.0,
        maximum_complexity=5,
        maximum_module_lines=200,
    )

    assert summary["passed"] is False
    assert summary["gates"]["coverage"] is False
    assert summary["gates"]["tests"] is False
