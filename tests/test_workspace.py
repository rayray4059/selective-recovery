from env.workspace import Workspace


def make_ws(tmp_path):
    src = tmp_path / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg" / "a.py").write_text("x = 1\n")
    return Workspace(tmp_path / "ws", source=src)


def test_init_commits_source(tmp_path):
    ws = make_ws(tmp_path)
    assert ws.files() == ["pkg/a.py"]
    assert ws.head() == ws.init_commit


def test_empty_workspace(tmp_path):
    ws = Workspace(tmp_path / "ws")
    assert ws.files() == [] and ws.head() == ws.init_commit


def test_commit_and_changed_files(tmp_path):
    ws = make_ws(tmp_path)
    (ws.path / "pkg" / "a.py").write_text("x = 2\n")
    c = ws.commit("edit")
    assert c != ws.init_commit
    assert ws.changed_files(ws.init_commit, c) == ["pkg/a.py"]
    assert ws.commit("nothing changed") == c


def test_rollback_restores_and_removes_new_files(tmp_path):
    ws = make_ws(tmp_path)
    (ws.path / "pkg" / "a.py").write_text("x = 2\n")
    (ws.path / "pkg" / "b.py").write_text("y = 1\n")
    ws.commit("edit")
    (ws.path / "junk.txt").write_text("not committed")
    ws.rollback(ws.init_commit)
    assert (ws.path / "pkg" / "a.py").read_text() == "x = 1\n"
    assert ws.files() == ["pkg/a.py"]
