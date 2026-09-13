from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.cursor_gate_trust import is_trusted_repo


def _repo_with_origin(tmp_path: Path, url: str) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin", url], check=True)
    return tmp_path


def test_trusted_github_owner_allows_native_gate(tmp_path: Path) -> None:
    repo = _repo_with_origin(tmp_path / "repo", "https://github.com/SanHsien/demo.git")
    trust = tmp_path / "trust.json"
    trust.write_text(
        json.dumps({"version": 1, "trusted_github_owners": ["SanHsien"]}),
        encoding="utf-8",
    )

    assert is_trusted_repo(repo, trust)


def test_external_owner_is_not_trusted(tmp_path: Path) -> None:
    repo = _repo_with_origin(tmp_path / "repo", "git@github.com:external/demo.git")
    trust = tmp_path / "trust.json"
    trust.write_text(
        json.dumps({"version": 1, "trusted_github_owners": ["SanHsien"]}),
        encoding="utf-8",
    )

    assert not is_trusted_repo(repo, trust)


def test_lookalike_github_domain_is_not_trusted(tmp_path: Path) -> None:
    repo = _repo_with_origin(tmp_path / "repo", "git@evilgithub.com:SanHsien/pwn.git")
    trust = tmp_path / "trust.json"
    trust.write_text(
        json.dumps({"version": 1, "trusted_github_owners": ["SanHsien"]}),
        encoding="utf-8",
    )

    assert not is_trusted_repo(repo, trust)


def test_repo_cannot_self_authorize_without_user_trust(tmp_path: Path) -> None:
    repo = _repo_with_origin(tmp_path / "repo", "https://github.com/external/demo.git")
    (repo / ".ai-quality-gates.json").write_text(
        json.dumps({"enabled": True, "quick": "python dangerous.py"}),
        encoding="utf-8",
    )

    assert not is_trusted_repo(repo, tmp_path / "missing-trust.json")


def test_explicit_user_local_repository_path_is_trusted(tmp_path: Path) -> None:
    repo = _repo_with_origin(tmp_path / "repo", "https://example.invalid/demo.git")
    trust = tmp_path / "trust.json"
    trust.write_text(
        json.dumps({"version": 1, "trusted_repositories": [str(repo)]}),
        encoding="utf-8",
    )

    assert is_trusted_repo(repo, trust)
