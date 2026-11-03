import shutil
import subprocess
import sys

import pytest

from tasks.schema import TASKS_DIR, load_tasks

TASKS = load_tasks()
SEED = TASKS_DIR / "codebase"


def test_ten_unique_tasks():
    assert len(TASKS) == 10
    assert len({t.id for t in TASKS}) == 10


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_files_exist(task):
    assert (TASKS_DIR / task.expected.hidden_test).is_file()
    assert (TASKS_DIR / "solutions" / task.id).is_dir()
    assert (TASKS_DIR / "wrong" / task.id).is_dir()
    for f in task.target_files:
        assert (SEED / f).is_file()
        assert f in task.allowed.paths


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_facts_only_in_docs(task):
    code = "".join(p.read_text() for p in (SEED / "billing").glob("*.py"))
    roles = [f.role for f in task.facts]
    assert "deciding" in roles and "control" in roles
    for f in task.facts:
        assert f.key in (SEED / f.doc).read_text()
        if f.role == "deciding":
            assert f.key.lower() not in task.instruction.lower()
            assert f.key not in code


def test_visible_tests_pass_on_seed(tmp_path):
    shutil.copytree(SEED, tmp_path / "ws")
    res = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
                         cwd=tmp_path / "ws", capture_output=True, text=True)
    assert res.returncode == 0, res.stdout
