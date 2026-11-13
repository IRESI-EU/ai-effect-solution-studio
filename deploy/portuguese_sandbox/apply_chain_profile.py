"""Narrow additive update of the existing sandbox configuration; starts nothing."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

API="sha256:df91c2367e477b607fd8378866b95d976a7b42730ca76662ccfc4250fb5d3ca0"
WEB="sha256:cd8d0324474bab93f3afdce6539d98549e3ea5297e49055b8cfa98fa200a3fe2"
ADAPTER="sha256:1305664435c30980c2649defc1a798fc2262e9ca835f8348ecbe2c43ae89034f"
OBSERVER="sha256:120dcd8bb3a999fa3d67d4955cecf396101a7b3e6d41fae4e3a4c59bda28455f"
WORKER="sha256:985d157eb09413f52fda426d98a567cad7ffe805fdd9aeb2a34447953ed100cf"


def prepare(profile,records):
    profile=profile.resolve();records=records.resolve()
    path=profile/"compose.private.json"
    original=path.read_bytes();c=json.loads(original);services=c["services"]
    if c["name"]!="ai-effect-pt-parameters" or any(n in services for n in ("model-observer","chain-operator","chain-worker")):
        raise ValueError("Existing unmodified standalone sandbox required; do not replace profiles")
    env=services["api"]["environment"]
    if (not env["DATABASE_URL"].endswith("/pt_parameter_sandbox") or env.get("OPENAI_API_KEY")
        or env.get("DESIGN_AI_ENABLED")!="false" or env.get("DESIGN_AI_DEMO_EXECUTION_GRANT_FILE")
        or env.get("DESIGN_AI_ACCEPTANCE_BUDGET_FILE")):
        raise ValueError("Disconnected isolated profile required")
    if services["ml"]["cpus"]!=2 or services["ml"]["mem_limit"]!="3g":
        raise ValueError("Existing resource limits differ")
    if any(not p.startswith("127.0.0.1:") for s in services.values() for p in s.get("ports",[])):
        raise ValueError("Loopback-only existing profile required")
    with (records/"compose-before.private.json").open("xb") as f:f.write(original)
    credential=json.loads((profile/"credentials.json").read_text())
    def bind(name,target):
        return {"type":"bind","source":str(profile/name).replace("\\","/"),"target":target,"read_only":True}
    private=[bind("policy.json","/private/policy.json"),bind("control.token","/private/control.token")]
    services["api"]["image"]=API;services["web"]["image"]=WEB;services["pt-adapter"]["image"]=ADAPTER
    services["pt-adapter"]["environment"]["PT_SANDBOX_MODEL_PROOF_URL"]="http://model-observer:8081"
    services["api"]["environment"].update(PORTUGUESE_EVIDENCE_ROOT="/pt-evidence",PORTUGUESE_MODEL_ROOT="/pt-models",
        PORTUGUESE_EVIDENCE_OWNER_ID=credential["owner_id"])
    services["api"].setdefault("volumes",[]).extend([
        {"type":"volume","source":"adapter","target":"/pt-evidence","read_only":True},
        {"type":"volume","source":"models","target":"/pt-models","read_only":True}])
    services["model-observer"]={"image":OBSERVER,"pull_policy":"never","restart":"no","networks":["private"],
        "mem_limit":"1g","cpus":.5,"read_only":True,"tmpfs":["/tmp:rw,size=64m"],
        "environment":{"PT_SANDBOX_POLICY":"/private/policy.json","PT_SANDBOX_TOKEN_FILE":"/private/control.token"},
        "volumes":private+[{"type":"volume","source":"models","target":"/models","read_only":True}],
        "logging":{"driver":"json-file","options":{"max-size":"5m","max-file":"2"}}}
    services["chain-operator"]=deepcopy(services["pt-adapter"])
    services["chain-operator"].update(profiles=["operator"],entrypoint=["python","-m","experimental.portuguese_parameters.authorization"],
        command=["status","--actor","operator-read-only"],volumes=private+["adapter:/state",
        {"type":"bind","source":str(records/"authorization.private.json").replace("\\","/"),"target":"/review/authorization.json",
            "read_only":True,"bind":{"create_host_path":False}}])
    services["chain-worker"]=deepcopy(services["worker"])
    services["chain-worker"].update(image=WORKER,profiles=["operator"],command=["python","-c","raise SystemExit('Explicit authorized workflow identity required; no daemon startup')"])
    path.write_text(json.dumps(c,indent=2))
    print("Prepared only existing sandbox component pins/read-only evidence mounts and explicit operator roles; no service or workflow started.")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--profile",type=Path,required=True);p.add_argument("--records",type=Path,required=True)
    a=p.parse_args();prepare(a.profile,a.records)
