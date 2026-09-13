"""Exercise the packaged command boundary with one deterministic smoke entity."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    command = [
        sys.executable,
        "-m",
        "quality_gate_demo",
        "quote",
        "--input",
        str(repo_root / "examples" / "order.json"),
    ]
    completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        print(completed.stderr, file=sys.stderr)
        return 1
    result = json.loads(completed.stdout)
    if result.get("total_cents") != 5_130:
        print(f"unexpected smoke result: {result}", file=sys.stderr)
        return 1
    print("QA SMOKE GREEN: example order total=5130")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
