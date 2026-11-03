import json
import random
from pathlib import Path

from faults.inject import ATTACKS
from tasks.schema import load_tasks

FAULTS = ["wrong_fact", "stale_fact", "timeout", "wrong_plan", "malicious_facts", "malicious_plan", "control"]
OUT = Path(__file__).resolve().parent / "schedules" / "phase1.json"


def make_schedule(tasks, seed=291):
    rng = random.Random(seed)
    names = sorted(ATTACKS)
    attacks = [names[i % len(names)] for i in range(len(tasks))]
    rng.shuffle(attacks)
    cells = []
    for t, attack in zip(tasks, attacks):
        for f in FAULTS:
            cells.append({"task": t.id, "fault": f, "attack": attack if f.startswith("malicious") else None})
    return cells


if __name__ == "__main__":
    OUT.write_text(json.dumps(make_schedule(load_tasks()), indent=1) + "\n")
    print("wrote", OUT)
