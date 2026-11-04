import json
import sys
from pathlib import Path

from fakes import DONE, FakeLLM
from tasks.schema import TASKS_DIR

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import run_faults

FIX = (TASKS_DIR / "solutions" / "t03_min_charge" / "billing" / "payments.py").read_text()
FACTS = json.dumps({"facts": [{"fact": "The minimum charge is 50 cents (amount_too_small).", "source": "docs/policy.md"}]})
PLAN = json.dumps({"steps": [{"file": "billing/payments.py", "function": "charge", "new_signature": "x", "change": "y"}]})
WRITE = '{"tool": "write_file", "path": "billing/payments.py"}\n```python\n' + FIX + "```"


class FlakyLLM(FakeLLM):
    def __init__(self, fail_on):
        super().__init__([])
        self.n = 0
        self.fail_on = fail_on
        self.client = self
        self.models = self

    def list(self):
        return []

    def chat(self, messages, schema=None):
        self.n += 1
        if self.n in self.fail_on:
            raise ConnectionError("server went away")
        system = messages[0]["content"]
        if "researcher" in system[:40]:
            self.replies = [FACTS]
        elif "planner" in system[:40]:
            self.replies = [PLAN]
        elif "executor" in system[:40] and "write_file" not in str(messages[1:]):
            self.replies = [WRITE]
        return super().chat(messages, schema)


def run(monkeypatch, out, llm):
    monkeypatch.setattr(run_faults, "LLM", lambda url: llm)
    monkeypatch.setattr(run_faults, "server_info", lambda: {"command": "fake"})
    monkeypatch.setattr(sys, "argv", ["run_faults.py", "--ids", "t03_min_charge", "--faults", "wrong_fact,control",
                                      "--restart", "--from", str(out)])
    run_faults.main()
    return [json.loads(line) for line in (out.parent / f"{out.name}_summary.jsonl").read_text().splitlines()]


def test_error_is_logged_and_batch_resumes(tmp_path, monkeypatch):
    out = tmp_path / "batch"
    rows = run(monkeypatch, out, FlakyLLM(fail_on={6}))
    errors = [r for r in rows if "error" in r]
    assert len(errors) == 1 and "server went away" in errors[0]["error"]
    assert (out / "errors.log").exists() and not (out / "t03_min_charge" / errors[0]["fault"] / "result.json").exists()
    assert (out / "t03_min_charge" / "control" / "result.json").exists()

    rows = run(monkeypatch, out, FlakyLLM(fail_on=set()))
    ok = [r for r in rows if "error" not in r]
    assert sorted(r["fault"] for r in ok) == ["control", "no_docs", "wrong_fact"]
    restarts = (tmp_path / "batch_restart.jsonl").read_text().splitlines()
    assert len(restarts) == 2
    info = json.loads((out / "batch.json").read_text())
    assert len(info) == 2 and info[0]["git_commit"] and info[0]["server"] == {"command": "fake"}
