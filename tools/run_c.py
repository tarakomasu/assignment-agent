"""Development helper: python tools/run_c.py source.c --stdin '10\\n20\\n'."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assignment_agent.runner import run_c

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--stdin", default="", help="Use literal \\n for line breaks")
    parser.add_argument("--work", type=Path, default=Path("work/manual"))
    args = parser.parse_args()
    print(json.dumps(run_c(args.source, args.stdin.replace("\\n", "\n"), args.work), ensure_ascii=False, indent=2))
