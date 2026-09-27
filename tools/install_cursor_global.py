#!/usr/bin/env python3
"""Install ai-quality-gates as an idempotent global Cursor adapter."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROUTER_SOURCE = REPO / "tools/cursor_gate_router.py"
CORE_SOURCE = REPO / "tools/cursor_gate_core.py"
BASELINE_SOURCE = REPO / "tools/cursor_gate_baseline.py"
GIT_SOURCE = REPO / "tools/cursor_gate_git.py"
TRUST_SOURCE = REPO / "tools/cursor_gate_trust.py"
RULE_SOURCE = REPO / "integrations/cursor/ai-quality-governance.mdc"
SKILL_SOURCE = REPO / ".agents/skills/quality-loop"
MANAGED_SCRIPT = "ai_quality_gate.py"


@dataclass(frozen=True)
class InstallReport:
    changed: bool
    actions: tuple[str, ...]
    backup: str = ""


def managed_command(cursor_dir: Path) -> str:
    return f'python "{cursor_dir / "hooks" / MANAGED_SCRIPT}"'


def merge_hooks(data: dict[str, object], command: str) -> tuple[dict[str, object], bool]:
    merged = json.loads(json.dumps(data)) if data else {"version": 1, "hooks": {}}
    merged["version"] = 1
    hooks = merged.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        merged["hooks"] = hooks
    entries = hooks.setdefault("stop", [])
    if not isinstance(entries, list):
        entries = []
    kept = [
        item
        for item in entries
        if not (
            isinstance(item, dict)
            and MANAGED_SCRIPT.lower() in str(item.get("command", "")).lower()
        )
    ]
    kept.append({"command": command, "timeout": 240})
    hooks["stop"] = kept
    return merged, merged != data


def _same_file(source: Path, target: Path) -> bool:
    return target.is_file() and source.read_bytes() == target.read_bytes()


def _planned_files(cursor_dir: Path) -> tuple[tuple[Path, Path], ...]:
    pairs = [
        (ROUTER_SOURCE, cursor_dir / "hooks" / MANAGED_SCRIPT),
        (CORE_SOURCE, cursor_dir / "hooks" / CORE_SOURCE.name),
        (BASELINE_SOURCE, cursor_dir / "hooks" / BASELINE_SOURCE.name),
        (GIT_SOURCE, cursor_dir / "hooks" / GIT_SOURCE.name),
        (TRUST_SOURCE, cursor_dir / "hooks" / TRUST_SOURCE.name),
        (RULE_SOURCE, cursor_dir / "rules" / RULE_SOURCE.name),
    ]
    pairs.extend(
        (source, cursor_dir / "skills/quality-loop" / source.relative_to(SKILL_SOURCE))
        for source in SKILL_SOURCE.rglob("*")
        if source.is_file()
    )
    return tuple(pairs)


def _load_hooks(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"version": 1, "hooks": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _atomic_json(path: Path, data: dict[str, object]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _backup_file(cursor_dir: Path, source: Path) -> str:
    backup_dir = cursor_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{source.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(source, backup_path)
    return str(backup_path)


def _copy_files(file_changes: list[tuple[Path, Path]]) -> None:
    for source, target in file_changes:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _install_actions(
    file_changes: list[tuple[Path, Path]], hooks_changed: bool, hooks_json: Path
) -> list[str]:
    actions = [f"copy {source} -> {target}" for source, target in file_changes]
    if hooks_changed:
        actions.append(f"merge managed stop hook into {hooks_json}")
    return actions


def _merged_trust(path: Path, owner: str | None) -> tuple[dict[str, object], bool]:
    if not owner:
        return {}, False
    current = _load_hooks(path) if path.exists() else {"version": 1}
    merged = json.loads(json.dumps(current))
    owners = merged.get("trusted_github_owners", [])
    owners = list(owners) if isinstance(owners, list) else []
    if owner.casefold() not in {str(item).casefold() for item in owners}:
        owners.append(owner)
    merged["trusted_github_owners"] = owners
    return merged, merged != current


def _changed_files(cursor_dir: Path) -> list[tuple[Path, Path]]:
    return [
        (source, target)
        for source, target in _planned_files(cursor_dir)
        if not _same_file(source, target)
    ]


def _backup_changes(
    cursor_dir: Path,
    hooks_json: Path,
    hooks_changed: bool,
    trust_path: Path,
    trust_changed: bool,
) -> list[str]:
    paths = []
    if hooks_changed and hooks_json.exists():
        paths.append(_backup_file(cursor_dir, hooks_json))
    if trust_changed and trust_path.exists():
        paths.append(_backup_file(cursor_dir, trust_path))
    return paths


def _write_json_changes(
    hooks_json: Path,
    hooks: dict[str, object],
    hooks_changed: bool,
    trust_path: Path,
    trust: dict[str, object],
    trust_changed: bool,
) -> None:
    if hooks_changed:
        hooks_json.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(hooks_json, hooks)
    if trust_changed:
        trust_path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(trust_path, trust)


def _snapshot(paths: list[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.is_file() else None for path in paths}


def _restore(snapshot: dict[Path, bytes | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def install(
    cursor_dir: Path | None = None,
    dry_run: bool = False,
    trusted_github_owner: str | None = None,
) -> InstallReport:
    cursor_dir = (cursor_dir or Path.home() / ".cursor").resolve()
    hooks_json = cursor_dir / "hooks.json"
    current = _load_hooks(hooks_json)
    merged, hooks_changed = merge_hooks(current, managed_command(cursor_dir))
    trust_path = cursor_dir / "governance" / "trust.json"
    trust, trust_changed = _merged_trust(trust_path, trusted_github_owner)
    file_changes = _changed_files(cursor_dir)
    actions = _install_actions(file_changes, hooks_changed, hooks_json)
    if trust_changed:
        actions.append(f"trust GitHub owner {trusted_github_owner} in {trust_path}")
    changed = bool(actions)
    if dry_run or not changed:
        return InstallReport(changed, tuple(actions))

    backups = _backup_changes(cursor_dir, hooks_json, hooks_changed, trust_path, trust_changed)
    changed_targets = [target for _source, target in file_changes]
    changed_targets.extend(
        path
        for path, needed in ((hooks_json, hooks_changed), (trust_path, trust_changed))
        if needed
    )
    snapshot = _snapshot(changed_targets)
    try:
        _copy_files(file_changes)
        _write_json_changes(hooks_json, merged, hooks_changed, trust_path, trust, trust_changed)
    except Exception:
        _restore(snapshot)
        raise
    return InstallReport(True, tuple(actions), "; ".join(backups))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cursor-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--trusted-github-owner")
    args = parser.parse_args(argv)
    report = install(args.cursor_dir, args.dry_run, args.trusted_github_owner)
    print("mode:", "dry-run" if args.dry_run else "install")
    for action in report.actions:
        print("-", action)
    print("changed:", str(report.changed).lower())
    if report.backup:
        print("backup:", report.backup)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
