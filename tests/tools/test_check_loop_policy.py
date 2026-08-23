from __future__ import annotations

from pathlib import Path

from tools.check_loop_policy import validate_loop_policy

VALID_POLICY = """\
version = 1

[loop]
enabled = false
max_iterations = 3
max_parallel_worktrees = 1
max_elapsed_minutes = 30
max_tokens_per_run = 100000
require_isolated_workspace = true
require_independent_verifier = true
persist_state = true
stop_on_repeated_failure = true
repeated_failure_limit = 2
allow_auto_merge = false
allow_direct_main_push = false

[verification]
quick_gate = "pwsh -NoProfile -File tools/dev_check.ps1 -Quick"
full_gate = "pwsh -NoProfile -File tools/dev_check.ps1"
mutation_gate = "pwsh -NoProfile -File tools/dev_check.ps1 -Mutation"
require_machine_evidence = true

[state]
path = "loop-state/state.json"
terminal_statuses = [
  "complete",
  "needs_human",
  "budget_exhausted",
  "verification_failed",
]

[connectors]
default_mode = "read-only"
require_explicit_credentials = true

[human_approval]
required_for = [
  "authentication",
  "authorization",
  "payments",
  "personal-data",
  "deletion",
  "deployment",
  "secrets",
  "dependency-major",
]
"""


def write_policy(tmp_path: Path, content: str = VALID_POLICY) -> Path:
    policy = tmp_path / "loop-policy.toml"
    policy.write_text(content, encoding="utf-8")
    return policy


def test_valid_bounded_policy_has_no_violations(tmp_path: Path) -> None:
    assert validate_loop_policy(write_policy(tmp_path)) == []


def test_policy_rejects_unbounded_or_self_approved_loop(tmp_path: Path) -> None:
    unsafe = (
        VALID_POLICY.replace("max_iterations = 3", "max_iterations = 0")
        .replace("require_independent_verifier = true", "require_independent_verifier = false")
        .replace("allow_auto_merge = false", "allow_auto_merge = true")
    )

    violations = validate_loop_policy(write_policy(tmp_path, unsafe))

    assert "loop.max_iterations must be between 1 and 10" in violations
    assert "loop.require_independent_verifier must be true" in violations
    assert "loop.allow_auto_merge must be false" in violations


def test_policy_rejects_enabling_an_unattended_runner(tmp_path: Path) -> None:
    unsafe = VALID_POLICY.replace("enabled = false", "enabled = true")

    violations = validate_loop_policy(write_policy(tmp_path, unsafe))

    assert "loop.enabled must be false" in violations


def test_policy_rejects_boolean_schema_version(tmp_path: Path) -> None:
    unsafe = VALID_POLICY.replace("version = 1", "version = true")

    violations = validate_loop_policy(write_policy(tmp_path, unsafe))

    assert "version must be integer 1" in violations


def test_policy_rejects_state_outside_repository(tmp_path: Path) -> None:
    unsafe = VALID_POLICY.replace('path = "loop-state/state.json"', 'path = "../shared/state.json"')

    violations = validate_loop_policy(write_policy(tmp_path, unsafe))

    assert "state.path must stay inside the repository" in violations


def test_policy_requires_all_high_risk_human_approval_categories(tmp_path: Path) -> None:
    unsafe = VALID_POLICY.replace('  "payments",\n', "")

    violations = validate_loop_policy(write_policy(tmp_path, unsafe))

    assert "human_approval.required_for is missing: payments" in violations


def test_policy_requires_hard_cost_and_failure_stops(tmp_path: Path) -> None:
    unsafe = (
        VALID_POLICY.replace("max_tokens_per_run = 100000", "max_tokens_per_run = 0")
        .replace("stop_on_repeated_failure = true", "stop_on_repeated_failure = false")
        .replace("repeated_failure_limit = 2", "repeated_failure_limit = 3")
    )

    violations = validate_loop_policy(write_policy(tmp_path, unsafe))

    assert "loop.max_tokens_per_run must be positive" in violations
    assert "loop.stop_on_repeated_failure must be true" in violations
    assert "loop.repeated_failure_limit must be less than loop.max_iterations" in violations


def test_policy_rejects_extra_shell_commands_in_verification_gate(tmp_path: Path) -> None:
    unsafe = VALID_POLICY.replace(
        'quick_gate = "pwsh -NoProfile -File tools/dev_check.ps1 -Quick"',
        'quick_gate = "pwsh -NoProfile -File tools/dev_check.ps1 -Quick; Remove-Item secrets"',
    )

    violations = validate_loop_policy(write_policy(tmp_path, unsafe))

    assert "verification.quick_gate must equal the canonical command" in violations
