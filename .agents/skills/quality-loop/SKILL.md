---
name: quality-loop
description: Run a bounded AI coding loop in this repository when work can be verified by deterministic quality gates.
---

# Quality Loop

Use this skill only for repeatable repository work with machine-verifiable acceptance criteria. Read `AGENTS.md`, `loop-policy.toml`, and `docs/loop-engineering.md` before starting.

## Contract

1. Write the goal, forbidden actions, acceptance commands, token budget, time limit, and iteration limit before execution.
2. Prove the complete maker → checker → state → stop path with one manual run before enabling any schedule.
3. Work in one isolated worktree. Do not push directly to `main`, auto-merge, copy secrets into a worktree, or reuse credentials without explicit authorization.
4. Keep maker and checker roles independent. Give the checker read-only access where practical; it evaluates the diff and reruns machine evidence instead of trusting the maker's report.
5. Persist only compact state at `loop-state/state.json`: task, current iteration, changed paths, last failure, evidence paths, remaining budget, and next action. Do not store secrets or full transcripts.
6. Run the smallest relevant focused test after a failure. Run Quick once for iteration feedback and Full once for the final candidate; use Mutation only for core-rule or test-strategy changes.
7. Stop immediately on success, exhausted budget, repeated failure, policy violation, or a required human approval boundary.

Authentication, authorization, payments, personal data, deletion, deployment, secrets, and major dependency upgrades always require a human decision at action time. A loop may prepare evidence for those actions but may not approve them itself.
