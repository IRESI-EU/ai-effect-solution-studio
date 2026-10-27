"""Local-only operator command. Preview is read-only; --apply commits policy+audit."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps/api"))
from app.services.design_ai_allowance_operator import amend_calls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--expected-ledger-sha256", required=True)
    parser.add_argument("--expected-limit", type=int, required=True)
    parser.add_argument("--new-limit", type=int, required=True)
    parser.add_argument("--amendment-id", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--authorization-ref", required=True)
    parser.add_argument("--task-checkpoint", required=True)
    parser.add_argument("--apply", action="store_true")
    args = vars(parser.parse_args())
    args["path"] = args.pop("ledger")
    args["task_limit_file"] = args.pop("task_checkpoint")
    args["dry_run"] = not args.pop("apply")
    print(json.dumps(amend_calls(**args), indent=2))


if __name__ == "__main__":
    main()
