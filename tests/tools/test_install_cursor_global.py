from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.install_cursor_global as installer
from tools.install_cursor_global import install, managed_command, merge_hooks


def test_merge_hooks_preserves_existing_entries_and_is_idempotent(tmp_path: Path) -> None:
    command = managed_command(tmp_path)
    existing = {
        "version": 1,
        "hooks": {"stop": [{"command": "python existing.py", "timeout": 10}]},
    }

    once, changed_once = merge_hooks(existing, command)
    twice, changed_twice = merge_hooks(once, command)

    assert changed_once
    assert not changed_twice
    assert once == twice
    assert once["hooks"]["stop"] == [
        {"command": "python existing.py", "timeout": 10},
        {"command": command, "timeout": 240},
    ]


def test_merge_hooks_replaces_stale_managed_registration(tmp_path: Path) -> None:
    command = managed_command(tmp_path)
    existing = {
        "version": 1,
        "hooks": {
            "stop": [
                {
                    "command": 'python "C:\\old\\ai_quality_gate.py"',
                    "timeout": 30,
                }
            ]
        },
    }

    merged, changed = merge_hooks(existing, command)

    assert changed
    assert merged["hooks"]["stop"] == [{"command": command, "timeout": 240}]


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    cursor_dir = tmp_path / ".cursor"

    report = install(cursor_dir, dry_run=True)

    assert report.changed
    assert not cursor_dir.exists()


def test_install_copies_router_rule_skill_and_merges_json(tmp_path: Path) -> None:
    cursor_dir = tmp_path / ".cursor"
    cursor_dir.mkdir()
    (cursor_dir / "hooks.json").write_text(
        json.dumps(
            {"version": 1, "hooks": {"stop": [{"command": "python existing.py", "timeout": 10}]}},
            indent=2,
        ),
        encoding="utf-8",
    )

    report = install(cursor_dir, trusted_github_owner="SanHsien")

    data = json.loads((cursor_dir / "hooks.json").read_text(encoding="utf-8"))
    assert report.changed
    assert (cursor_dir / "hooks" / "ai_quality_gate.py").is_file()
    assert (cursor_dir / "hooks" / "cursor_gate_core.py").is_file()
    assert (cursor_dir / "hooks" / "cursor_gate_baseline.py").is_file()
    assert (cursor_dir / "hooks" / "cursor_gate_git.py").is_file()
    assert (cursor_dir / "hooks" / "cursor_gate_trust.py").is_file()
    assert (cursor_dir / "rules" / "ai-quality-governance.mdc").is_file()
    assert (cursor_dir / "skills" / "quality-loop" / "SKILL.md").is_file()
    assert data["hooks"]["stop"][-1] == {
        "command": managed_command(cursor_dir),
        "timeout": 240,
    }
    assert list((cursor_dir / "backups").glob("hooks.json.bak-*"))
    trust = json.loads((cursor_dir / "governance" / "trust.json").read_text(encoding="utf-8"))
    assert trust == {"version": 1, "trusted_github_owners": ["SanHsien"]}


def test_second_install_is_idempotent(tmp_path: Path) -> None:
    cursor_dir = tmp_path / ".cursor"

    first = install(cursor_dir)
    second = install(cursor_dir)

    assert first.changed
    assert not second.changed


def test_install_merges_owner_without_dropping_explicit_paths(tmp_path: Path) -> None:
    cursor_dir = tmp_path / ".cursor"
    trust_path = cursor_dir / "governance" / "trust.json"
    trust_path.parent.mkdir(parents=True)
    trust_path.write_text(
        json.dumps({"version": 1, "trusted_repositories": ["C:/safe/repo"]}),
        encoding="utf-8",
    )

    install(cursor_dir, trusted_github_owner="SanHsien")

    trust = json.loads(trust_path.read_text(encoding="utf-8"))
    assert trust["trusted_repositories"] == ["C:/safe/repo"]
    assert trust["trusted_github_owners"] == ["SanHsien"]
    assert list((cursor_dir / "backups").glob("trust.json.bak-*"))


def test_install_rolls_back_managed_files_when_config_write_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cursor_dir = tmp_path / ".cursor"
    router = cursor_dir / "hooks" / "ai_quality_gate.py"
    router.parent.mkdir(parents=True)
    router.write_text("old router\n", encoding="utf-8")

    def fail_write(*_args: object) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr(installer, "_atomic_json", fail_write)

    with pytest.raises(OSError, match="simulated write failure"):
        install(cursor_dir, trusted_github_owner="SanHsien")

    assert router.read_text(encoding="utf-8") == "old router\n"
    assert not (cursor_dir / "hooks.json").exists()
    assert not (cursor_dir / "governance" / "trust.json").exists()
