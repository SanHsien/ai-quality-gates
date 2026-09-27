"""User-local trust policy for automatic Cursor quality-gate execution."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

try:
    from tools.cursor_gate_git import find_trusted_git
except ModuleNotFoundError:  # installed flat beside this module
    from cursor_gate_git import find_trusted_git  # type: ignore[import-not-found,no-redef]

_GITHUB_OWNER = re.compile(
    r"^(?:https?://|ssh://git@|git@)?github\.com(?::|/)([^/]+)/", re.IGNORECASE
)


def _load_trust(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _normal_path(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _origin_owner(repo: Path) -> str:
    git = find_trusted_git(repo)
    if not git:
        return ""
    proc = subprocess.run(
        [git, "-C", str(repo), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    match = _GITHUB_OWNER.search(proc.stdout.strip())
    return match.group(1).casefold() if match else ""


def _path_is_trusted(repo: Path, data: dict[str, object]) -> bool:
    trusted_paths = data.get("trusted_repositories", [])
    if not isinstance(trusted_paths, list):
        return False
    target = _normal_path(repo)
    return any(
        isinstance(item, str) and _normal_path(Path(item)) == target for item in trusted_paths
    )


def _owner_is_trusted(repo: Path, data: dict[str, object]) -> bool:
    trusted_owners = data.get("trusted_github_owners", [])
    if not isinstance(trusted_owners, list):
        return False
    owner = _origin_owner(repo)
    return bool(owner) and owner in {
        item.casefold() for item in trusted_owners if isinstance(item, str) and item.strip()
    }


def is_trusted_repo(repo: Path, trust_path: Path | None = None) -> bool:
    """Return whether user-local policy authorizes native commands for repo."""
    path = trust_path or Path.home() / ".cursor/governance/trust.json"
    data = _load_trust(path)
    return _path_is_trusted(repo, data) or _owner_is_trusted(repo, data)
