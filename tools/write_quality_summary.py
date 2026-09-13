"""Write a machine-readable summary of the repository's quantitative gates."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as element_tree
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from radon.complexity import cc_rank, cc_visit

from tools.check_module_size import count_maintained_lines, iter_python_modules


def _read_test_totals(path: Path) -> dict[str, int]:
    root = element_tree.parse(path).getroot()
    suites = (
        [root]
        if root.tag == "testsuite" or "tests" in root.attrib
        else list(root.findall(".//testsuite"))
    )
    keys = {"tests": "total", "failures": "failures", "errors": "errors", "skipped": "skipped"}
    return {
        output_key: sum(int(suite.attrib.get(input_key, 0)) for suite in suites)
        for input_key, output_key in keys.items()
    }


def _measure_source(source_paths: Sequence[Path]) -> tuple[dict[str, Any], dict[str, Any]]:
    complexities: list[tuple[str, int]] = []
    modules: list[tuple[str, int]] = []
    for path in iter_python_modules(source_paths):
        content = path.read_text(encoding="utf-8")
        modules.append((str(path), count_maintained_lines(path)))
        complexities.extend(
            (f"{path}:{block.name}", block.complexity) for block in cc_visit(content)
        )

    max_complexity = max((score for _, score in complexities), default=0)
    max_module_lines = max((lines for _, lines in modules), default=0)
    complexity = {
        "maximum": max_complexity,
        "grade": cc_rank(max_complexity) if max_complexity else "A",
        "blocks": len(complexities),
    }
    module_size = {"maximum_lines": max_module_lines, "modules": len(modules)}
    return complexity, module_size


def build_summary(
    *,
    coverage_path: Path,
    junit_path: Path,
    source_paths: Sequence[Path],
    minimum_coverage: float,
    maximum_complexity: int,
    maximum_module_lines: int,
) -> dict[str, Any]:
    coverage_totals = json.loads(coverage_path.read_text(encoding="utf-8"))["totals"]
    tests = _read_test_totals(junit_path)
    complexity, modules = _measure_source(source_paths)
    coverage = {
        "percent": round(float(coverage_totals["percent_covered"]), 2),
        "covered_lines": int(coverage_totals["covered_lines"]),
        "statements": int(coverage_totals["num_statements"]),
        "branches": int(coverage_totals.get("num_branches", 0)),
        "missing_branches": int(coverage_totals.get("missing_branches", 0)),
    }
    gates = {
        "coverage": coverage["percent"] >= minimum_coverage,
        "tests": tests["failures"] == 0 and tests["errors"] == 0 and tests["skipped"] == 0,
        "complexity": complexity["maximum"] <= maximum_complexity,
        "module_size": modules["maximum_lines"] <= maximum_module_lines,
    }
    return {
        "passed": all(gates.values()),
        "gates": gates,
        "thresholds": {
            "minimum_coverage": minimum_coverage,
            "maximum_complexity": maximum_complexity,
            "maximum_module_lines": maximum_module_lines,
        },
        "coverage": coverage,
        "tests": tests,
        "complexity": complexity,
        "modules": modules,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=Path("artifacts/coverage.json"))
    parser.add_argument("--junit", type=Path, default=Path("artifacts/junit.xml"))
    parser.add_argument("--source", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path("artifacts/quality-summary.json"))
    parser.add_argument("--minimum-coverage", type=float, default=95.0)
    parser.add_argument("--maximum-complexity", type=int, default=10)
    parser.add_argument("--maximum-module-lines", type=int, default=200)
    args = parser.parse_args(argv)
    sources = args.source or [Path("src"), Path("tools")]
    summary = build_summary(
        coverage_path=args.coverage,
        junit_path=args.junit,
        source_paths=sources,
        minimum_coverage=args.minimum_coverage,
        maximum_complexity=args.maximum_complexity,
        maximum_module_lines=args.maximum_module_lines,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
