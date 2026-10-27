"""Export/check the canonical portable validator into an explicit WP3 checkout."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--wp3-root", type=Path, required=True)
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
target = args.wp3_root.resolve() / "orchestrator"
if not (target / "src/services").is_dir():
    parser.error("Expected an existing WP3 checkout with orchestrator/src/services")
source = root / "apps/api/app/services/parameter_values.py"
data = source.read_bytes()
provenance = {"owner": "Solution Studio Operation Contract Registry", "source": "apps/api/app/services/parameter_values.py",
    "validator_version": "1.0", "sha256": hashlib.sha256(data).hexdigest(),
    "note": "Exact vendored release artifact; regenerate with deploy/aie18/sync_wp3_contract.py, do not edit independently"}
destination = target / "src/services/parameter_contract.py"
record = target / "parameter_contract_provenance.json"
if args.check:
    if destination.read_bytes() != data or json.loads(record.read_text(encoding="utf-8")) != provenance:
        raise SystemExit("Validator export/provenance drift")
    print("Validator bytes and provenance match")
else:
    destination.write_bytes(data)
    record.write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    print("Exported canonical validator and provenance")
