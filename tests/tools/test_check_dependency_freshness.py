from __future__ import annotations

import json
from pathlib import Path

from tools.check_dependency_freshness import (
    Declaration,
    Status,
    is_newer,
    load_declarations,
    load_deferrals,
    parse_holds,
    unresolved,
)

PYPROJECT = """
[build-system]
requires = ["hatchling>=1.32,<2"]

[project]
dependencies = []

[dependency-groups]
dev = [
  "ruff>=0.16,<1",
  "radon>=6.0,<7",  # freshness-hold: 6.x 是最後支援本專案介面的版本線
]
"""


def declaration(name: str, floor: str, hold: str = "") -> Declaration:
    return Declaration(
        name=name, floor=floor, requirement=f"{name}>={floor}", group="dev", hold=hold
    )


def test_floor_is_compared_at_the_precision_it_states() -> None:
    # `>=0.12` promises a 0.12+ line, so 0.12.4 is not news; 0.16 is.
    assert not is_newer("0.12.4", "0.12")
    assert is_newer("0.16.4", "0.12")
    assert not is_newer("6.0.1", "6.0")


def test_hold_marker_binds_to_the_package_declared_on_that_line(tmp_path: Path) -> None:
    holds = parse_holds(PYPROJECT)

    assert holds == {"radon": "6.x 是最後支援本專案介面的版本線"}


def test_declarations_cover_dependency_groups_and_the_build_backend(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT, encoding="utf-8")

    declarations = load_declarations(pyproject)

    assert [(item.name, item.group, item.floor) for item in declarations] == [
        ("ruff", "group:dev", "0.16"),
        ("radon", "group:dev", "6.0"),
        ("hatchling", "build-system", "1.32"),
    ]
    assert declarations[1].hold  # the held floor carries its reason


def test_deferral_without_a_reviewed_release_is_ignored(tmp_path: Path) -> None:
    # Otherwise a deferral becomes a permanently silenced check.
    path = tmp_path / "deferrals.json"
    path.write_text(json.dumps({"deferrals": {"mypy": {"reason": "later"}}}), encoding="utf-8")

    assert load_deferrals(path) == {}


def test_missing_deferrals_file_defers_nothing(tmp_path: Path) -> None:
    assert load_deferrals(tmp_path / "absent.json") == {}


def test_aged_floor_needs_review_unless_held_or_deferred() -> None:
    plain = Status(declaration=declaration("ruff", "0.12"), latest="0.16.4", deferred_reason="")
    held = Status(
        declaration=declaration("ruff", "0.12", hold="policy"), latest="0.16.4", deferred_reason=""
    )
    deferred = Status(
        declaration=declaration("ruff", "0.12"), latest="0.16.4", deferred_reason="需要人工驗證"
    )

    assert plain.needs_review
    assert not held.needs_review
    assert not deferred.needs_review
    assert held.label.startswith("維持宣告")
    assert deferred.label.startswith("已延後")


def test_a_missing_floor_and_an_unanswered_lookup_both_stay_unresolved() -> None:
    no_floor = Status(declaration=declaration("ruff", ""), latest="0.16.4", deferred_reason="")
    no_answer = Status(declaration=declaration("ruff", "0.16"), latest=None, deferred_reason="")

    assert unresolved([no_floor])
    assert unresolved([no_answer])
    assert unresolved([])
    assert not unresolved(
        [Status(declaration=declaration("ruff", "0.16"), latest="0.16.4", deferred_reason="")]
    )


def test_repository_declarations_all_state_a_floor() -> None:
    assert all(item.floor for item in load_declarations())
