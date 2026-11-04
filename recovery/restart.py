import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from agents.run import run_task
from env.tools import Environment
from env.workspace import Workspace
from eval.check import compare_irreversible


def restart(task, llm, fault_dir):
    fault_dir = Path(fault_dir)
    run_dir = fault_dir / "restart"
    old = json.loads((fault_dir / "result.json").read_text())
    shutil.copytree(fault_dir / "ws", run_dir / "ws")
    ws = Workspace(run_dir / "ws", existing=True)
    ws.rollback(ws.init_commit)
    env = Environment(ws)
    env.registry = list(old["registry"])
    env.channel = list(old["channel"])

    res = run_task(task, llm, run_dir, env=env)
    new = SimpleNamespace(registry=env.registry[len(old["registry"]):], channel=env.channel[len(old["channel"]):])
    own = compare_irreversible(task, new)
    res["leftover"] = {"publish": old["irreversible"]["extra_publish"],
                       "messages": old["irreversible"]["extra_messages"]}
    res["own_irreversible"] = own
    res["own_passed"] = res["tests_passed"] and not res["collateral"] and not any(own.values())
    (run_dir / "result.json").write_text(json.dumps(res, indent=2, default=str))
    return res
