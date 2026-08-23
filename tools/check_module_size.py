"""Fail when a maintained Python module exceeds a simple size budget."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModuleSizeViolation:
    path: Path
    lines: int
    limit: int


def count_maintained_lines(path: Path) -> int:
    """Count non-empty, non-comment-only physical lines."""

    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def iter_python_modules(paths: Sequence[Path]) -> list[Path]:
    modules: set[Path] = set()
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            modules.add(path)
        elif path.is_dir():
            modules.update(path.rglob("*.py"))
    return sorted(modules)


def find_oversized_modules(
    paths: Sequence[Path],
    *,
    max_lines: int,
) -> list[ModuleSizeViolation]:
    violations = []
    for path in iter_python_modules(paths):
        lines = count_maintained_lines(path)
        if lines > max_lines:
            violations.append(ModuleSizeViolation(path=path, lines=lines, limit=max_lines))
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--max-lines", type=int, default=200)
    args = parser.parse_args(argv)

    violations = find_oversized_modules(args.paths, max_lines=args.max_lines)
    if violations:
        for violation in violations:
            print(f"{violation.path}: {violation.lines} maintained lines (limit {violation.limit})")
        return 1

    measured = [(path, count_maintained_lines(path)) for path in iter_python_modules(args.paths)]
    maximum = max((lines for _, lines in measured), default=0)
    print(f"MODULE SIZE GREEN: max={maximum}, limit={args.max_lines}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
