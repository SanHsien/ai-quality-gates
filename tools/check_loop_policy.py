"""Fail closed when the repository's autonomous-loop policy is unsafe."""

from __future__ import annotations

import argparse
import tomllib
from collections.abc import Sequence
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import cast

HIGH_RISK_APPROVALS = frozenset(
    {
        "authentication",
        "authorization",
        "payments",
        "personal-data",
        "deletion",
        "deployment",
        "secrets",
        "dependency-major",
    }
)
TERMINAL_STATUSES = frozenset(
    {"complete", "needs_human", "budget_exhausted", "verification_failed"}
)
EXPECTED_GATES = {
    "quick_gate": "pwsh -NoProfile -File tools/dev_check.ps1 -Quick",
    "full_gate": "pwsh -NoProfile -File tools/dev_check.ps1",
    "mutation_gate": "pwsh -NoProfile -File tools/dev_check.ps1 -Mutation",
}


def _table(policy: dict[str, object], name: str) -> dict[str, object]:
    value = policy.get(name)
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _is_integer(value: object, minimum: int, maximum: int | None = None) -> bool:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        return False
    return maximum is None or value <= maximum


def _is_repo_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    windows_path = PureWindowsPath(value)
    posix_path = PurePosixPath(value.replace("\\", "/"))
    return (
        not windows_path.is_absolute()
        and not windows_path.drive
        and not posix_path.is_absolute()
        and ".." not in posix_path.parts
    )


def _string_set(value: object) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return set()
    return set(cast(list[str], value))


def _validate_failure_limit(loop: dict[str, object]) -> list[str]:
    failure_limit = loop.get("repeated_failure_limit")
    max_iterations = loop.get("max_iterations")
    if not _is_integer(failure_limit, 1):
        return ["repeated_failure_limit must be positive"]
    if _is_integer(max_iterations, 1) and cast(int, failure_limit) >= cast(int, max_iterations):
        return ["repeated_failure_limit must be less than loop.max_iterations"]
    return []


def _validate_loop(loop: dict[str, object]) -> list[str]:
    checks = (
        (loop.get("enabled") is False, "enabled must be false"),
        (_is_integer(loop.get("max_iterations"), 1, 10), "max_iterations must be between 1 and 10"),
        (
            _is_integer(loop.get("max_parallel_worktrees"), 1, 4),
            "max_parallel_worktrees must be between 1 and 4",
        ),
        (
            _is_integer(loop.get("max_elapsed_minutes"), 1, 120),
            "max_elapsed_minutes must be between 1 and 120",
        ),
        (_is_integer(loop.get("max_tokens_per_run"), 1), "max_tokens_per_run must be positive"),
        (loop.get("require_isolated_workspace") is True, "require_isolated_workspace must be true"),
        (
            loop.get("require_independent_verifier") is True,
            "require_independent_verifier must be true",
        ),
        (loop.get("persist_state") is True, "persist_state must be true"),
        (
            loop.get("stop_on_repeated_failure") is True,
            "stop_on_repeated_failure must be true",
        ),
        (loop.get("allow_auto_merge") is False, "allow_auto_merge must be false"),
        (loop.get("allow_direct_main_push") is False, "allow_direct_main_push must be false"),
    )
    violations = [message for condition, message in checks if not condition]
    violations.extend(_validate_failure_limit(loop))
    return [f"loop.{violation}" for violation in violations]


def _validate_verification(verification: dict[str, object]) -> list[str]:
    violations: list[str] = []
    for key, expected in EXPECTED_GATES.items():
        if verification.get(key) != expected:
            violations.append(f"verification.{key} must equal the canonical command")
    if verification.get("require_machine_evidence") is not True:
        violations.append("verification.require_machine_evidence must be true")
    return violations


def validate_loop_policy(path: Path) -> list[str]:
    """Return every safety-policy violation; malformed or missing input fails closed."""

    try:
        policy = cast(dict[str, object], tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError) as error:
        return [f"policy could not be read: {error}"]

    violations: list[str] = []
    version = policy.get("version")
    if isinstance(version, bool) or version != 1:
        violations.append("version must be integer 1")

    loop = _table(policy, "loop")
    violations.extend(_validate_loop(loop))
    violations.extend(_validate_verification(_table(policy, "verification")))

    state = _table(policy, "state")
    if not _is_repo_relative_path(state.get("path")):
        violations.append("state.path must stay inside the repository")
    missing_statuses = TERMINAL_STATUSES - _string_set(state.get("terminal_statuses"))
    if missing_statuses:
        violations.append(
            f"state.terminal_statuses is missing: {', '.join(sorted(missing_statuses))}"
        )

    connectors = _table(policy, "connectors")
    if connectors.get("default_mode") != "read-only":
        violations.append("connectors.default_mode must be read-only")
    if connectors.get("require_explicit_credentials") is not True:
        violations.append("connectors.require_explicit_credentials must be true")

    approvals = _table(policy, "human_approval")
    missing_approvals = HIGH_RISK_APPROVALS - _string_set(approvals.get("required_for"))
    if missing_approvals:
        violations.append(
            f"human_approval.required_for is missing: {', '.join(sorted(missing_approvals))}"
        )
    return violations


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("policy", nargs="?", type=Path, default=Path("loop-policy.toml"))
    args = parser.parse_args(argv)
    violations = validate_loop_policy(args.policy)
    if violations:
        for violation in violations:
            print(f"LOOP POLICY ERROR: {violation}")
        return 1
    print("LOOP POLICY GREEN: bounded execution and human approval rules verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
