from __future__ import annotations

from pathlib import Path

from tools.check_module_size import find_oversized_modules


def test_module_size_ignores_blank_and_comment_only_lines(tmp_path: Path) -> None:
    module = tmp_path / "small.py"
    module.write_text("# heading\n\nvalue = 1\nvalue += 1\n", encoding="utf-8")

    assert find_oversized_modules([tmp_path], max_lines=2) == []


def test_module_size_reports_the_measured_limit(tmp_path: Path) -> None:
    module = tmp_path / "large.py"
    module.write_text("one = 1\ntwo = 2\nthree = 3\n", encoding="utf-8")

    violations = find_oversized_modules([tmp_path], max_lines=2)

    assert len(violations) == 1
    assert violations[0].path == module
    assert violations[0].lines == 3
    assert violations[0].limit == 2
