#!/usr/bin/env python3
"""Cursor hook/CLI that caches repository-native quality-gate evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

try:
    from tools.cursor_gate_core import (
        GateResult,
        GateSpec,
        discover_gate,
        fingerprint,
        hook_result,
        run_gate,
    )
    from tools.cursor_gate_git import find_trusted_git
    from tools.cursor_gate_trust import is_trusted_repo
except ModuleNotFoundError:  # installed flat beside this script
    from cursor_gate_core import (  # type: ignore[import-not-found,no-redef]
        GateResult,
        GateSpec,
        discover_gate,
        fingerprint,
        hook_result,
        run_gate,
    )
    from cursor_gate_git import find_trusted_git  # type: ignore[import-not-found,no-redef]
    from cursor_gate_trust import is_trusted_repo  # type: ignore[import-not-found,no-redef]

__all__ = [
    "GateResult",
    "GateSpec",
    "discover_gate",
    "effective_gate",
    "fingerprint",
    "git_state",
    "hook_result",
    "run_gate",
]


def git_state(repo: Path) -> str:
    git = find_trusted_git(repo)
    if not git:
        return "NO_GIT"
    parts = []
    for args in (
        ("rev-parse", "HEAD"),
        ("diff", "--binary", "--no-ext-diff"),
        ("diff", "--cached", "--binary", "--no-ext-diff"),
    ):
        proc = subprocess.run([git, "-C", str(repo), *args], capture_output=True, text=True)
        parts.append(proc.stdout if proc.returncode == 0 else "NO_HEAD")
    untracked = subprocess.run(
        [git, "-C", str(repo), "ls-files", "--others", "--exclude-standard", "-z"],
        capture_output=True,
    )
    for raw in untracked.stdout.decode("utf-8", "surrogateescape").split("\0"):
        if not raw:
            continue
        try:
            target = repo / raw
            stat = target.stat()
            with target.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            parts.append(f"UNTRACKED {raw}\0{stat.st_size}\0{stat.st_mtime_ns}\0{digest}")
        except OSError:
            parts.append(f"UNTRACKED-MISSING {raw}")
    return "\n".join(parts)


def _state_path() -> Path:
    return Path.home() / ".cursor/governance/state.json"


def _load_state(path: Path) -> dict[str, dict[str, object]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_state(path: Path, data: dict[str, dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        tmp = Path(stream.name)
    try:
        os.replace(tmp, path)
    except OSError:
        # Cache persistence is an optimization. A competing Cursor window may
        # replace the same file first; the verified gate result still stands.
        pass
    finally:
        tmp.unlink(missing_ok=True)


def effective_gate(repo: Path, trust_path: Path | None = None) -> GateSpec | None:
    """Return the gate that automatic execution is allowed to run."""
    if not is_trusted_repo(repo, trust_path):
        return GateSpec("git diff --check && git diff --cached --check", "untrusted-baseline", 60)
    return discover_gate(repo)


def evaluate(repo: Path, use_cache: bool = True) -> GateResult:
    spec = effective_gate(repo)
    if spec is None:
        return GateResult("unconfigured", "", "", None, "")
    key = hashlib.sha256(str(repo.resolve()).encode()).hexdigest()
    mark = fingerprint(repo, spec, git_state(repo))
    path = _state_path()
    state = _load_state(path)
    cached = state.get(key, {})
    if use_cache and cached.get("fingerprint") == mark:
        exit_code = cached.get("exit_code")
        return GateResult(
            str(cached.get("status")),
            spec.command,
            spec.source,
            exit_code if isinstance(exit_code, int) else None,
            str(cached.get("output") or ""),
        )
    result = run_gate(repo, spec)
    state[key] = {"repo": str(repo), "fingerprint": mark, **asdict(result)}
    _save_state(path, state)
    return result


def _payload_repo(payload: dict[str, object]) -> Path | None:
    roots = payload.get("workspace_roots") or []
    candidate = payload.get("cwd") or (roots[0] if isinstance(roots, list) and roots else None)
    if not isinstance(candidate, str) or not Path(candidate).is_dir():
        return None
    git = find_trusted_git(Path(candidate))
    if not git:
        return None
    proc = subprocess.run(
        [git, "-C", candidate, "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    return Path(proc.stdout.strip()) if proc.returncode == 0 else None


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", type=Path)
    parser.add_argument("--check", type=Path)
    return parser.parse_args(argv)


def _cli_main(args: argparse.Namespace) -> int | None:
    if args.discover:
        spec = effective_gate(args.discover)
        print(json.dumps(asdict(spec) if spec else {"status": "unconfigured"}, ensure_ascii=False))
        return 0 if spec else 2
    if args.check:
        result = evaluate(args.check, use_cache=False)
        print(json.dumps(asdict(result), ensure_ascii=False))
        return 0 if result.status == "passed" else 2 if result.status == "unconfigured" else 1
    return None


def _hook_main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        payload = {}
    if payload.get("stop_hook_active") is True:
        return 0
    repo = _payload_repo(payload)
    if repo is None:
        return 0
    result = evaluate(repo)
    response = hook_result(result.status, result.output, result.command)
    if response:
        print(json.dumps(response, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    cli_result = _cli_main(_parse_args(argv))
    return _hook_main() if cli_result is None else cli_result


if __name__ == "__main__":
    raise SystemExit(main())
