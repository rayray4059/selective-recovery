import shutil
import subprocess
from pathlib import Path


class Workspace:
    def __init__(self, path, source=None, existing=False):
        self.path = Path(path)
        if existing:
            self.init_commit = self.git("rev-list", "--max-parents=0", "HEAD")
            return
        if source:
            shutil.copytree(source, self.path)
        else:
            self.path.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q")
        (self.path / ".git" / "info" / "exclude").write_text("__pycache__/\n.pytest_cache/\n")
        self.init_commit = None
        self.init_commit = self.commit("init")

    def git(self, *args):
        cmd = ["git", "-c", "user.name=agent", "-c", "user.email=agent@local", *args]
        out = subprocess.run(cmd, cwd=self.path, capture_output=True, text=True, check=True)
        return out.stdout.strip()

    def head(self):
        return self.git("rev-parse", "HEAD")

    def commit(self, msg):
        self.git("add", "-A")
        if self.init_commit and self.git("status", "--porcelain") == "":
            return self.head()
        self.git("commit", "-q", "--allow-empty", "-m", msg)
        return self.head()

    def rollback(self, sha):
        self.git("reset", "-q", "--hard", sha)
        self.git("clean", "-q", "-fd")

    def changed_files(self, a, b="HEAD"):
        out = self.git("diff", "--name-only", a, b)
        return out.splitlines() if out else []

    def changed_since(self, sha):
        out = self.git("diff", "--name-only", sha) + "\n" + self.git("ls-files", "--others", "--exclude-standard")
        return sorted(set(x for x in out.splitlines() if x))

    def files(self):
        out = self.git("ls-files", "--cached", "--others", "--exclude-standard")
        return sorted(out.splitlines()) if out else []
