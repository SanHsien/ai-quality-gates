"""Compare the dependency floors declared in pyproject.toml against PyPI.

Dependabot answers "has this package released?" one pull request at a time; this
answers "how far behind is everything we declare?" once a month. Declarations
only: neither the lock file nor the environment is inspected, and nothing is edited.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tomllib
import urllib.parse
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFERRALS_PATH = REPO_ROOT / ".github" / "dependency-deferrals.json"
HOLD_MARKER = "freshness-hold:"
USER_AGENT = "ai-quality-gates-dependency-freshness"

FOOTER = (
    "本報告只比對 `pyproject.toml` 的宣告與 PyPI 現行版，不看 `uv.lock`，也不改任何檔案。"
    "紅燈的兩條正當出口見 [`docs/quality-gates.md`](../docs/quality-gates.md)：宣告行上的 "
    "`# freshness-hold:`（長期政策），或 `.github/dependency-deferrals.json`（這次不升，並記下"
    "當時版本）。兩者都要寫理由；調高下限不是消音的方法。"
)

REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?\s*(.*)$")
FLOOR = re.compile(r"(>=|>|==|~=)\s*([0-9][0-9A-Za-z.!+_-]*)")
RELEASE = re.compile(r"^[0-9]+(?:\.[0-9]+)*")
QUOTED = re.compile(r"\"([^\"]+)\"|'([^']+)'")


@dataclass(frozen=True, slots=True)
class Declaration:
    name: str
    floor: str
    requirement: str
    group: str
    hold: str


@dataclass(frozen=True, slots=True)
class Status:
    declaration: Declaration
    latest: str | None
    deferred_reason: str

    @property
    def aged(self) -> bool:
        floor = self.declaration.floor
        return bool(floor and self.latest and is_newer(self.latest, floor))

    @property
    def needs_review(self) -> bool:
        """An aged floor counts unless a hold or a live deferral covers it."""

        return self.aged and not self.declaration.hold and not self.deferred_reason

    @property
    def label(self) -> str:
        if self.latest is None:
            return "檢查失敗"
        if not self.declaration.floor:
            return "未宣告下限"
        if self.aged and self.declaration.hold:
            return f"維持宣告：{self.declaration.hold}"
        if self.aged and self.deferred_reason:
            return f"已延後（{self.latest}）：{self.deferred_reason}"
        return "待審視" if self.aged else "OK"


def release_key(version: str) -> tuple[int, ...]:
    match = RELEASE.match(version.strip())
    return tuple(int(part) for part in match.group(0).split(".")) if match else ()


def is_newer(latest: str, declared: str) -> bool:
    """Is `latest` newer than `declared` at the precision `declared` states?

    A floor of `ruff>=0.12` promises a 0.12+ line, so reporting 0.12.4 against it
    would be a standing false alarm, and a report that cries wolf gets ignored.
    """

    latest_key, declared_key = release_key(latest), release_key(declared)
    depth = len(declared_key)
    padded = latest_key + (0,) * (depth - len(latest_key))
    return bool(latest_key and declared_key) and padded[:depth] > declared_key


def parse_holds(text: str) -> dict[str, str]:
    """Map package -> reason for `# freshness-hold:` comments, which tomllib drops."""

    holds: dict[str, str] = {}
    for line in text.splitlines():
        head, marker, comment = line.partition("#")
        reason = comment.strip()[len(HOLD_MARKER) :].strip()
        if not marker or not comment.strip().startswith(HOLD_MARKER) or not reason:
            continue
        for quoted in QUOTED.findall(head):
            match = REQUIREMENT.match(quoted[0] or quoted[1])
            if match:
                holds[match.group(1).lower()] = reason
    return holds


def declare(requirement: str, group: str, holds: dict[str, str]) -> Declaration | None:
    match = REQUIREMENT.match(requirement.split(";", maxsplit=1)[0])
    if not match:
        return None
    name, specifiers = match.groups()
    floor = FLOOR.search(specifiers)
    return Declaration(
        name=name,
        floor=floor.group(2) if floor else "",
        requirement=requirement.strip(),
        group=group,
        hold=holds.get(name.lower(), ""),
    )


def parse_group(reqs: Sequence[str], group: str, holds: dict[str, str]) -> list[Declaration]:
    parsed = (declare(requirement, group, holds) for requirement in reqs)
    return [declaration for declaration in parsed if declaration is not None]


def load_declarations(pyproject: Path = REPO_ROOT / "pyproject.toml") -> list[Declaration]:
    text = pyproject.read_text(encoding="utf-8")
    data: dict[str, Any] = tomllib.loads(text)
    holds = parse_holds(text)
    declarations = parse_group(data.get("project", {}).get("dependencies", []), "runtime", holds)
    for group, requirements in data.get("dependency-groups", {}).items():
        declarations.extend(parse_group(requirements, f"group:{group}", holds))
    build = data.get("build-system", {}).get("requires", [])
    declarations.extend(parse_group(build, "build-system", holds))
    return declarations


def load_deferrals(path: Path = DEFERRALS_PATH) -> dict[str, tuple[str, str]]:
    """Read reviewed-but-not-now decisions: package -> (reviewed release, reason).

    The reviewed release makes a deferral expire by itself: once PyPI moves past
    it the report asks again, so a deferral cannot become a silenced check.
    """

    try:
        entries = json.loads(path.read_text(encoding="utf-8")).get("deferrals", {})
    except (OSError, ValueError):
        return {}
    deferrals: dict[str, tuple[str, str]] = {}
    for name, entry in entries.items():
        latest, reason = str(entry.get("deferredLatest", "")), str(entry.get("reason", ""))
        if latest and reason:
            deferrals[name.lower()] = (latest, reason)
    return deferrals


def fetch_latest(package: str, timeout: float = 10.0) -> str | None:
    quoted = urllib.parse.quote(package, safe="")
    request = urllib.request.Request(  # noqa: S310 - fixed https host
        f"https://pypi.org/pypi/{quoted}/json",
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    version = payload.get("info", {}).get("version")
    return str(version) if version else None


def status_for(declaration: Declaration, deferrals: dict[str, tuple[str, str]]) -> Status:
    latest = fetch_latest(declaration.name)
    reviewed, reason = deferrals.get(declaration.name.lower(), ("", ""))
    covered = bool(reviewed and latest and not is_newer(latest, reviewed))
    return Status(declaration=declaration, latest=latest, deferred_reason=reason if covered else "")


def render(statuses: Sequence[Status]) -> str:
    lines = [
        "# 依賴新鮮度報告",
        "",
        "| 套件 | 群組 | 宣告 | PyPI 現行版 | 狀態 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for status in statuses:
        declaration = status.declaration
        lines.append(
            f"| `{declaration.name}` | `{declaration.group}` | `{declaration.requirement}` | "
            f"`{status.latest or 'unknown'}` | {status.label} |"
        )
    lines += ["", FOOTER, ""]
    return "\n".join(lines)


def write_github_output(statuses: Sequence[Status]) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"needs_attention={'true' if unresolved(statuses) else 'false'}\n")


def unresolved(statuses: Sequence[Status]) -> bool:
    """Anything a maintainer still has to answer: aged floor, no floor, or no answer."""

    return not statuses or any(
        status.needs_review or status.latest is None or not status.declaration.floor
        for status in statuses
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dependency-freshness-report.md"))
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)

    deferrals = load_deferrals()
    statuses = [status_for(declaration, deferrals) for declaration in load_declarations()]
    report = render(statuses)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    if args.github_output:
        write_github_output(statuses)
    return 1 if args.strict and unresolved(statuses) else 0


if __name__ == "__main__":
    raise SystemExit(main())
