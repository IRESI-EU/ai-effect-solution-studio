import argparse
import json

from app.db import SessionLocal
from app.services.package_solution_repair import repair_legacy_package_solution


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate or repair one untouched legacy package-imported draft.")
    parser.add_argument("solution_id")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    with SessionLocal() as db:
        result = repair_legacy_package_solution(db, args.solution_id, apply=args.apply)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
