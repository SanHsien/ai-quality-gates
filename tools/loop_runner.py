"""Bounded AI coding loop runner governed by loop-policy.toml."""

from __future__ import annotations

import argparse
import json
import time
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from tools.check_loop_policy import HIGH_RISK_APPROVALS
from tools.loop_signature import failure_signature
from tools.loop_verifier import run_verifier as _default_verifier
from tools.loop_verifier import run_within_budget


@dataclass
class LoopState:
    task: str
    iteration: int
    phase: str
    status: str
    changed_paths: list[str]
    last_failure: str | None
    evidence_paths: list[str]
    remaining_tokens: int
    next_action: str

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")


@dataclass(frozen=True)
class LoopPolicy:
    enabled: bool
    max_iterations: int
    max_elapsed_minutes: int
    max_tokens_per_run: int
    repeated_failure_limit: int
    state_path: Path
    quick_gate: str
    full_gate: str

    @classmethod
    def load(cls, path: Path) -> LoopPolicy:
        d = tomllib.loads(path.read_text(encoding="utf-8"))
        loop, verif, st = d.get("loop", {}), d.get("verification", {}), d.get("state", {})
        return cls(
            enabled=bool(loop.get("enabled", False)),
            max_iterations=int(loop.get("max_iterations", 3)),
            max_elapsed_minutes=int(loop.get("max_elapsed_minutes", 30)),
            max_tokens_per_run=int(loop.get("max_tokens_per_run", 100000)),
            repeated_failure_limit=int(loop.get("repeated_failure_limit", 2)),
            state_path=Path(str(st.get("path", "loop-state/state.json"))),
            quick_gate=str(
                verif.get("quick_gate", "pwsh -NoProfile -File tools/dev_check.ps1 -Quick")
            ),
            full_gate=str(verif.get("full_gate", "pwsh -NoProfile -File tools/dev_check.ps1")),
        )


def check_human_approval_required(text: str) -> str | None:
    lowered = text.lower()
    return next((r for r in HIGH_RISK_APPROVALS if r in lowered), None)


def _make_state(
    task: str,
    status: str,
    next_action: str,
    remaining_tokens: int,
    last_failure: str | None = None,
) -> LoopState:
    return LoopState(
        task=task,
        iteration=0 if last_failure else 1,
        phase="plan" if last_failure else "discover",
        status=status,
        changed_paths=[],
        last_failure=last_failure,
        evidence_paths=[],
        remaining_tokens=remaining_tokens,
        next_action=next_action,
    )


def _stop_budget(state: LoopState, next_action: str, state_path: Path) -> tuple[str, LoopState]:
    state.status, state.next_action, state.phase = "budget_exhausted", next_action, "verify"
    state.save(state_path)
    return "budget_exhausted", state


def _budget_stop_reason(start_time: float, policy: LoopPolicy, remaining_tokens: int) -> str | None:
    elapsed_over = (time.monotonic() - start_time) / 60.0 > policy.max_elapsed_minutes
    out_of_tokens = remaining_tokens <= 0
    return "stop_time_limit" if elapsed_over else ("stop_token_budget" if out_of_tokens else None)


def _evaluate_failure(
    code: int, output: str, consecutive: int, previous: str | None, limit: int, state: LoopState
) -> tuple[bool, int, str]:
    signature = failure_signature(output, code)
    state.last_failure = output.strip().splitlines()[-1] if output.strip() else f"exit {code}"
    new_consec = consecutive + 1 if previous == signature else 1
    if new_consec >= limit:
        state.status, state.next_action = "verification_failed", "stop_repeated_failure"
        return True, new_consec, signature
    return False, new_consec, signature


def _check_preconditions(task: str, policy: LoopPolicy, allow_disabled: bool) -> LoopState | None:
    if not policy.enabled and not allow_disabled:
        raise ValueError(
            "Loop execution is disabled by policy; set allow_disabled=True or enable in policy"
        )
    risk = check_human_approval_required(task)
    if not risk:
        return None
    state = _make_state(
        task=task,
        status="needs_human",
        next_action="await_human",
        remaining_tokens=policy.max_tokens_per_run,
        last_failure=f"Risk boundary: {risk}",
    )
    state.save(policy.state_path)
    return state


def _run_execution_step(
    execute_step: Callable[[int], list[str]] | None,
    state: LoopState,
    token_cost: int,
) -> None:
    state.phase = "execute"
    if execute_step:
        for path in execute_step(state.iteration):
            if path not in state.changed_paths:
                state.changed_paths.append(path)
    state.remaining_tokens = max(0, state.remaining_tokens - token_cost)


def run_bounded_loop(
    task: str,
    *,
    policy_path: Path = Path("loop-policy.toml"),
    custom_gate: str | None = None,
    execute_step: Callable[[int], list[str]] | None = None,
    verifier: Callable[..., tuple[int, str]] | None = None,
    allow_disabled: bool = True,
    token_cost_per_iter: int = 5000,
) -> tuple[str, LoopState]:
    policy = LoopPolicy.load(policy_path)
    early_state = _check_preconditions(task, policy, allow_disabled)
    if early_state:
        return "needs_human", early_state

    gate_cmd = custom_gate or policy.quick_gate
    run_verifier = verifier or _default_verifier
    state = _make_state(
        task=task,
        status="in_progress",
        next_action="plan",
        remaining_tokens=policy.max_tokens_per_run,
    )
    state.save(policy.state_path)

    start_time, consecutive_failures, previous_signature = time.monotonic(), 0, None

    while state.iteration <= policy.max_iterations:
        stop_reason = _budget_stop_reason(start_time, policy, state.remaining_tokens)
        if stop_reason:
            return _stop_budget(state, stop_reason, policy.state_path)

        _run_execution_step(execute_step, state, token_cost_per_iter)

        state.phase = "verify"
        result = run_within_budget(run_verifier, gate_cmd, start_time, policy.max_elapsed_minutes)
        if result is None:
            return _stop_budget(state, "stop_time_limit", policy.state_path)

        code, output = result
        if code == 0:
            state.status, state.last_failure, state.next_action = "complete", None, "stop"
            state.save(policy.state_path)
            return "complete", state

        stop, consecutive_failures, previous_signature = _evaluate_failure(
            code,
            output,
            consecutive_failures,
            previous_signature,
            policy.repeated_failure_limit,
            state,
        )
        if stop:
            state.save(policy.state_path)
            return "verification_failed", state

        state.iteration += 1
        state.phase = "iterate"
        state.next_action = f"iterate_retry_{state.iteration}"
        state.save(policy.state_path)

    return _stop_budget(state, "stop_iteration_limit", policy.state_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True, help="Bounded task identifier")
    parser.add_argument("--policy", type=Path, default=Path("loop-policy.toml"))
    parser.add_argument("--command", help="Custom verification gate command")
    parser.add_argument("--full", action="store_true", help="Use full gate")
    parser.add_argument("--force", action="store_true", help="Allow running when disabled")
    args = parser.parse_args(argv)

    policy = LoopPolicy.load(args.policy)
    gate = args.command or (policy.full_gate if args.full else policy.quick_gate)
    status, state = run_bounded_loop(
        args.task,
        policy_path=args.policy,
        custom_gate=gate,
        allow_disabled=args.force or policy.enabled,
    )
    summary = f"iter={state.iteration}, status={state.status}, next={state.next_action}"
    print(f"LOOP {status.upper()}: {summary}")
    mapping = {"complete": 0, "needs_human": 2, "budget_exhausted": 3, "verification_failed": 4}
    return mapping.get(status, 1)


if __name__ == "__main__":
    raise SystemExit(main())
