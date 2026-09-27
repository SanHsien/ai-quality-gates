"""Safe baseline that never resolves executables from an untrusted repository."""

from __future__ import annotations

import subprocess
from pathlib import Path

try:
    from tools.cursor_gate_git import find_trusted_git
except ModuleNotFoundError:  # installed flat beside this module
    from cursor_gate_git import find_trusted_git  # type: ignore[import-not-found,no-redef]


def _text(value: bytes | str | None) -> str:
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value or ""


def _run_git(git: str, repo: Path, args: tuple[str, ...], timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            [git, *args],
            cwd=repo,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        output = _text(exc.stdout) + _text(exc.stderr)
        return 124, output, "baseline timed out"
    except OSError as exc:
        return 126, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def run_baseline(repo: Path, timeout: int) -> tuple[int, str, str]:
    git = find_trusted_git(repo)
    if not git:
        return 126, "", "trusted git executable not found on absolute PATH entries"
    working = _run_git(git, repo, ("diff", "--check"), timeout)
    if working[0] != 0:
        return working
    staged = _run_git(git, repo, ("diff", "--cached", "--check"), timeout)
    return staged[0], working[1] + staged[1], working[2] + staged[2]
