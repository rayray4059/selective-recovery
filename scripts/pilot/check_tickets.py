"""Sanity-check the pilot tickets: each hidden test must fail on the original codebase and
pass once the ticket's reference solution is applied.

Usage: python3 scripts/pilot/check_tickets.py
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PILOT = Path(__file__).resolve().parent


def run_hidden_test(workspace: Path, test_file: Path) -> bool:
    """Copy the test into the workspace, run it with pytest, and return True if it passes."""
    shutil.copy(test_file, workspace / test_file.name)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", test_file.name],
        cwd=workspace, capture_output=True, text=True,
    )
    return result.returncode == 0


def fresh_workspace(root: Path) -> Path:
    workspace = root / "ws"
    shutil.copytree(PILOT / "codebase", workspace)
    return workspace


def main() -> int:
    tickets = [json.loads(line) for line in (PILOT / "tickets.jsonl").read_text().splitlines() if line]
    ok = True
    for t in tickets:
        test_file = PILOT / t["hidden_test"]
        with tempfile.TemporaryDirectory() as tmp:
            fails_before = not run_hidden_test(fresh_workspace(Path(tmp)), test_file)
        with tempfile.TemporaryDirectory() as tmp:
            workspace = fresh_workspace(Path(tmp))
            shutil.copytree(PILOT / "solutions" / t["id"], workspace, dirs_exist_ok=True)
            passes_after = run_hidden_test(workspace, test_file)
        good = fails_before and passes_after
        ok &= good
        print(f"{'ok  ' if good else 'FAIL'} {t['id']}: fails on original={fails_before}, "
              f"passes with solution={passes_after}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
