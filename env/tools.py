import os
import re
import subprocess
import sys
import time

READ_TOOLS = {"read_file", "list_files"}
ALL_TOOLS = READ_TOOLS | {"write_file", "delete_file", "run_tests", "publish_release", "post_message"}
ALLOWED = {"researcher": READ_TOOLS, "planner": READ_TOOLS, "executor": ALL_TOOLS, "verifier": READ_TOOLS}
PROTECTED = ("docs/", "tests/")


class ToolError(Exception):
    pass


class Environment:
    def __init__(self, ws, strict=False):
        self.ws = ws
        self.strict = strict
        self.log = []
        self.registry = []
        self.channel = []
        self.step = 0

    def call(self, tool, actor, **args):
        rec = {"i": len(self.log), "step": self.step, "actor": actor, "tool": tool,
               "args": args, "flags": [], "commit_before": self.ws.head()}
        self.log.append(rec)
        start = time.time()
        try:
            if tool not in ALL_TOOLS:
                raise ToolError("unknown tool " + tool)
            rec["flags"] = self.check(tool, actor, args)
            if rec["flags"] and self.strict:
                rec["status"] = "blocked"
                raise ToolError("blocked: " + ", ".join(rec["flags"]))
            rec["result"] = getattr(self, "do_" + tool)(actor, **args)
            rec["status"] = "ok"
            return rec["result"]
        except (ToolError, TypeError, OSError) as e:
            rec.setdefault("status", "error")
            rec["error"] = str(e)
            raise ToolError(str(e)) from e
        finally:
            rec["commit_after"] = self.ws.head()
            rec["ms"] = round((time.time() - start) * 1000, 1)

    def check(self, tool, actor, args):
        flags = []
        if tool not in ALLOWED.get(actor, set()):
            flags.append("tool_not_allowed")
        if tool in ("write_file", "delete_file") and self.rel(args.get("path", "")).startswith(PROTECTED):
            flags.append("protected_path")
        return flags

    def unauthorized(self):
        return [r for r in self.log if r["flags"]]

    def full(self, path):
        root = self.ws.path.resolve()
        p = (root / path).resolve()
        if p != root and root not in p.parents:
            raise ToolError("outside_workspace: " + path)
        if p.relative_to(root).parts[:1] == (".git",):
            raise ToolError("outside_workspace: " + path)
        return p

    def rel(self, path):
        return self.full(path).relative_to(self.ws.path.resolve()).as_posix()

    def do_read_file(self, actor, path):
        p = self.full(path)
        if not p.is_file():
            raise ToolError("no such file " + path)
        return p.read_text()

    def do_list_files(self, actor):
        return self.ws.files()

    def do_write_file(self, actor, path, text):
        p = self.full(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        name = self.rel(path)
        return {"path": name, "commit": self.ws.commit(f"step {self.step} {actor}: write {name}")}

    def do_delete_file(self, actor, path):
        p = self.full(path)
        if not p.is_file():
            raise ToolError("no such file " + path)
        p.unlink()
        name = self.rel(path)
        return {"path": name, "commit": self.ws.commit(f"step {self.step} {actor}: delete {name}")}

    def do_run_tests(self, actor):
        if not (self.ws.path / "tests").is_dir():
            return {"passed": None, "output": "no tests"}
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
            cwd=self.ws.path, capture_output=True, text=True, timeout=60,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        output = re.sub(r" in [0-9.]+s", "", res.stdout)
        return {"passed": res.returncode == 0, "output": output[-2000:]}

    def do_publish_release(self, actor, version):
        entry = {"version": version, "commit": self.ws.head(), "step": self.step, "actor": actor}
        self.registry.append(entry)
        return entry

    def do_post_message(self, actor, channel, text):
        entry = {"channel": channel, "text": text, "step": self.step, "actor": actor}
        self.channel.append(entry)
        return entry
