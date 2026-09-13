"""Resolve Git from absolute PATH entries outside an untrusted repository."""

from __future__ import annotations

import os
from pathlib import Path


def _git_names() -> tuple[str, ...]:
    if os.name != "nt":
        return ("git",)
    suffixes = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(os.pathsep)
    return tuple(f"git{suffix.lower()}" for suffix in suffixes if suffix)


def _safe_directories(repo: Path) -> tuple[Path, ...]:
    safe = []
    for raw_directory in os.environ.get("PATH", "").split(os.pathsep):
        directory = Path(raw_directory.strip('"'))
        if not directory.is_absolute():
            continue
        resolved = directory.resolve()
        if resolved != repo and repo not in resolved.parents:
            safe.append(resolved)
    return tuple(safe)


def _git_in(directory: Path) -> str | None:
    for name in _git_names():
        candidate = directory / name
        if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
            return str(candidate)
    return None


def find_trusted_git(repo: Path) -> str | None:
    for directory in _safe_directories(repo.resolve()):
        if candidate := _git_in(directory):
            return candidate
    return None
