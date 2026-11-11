"""Supported exact amendments, dry-run by default. Never initializes a ledger.

No operator command is run automatically by web/API startup or deployment.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"apps/api"))
from app.services.shared_allowance import Authority  # noqa: E402


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger",type=Path,required=True)
    operation=parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--request",type=Path,help="Private reviewed JSON: phase, scope_id, authority_id, bindings, expected_sha256, expected_ledger_path, expected_file_identity, operator, authorization_ref, optional acceptance_evidence")
    operation.add_argument("--inspect",action="store_true",help="Read-only audit head and unresolved reservations; never releases capacity")
    operation.add_argument("--stop-request",type=Path,help="Private scope_id/expected_sha256/operator/authorization_ref; closes without refund or reopening")
    parser.add_argument("--apply",action="store_true",help="Apply only after release prerequisites pass; omitted is read-only")
    args=parser.parse_args()
    if args.inspect:
        if args.apply:parser.error("--inspect is read-only")
        print(json.dumps(Authority(args.ledger).inspect(),indent=2));return
    if args.stop_request:
        values=json.loads(args.stop_request.read_text())
        if not args.apply:
            print(json.dumps({"applied":False,"stop_proposal":values},indent=2));return
        print(json.dumps(Authority(args.ledger).stop(**values),indent=2));return
    values=json.loads(args.request.read_text())
    print(json.dumps(Authority(args.ledger).activate(**values,apply=args.apply),indent=2))


if __name__=="__main__":main()
