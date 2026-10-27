"""Read-only authenticated template export for isolated local acceptance.

No credential, user record, dataset or artifact is included in the export.
Exports retain catalogue runtime metadata locally; never commit or send the raw
export to an LLM. The application builds its own minimized provider context.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

import requests


def credentials(path, base_url):
    fields = dict(re.findall(r"(?m)^([A-Za-z _-]+):\s*(.+)$", path.read_text(encoding="utf-8-sig")))
    if urlsplit(fields.get("URL", "")).hostname != urlsplit(base_url).hostname:
        raise ValueError("Credential-file destination does not match the requested application")
    if not fields.get("Email") or not fields.get("Temporary password"):
        raise ValueError("Expected Email and Temporary password fields in the local credentials file")
    return fields["Email"].strip(), fields["Temporary password"].strip()


def export_metadata(base_url, credentials_file, output, selectors):
    if urlsplit(base_url).scheme != "https":
        raise ValueError("Remote metadata export requires HTTPS")
    email, password = credentials(credentials_file, base_url)
    session = requests.Session()
    session.trust_env = False
    root = base_url.rstrip("/") + "/api"
    def read(path):
        result = session.get(root + path, timeout=20, allow_redirects=False)
        if result.status_code != 200:
            raise RuntimeError(f"Metadata read failed (HTTP {result.status_code}); response body omitted")
        return result.json()
    result = session.post(root + "/auth/login", json={"email":email,"password":password}, timeout=20, allow_redirects=False)
    if result.status_code != 200:
        raise RuntimeError(f"Application authentication failed (HTTP {result.status_code}); credentials and response omitted")
    try:
        all_solutions = read("/solutions")
        selected = {}
        for key, selector in selectors.items():
            matches = [item for item in all_solutions if item["id"] == selector or item["name"] == selector]
            if len(matches) != 1:
                raise ValueError(f"Selector for {key} must match exactly one saved solution; found {len(matches)}")
            selected[key] = read("/solutions/" + quote(matches[0]["id"],safe="") + "/workspace")
        service_ids = {node.get("data",{}).get("service",{}).get("id") or node.get("service_id")
                       for solution in selected.values() for node in solution["nodes"]
                       if node.get("data",{}).get("service",{}).get("id") or node.get("service_id")}
        # The legacy collection GET seeds an empty catalogue. Specific-record
        # reads have no such side effect and fetch only necessary metadata.
        services = [read("/services/"+quote(item,safe="")) for item in sorted(service_ids)]
        if {item["id"] for item in services} != service_ids:
            raise ValueError("Some referenced catalogue records are missing or inaccessible")
        contracts = []
        for item in services:
            contracts.extend(read("/services/" + quote(item["id"],safe="") + "/operation-contracts"))
        # Owner identities and deployment workflow IDs are not needed for a local design copy.
        for item in services:
            item.pop("created_by_user_id", None)
        for item in selected.values():
            item.pop("created_by_user_id", None)
            item["deployments"] = [{key: deployment.get(key) for key in ("id","name","status","created_at","updated_at")}
                                   for deployment in item.get("deployments",[])]
        bundle = {"format":"ai-effect-design-metadata/1", "exported_at":datetime.now(timezone.utc).isoformat(),
                  "source_application":base_url, "solutions":selected,"services":services,"contracts":contracts,
                  "execution_snapshot":None,"reference_note":"Authenticated export of mutable saved designs; no executed-design snapshot is available in the application schema."}
        encoded = json.dumps(bundle, indent=2, ensure_ascii=False).encode("utf-8")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as target:
            target.write(encoded)
        print(json.dumps({"solutions":len(selected),"services":len(services),"contracts":len(contracts),
                          "sha256":hashlib.sha256(encoded).hexdigest(),"output":str(output)}))
    finally:
        session.post(root + "/auth/logout", timeout=10, allow_redirects=False)
        session.close()


def export_dump(dump_path, output, selectors):
    """Read selected metadata, never execute dump DDL or restore auth tables."""
    import pgdumplib  # Optional acceptance-tool dependency, not an API dependency.
    dump=pgdumplib.load(dump_path)
    def records(table):
        entry=dump.lookup_entry("TABLE DATA","public",table)
        if not entry:
            return []
        columns=[value.strip().strip('"') for value in re.search(r"\((.+)\)",entry.copy_stmt).group(1).split(",")]
        result=[]
        for row in dump.table_data("public",table):
            item=dict(zip(columns,row))
            for key in ("nodes","edges","interface_contract","definition","design_metadata"):
                if item.get(key) is not None and isinstance(item[key],str):
                    item[key]=json.loads(item[key])
            result.append(item)
        return result
    selected={}
    all_solutions=records("solutions")
    deployments=records("deployments")
    for key,selector in selectors.items():
        matches=[item for item in all_solutions if item["id"]==selector or item["name"]==selector]
        if len(matches)!=1:
            raise ValueError(f"Selector for {key} must match exactly one exported saved solution")
        item=matches[0]
        item.pop("created_by_user_id",None)
        item["deployments"]=[{k:d.get(k) for k in ("id","name","status","created_at","updated_at")}
                             for d in deployments if d.get("solution_id")==item["id"]]
        selected[key]=item
    ids={node.get("data",{}).get("service",{}).get("id") or node.get("service_id")
         for solution in selected.values() for node in solution["nodes"] if node.get("data",{}).get("service") or node.get("service_id")}
    services=[item for item in records("services") if item["id"] in ids]
    if {item["id"] for item in services}!=ids:
        raise ValueError("The export does not include every referenced catalogue service")
    for item in services:
        item.pop("created_by_user_id",None)
    contracts=[item for item in records("operation_contracts") if item["service_id"] in ids]
    bundle={"format":"ai-effect-design-metadata/1","exported_at":datetime.now(timezone.utc).isoformat(),
        "source_dump":dump_path.name,"source_dump_sha256":hashlib.sha256(dump_path.read_bytes()).hexdigest(),
        "solutions":selected,"services":services,"contracts":contracts,"execution_snapshot":None,
        "reference_note":"Selected real metadata from a historical operator-exported backup. Not verified against the current platform or the exact executed version."}
    encoded=json.dumps(bundle,indent=2,ensure_ascii=False,default=str).encode("utf-8")
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("xb") as target:
        target.write(encoded)
    print(json.dumps({"solutions":len(selected),"services":len(services),"contracts":len(contracts),"sha256":hashlib.sha256(encoded).hexdigest(),"output":str(output)}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url")
    parser.add_argument("--credentials-file",type=Path)
    parser.add_argument("--dump",type=Path,help="Existing operator-exported pg_dump backup; extracts metadata only")
    parser.add_argument("--selectors",type=Path,required=True,help="JSON mapping pilot keys to exact saved IDs or names")
    parser.add_argument("--output",type=Path,required=True,help="New ignored local export path; existing files are never overwritten")
    args=parser.parse_args()
    try:
        selectors=json.loads(args.selectors.read_text())
        if not isinstance(selectors,dict) or not selectors or set(selectors)-{"denmark","dutch","portugal","germany"}:
            raise ValueError("Selectors must map known pilot keys to exact saved names or IDs")
        if args.dump:
            if args.base_url or args.credentials_file:
                raise ValueError("Choose either an existing dump or authenticated application export")
            export_dump(args.dump,args.output,selectors)
        elif args.base_url and args.credentials_file:
            export_metadata(args.base_url,args.credentials_file,args.output,selectors)
        else:
            raise ValueError("Provide --dump, or both --base-url and --credentials-file")
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        # requests exceptions may include URLs; never emit credentials or raw response bodies.
        parser.exit(1, (str(exc) if not isinstance(exc, requests.RequestException) else "Remote metadata request failed; check network access.") + "\n")


if __name__ == "__main__":
    main()
