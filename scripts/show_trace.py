import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env.trace import downstream


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir")
    parser.add_argument("--from", dest="start", default="")
    args = parser.parse_args()

    nodes = [json.loads(line) for line in (Path(args.run_dir) / "trace.jsonl").read_text().splitlines()]
    if args.start:
        keep = set(downstream(nodes, args.start))
        print(f"{len(keep)} nodes depend on {args.start}:")
        nodes = [n for n in nodes if n["id"] in keep]
    for n in nodes:
        inputs = ", ".join(n["inputs"]) or "-"
        print(f"{n['id']:<5} {n['kind']:<7} {n['actor']:<11} {n['label']:<40} <- {inputs}")


if __name__ == "__main__":
    main()
