"""Existing-profile activation only. Never creates/binds/closes authority or submits.

check: retained-profile drift + real read-only probe, no journal initialization.
activate: requires separately created exact prepared authority; one standby only.
Closure/rollback remain explicit supported operator and scoped Compose steps.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sqlite3
import re
import time
import requests

PROJECT = "ai-effect-pt-parameters"


def activate(driver, *, monotonic=time.monotonic, sleep=time.sleep):
    """The sole activation order. Test doubles exercise this same orchestration."""
    driver.verify_authority()
    driver.configure_adapter()  # API still disabled; original config backed up.
    driver.up("pt-adapter")
    deadline = monotonic() + 30
    while True:
        remaining=deadline-monotonic()
        if remaining<=0:
            raise ValueError("Adapter stabilization deadline expired; API admission stays disabled")
        try:
            driver.probe(timeout=min(20,remaining))
            if monotonic()>=deadline:
                raise ValueError("Adapter stabilization deadline expired; API admission stays disabled")
            break
        except ConnectionError:
            if monotonic() >= deadline:
                raise ValueError("Adapter stabilization deadline expired; API admission stays disabled")
            sleep(min(1, max(0, deadline-monotonic())))
    adapter = driver.identity("pt-adapter")
    admission_enabled=False
    try:
        driver.start_worker()  # Exclusive durable marker; never a replacement.
        driver.wait_lease()
        driver.enable_api()
        admission_enabled=True
        driver.up("api")  # Never adapter/web/database or workers.
        if driver.identity("pt-adapter") != adapter:
            raise ValueError("Adapter identity changed during API-only activation")
        driver.wait_lease()  # Restarting API must not interrupt the processor.
    except Exception:
        if admission_enabled:
            driver.disable_api()
            driver.up("api")
        driver.stop_if_unbound()
        raise


class DockerProfile:
    def __init__(self, profile, proposal, records, authority=None, worker_name=None):
        self.profile, self.records = profile.resolve(), records.resolve()
        self.path = self.profile / "compose.private.json"
        self.original = self.path.read_bytes()
        self.config = json.loads(self.original)
        self.proposal = json.loads(proposal.read_text())
        self.authority = json.loads(authority.read_text()) if authority else None
        self.worker_name = worker_name
        self.D = ["docker", "--context", "desktop-linux"]
        self.C = self.D + ["compose", "-f", str(self.path)]
        self.records.mkdir(parents=True, exist_ok=False)
        (self.records/"compose-before.private.json").write_bytes(self.original)
        self.check()

    def command(self, args, *, data=None, timeout=45):
        result = subprocess.run(args, input=data, capture_output=True, text=True, timeout=timeout)
        if result.returncode:
            # Private errors can contain environment/connection strings.
            (self.records/"last-error.private.log").write_text(result.stdout+result.stderr)
            raise ValueError("Operator command failed; inspect last-error.private.log; never repeat a consumed worker start")
        return result.stdout

    def inspect(self, role):
        return json.loads(self.command(self.D+["inspect", PROJECT+"-"+role+"-1"]))[0]

    def journal(self):
        code = "import json,sqlite3;d=sqlite3.connect('file:/state/journal.sqlite3?mode=ro',uri=True);d.row_factory=sqlite3.Row;ts=['jobs','authorizations','authorized_jobs'];ts+=['supervised_processors'] if d.execute(\"select 1 from sqlite_master where name='supervised_processors'\").fetchone() else [];print(json.dumps({t:[dict(r) for r in d.execute('select * from '+t)] for t in ts}))"
        return json.loads(self.command(self.C+["exec","-T","pt-adapter","python","-c",code]))

    def check(self):
        f = self.proposal; services=self.config["services"]; env=services["api"]["environment"]
        if (self.config.get("name")!=PROJECT or not env["DATABASE_URL"].endswith("/pt_parameter_sandbox")
            or env.get("OPENAI_API_KEY") or env.get("DESIGN_AI_ENABLED")!="false"
            or env.get("DESIGN_AI_DEMO_EXECUTION_GRANT_FILE") or env.get("DESIGN_AI_ACCEPTANCE_BUDGET_FILE")
            or env.get("PORTUGUESE_SUPERVISED_MODE","false").lower()=="true"):
            raise ValueError("Exact disconnected inspection-only Portuguese profile required")
        if any(not port.startswith("127.0.0.1:") for service in services.values() for port in service.get("ports",[])):
            raise ValueError("Retained loopback-only ports required")
        if hashlib.sha256(json.dumps(f["request"],sort_keys=True).encode()).hexdigest()!=f["request_sha256"]:
            raise ValueError("Frozen request integrity differs")
        for role, image in f["images"].items():
            if role=="candidate_targeted_worker":
                self.command(self.D+["image","inspect",image]); continue
            actual=self.inspect(role); limits=f["resources"]["retained_component_limits"][role]
            memory=int(limits["mem_limit"][:-1])*({'m':1024**2,'g':1024**3}[limits["mem_limit"][-1]])
            if (actual["Image"]!=image or not actual["State"]["Running"]
                or actual["HostConfig"]["Memory"]!=memory
                or actual["HostConfig"]["NanoCpus"]!=int(limits["cpus"]*1e9)):
                raise ValueError("Serving image/resource drift: "+role)
        credential=json.loads((self.profile/"credentials.json").read_text())
        with requests.Session() as session:
            session.trust_env=False; base="http://127.0.0.1:23124/api"
            response=session.post(base+"/auth/login",json={k:credential[k] for k in ["email","password"]},timeout=10);response.raise_for_status()
            if response.json()["id"]!=credential["owner_id"]:raise ValueError("Reviewer identity differs")
            saved=session.get(base+"/solutions/"+f["solution_id"],timeout=10);saved.raise_for_status();saved=saved.json()
            if saved["updated_at"]!=f["saved_revision"]:raise ValueError("Saved revision changed")
            nodes={n["id"]:n["data"] for n in saved["nodes"] if n.get("data",{}).get("service")}
            if (saved["name"]!=f["request"]["name"] or set(nodes)!={n["node_id"] for n in f["request"]["nodes"]}
                or (saved.get("design_metadata") or {}).get("run_input")!=f["request"]["run_input"]
                or any(nodes[n["node_id"]]["service"]["id"]!=n["service_id"]
                       or nodes[n["node_id"]].get("configuration")!=n["configuration"]
                       or nodes[n["node_id"]].get("operation_contract")!=n["operation_contract"] for n in f["request"]["nodes"])):
                raise ValueError("Saved input, settings or instances drifted")
            links=[{"source":e["source"],"target":e["target"],"binding":(e.get("data") or {}).get("binding")} for e in saved["edges"] if e["source"] in nodes and e["target"] in nodes]
            if links!=f["request"]["edges"]:raise ValueError("Saved binding drifted")
            response=session.post(base+"/workflows/compile",json=f["request"],timeout=15);response.raise_for_status()
            self.compiled=response.json();self.saved=saved
            if self.compiled["solution_studio_metadata"]["execution_instances"]!=f["instances"]:raise ValueError("Compiled settings/pins/binding differ")
            if any(n["image"]!=f["registered_adapter_image"] for n in self.compiled["blueprint"]["nodes"]):raise ValueError("Historical registered image mapping drifted")
            for method, expected in f["contracts"].items():
                response=session.get(base+"/services/pt-experimental-chain-"+method+"/operation-contract-resolution",timeout=10);response.raise_for_status();contract=response.json()["contract"]
                if contract["id"]!=expected["id"] or contract["contract_version"]!=expected["version"] or contract["definition"]!=expected["definition"]:raise ValueError("Active contract definition drift")
        code="import pathlib,hashlib;print(hashlib.sha256(pathlib.Path('/state/dataset.csv').read_bytes()).hexdigest())"
        if self.command(self.C+["exec","-T","pt-adapter","python","-c",code]).strip()!=f["dataset_sha256"]:raise ValueError("Approved dataset changed")
        if any(j["state"]!="complete" for j in self.journal()["jobs"]):raise ValueError("Unresolved algorithm dispatch; reconcile first")
        if not self.authority and any(a["state"]!="closed" for a in self.journal()["authorizations"]):raise ValueError("Read-only preparation requires all existing scopes closed")
        ledger=f.get("provider_ledger")
        if ledger:
            root=self.profile.parents[2];path=(root/ledger["relative_path"]).resolve()
            if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest()!=ledger["sha256"]:raise ValueError("Provider ledger identity changed")
            with sqlite3.connect(path.as_uri()+"?mode=ro",uri=True) as db:
                if db.execute("select count(*) from requests").fetchone()[0]!=25 or db.execute("select count(*) from requests where usage is null or status='settled_unacknowledged'").fetchone()[0]:raise ValueError("Provider accounting drift")
        for name in [PROJECT+"-worker-1","ai-effect-pt-chain-20261113-worker","ai-effect-pt-owner-recovery-wf-375a888b8976"]:
            if json.loads(self.command(self.D+["inspect",name]))[0]["State"]["Running"]:raise ValueError("Earlier worker must remain stopped")

    def verify_authority(self):
        a=self.authority; f=self.proposal
        if not a or not self.worker_name or a["request_sha256"]!=f["request_sha256"] or a["authorization_id"]!=f["proposed_authorization_id"]:
            raise ValueError("Separately created exact proposed authority and unique worker name required")
        tasks={n["task_id"]:{"method":n["operation_name"],"configuration":n["configuration"],"inputs":self.compiled["inputs"] if n["operation_name"]=="TrainModel" else "producer:model_ref"} for n in f["instances"]}
        if (a["owner_id"]!=self.saved["created_by_user_id"] or a["dataset_sha256"]!=f["dataset_sha256"]
            or a["tasks"]!=tasks or a["binding"]!=f["binding"] or a["resources"].get("images")!=f["images"]
            or a["resources"].get("limits")!=f["resources"]):
            raise ValueError("Existing authority does not match the reviewed task/input/resource policy")
        rows=self.journal(); scope=next((v for v in rows["authorizations"] if v["id"]==a["authorization_id"]),None)
        if (not scope or scope["state"]!="prepared" or json.loads(scope["policy"])!=a
            or any(v["state"]!="closed" for v in rows["authorizations"] if v["id"]!=a["authorization_id"])
            or any(v["authorization_id"]==a["authorization_id"] for v in rows.get("supervised_processors",[]))):
            raise ValueError("Authority absent, changed, closed, bound or processor consumed; no replacement")
        if hashlib.sha256(json.dumps(a,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()!=scope["policy_sha256"]:
            raise ValueError("Authorization policy integrity differs")
        if not re.fullmatch(r"ai-effect-pt-supervised-[A-Za-z0-9_-]+",self.worker_name):raise ValueError("One explicit Portuguese supervised worker name required")
        if self.worker_name in self.command(self.D+["ps","-a","--format","{{.Names}}"]).splitlines():raise ValueError("Worker name is retained already; never replace or restart it")
        # API admission must remain disabled while dependencies are recreated.
        if self.config["services"]["api"]["environment"].get("PORTUGUESE_SUPERVISED_MODE","false").lower()=="true":raise ValueError("Disable API admission first")

    def write(self):
        # Refuse external configuration edits; this helper owns only three roles.
        prior=getattr(self,"last_written",self.original)
        if self.path.read_bytes()!=prior:raise ValueError("Private compose changed concurrently")
        data=json.dumps(self.config,indent=2).encode();self.path.write_bytes(data);self.last_written=data

    def configure_adapter(self):
        services=self.config["services"]; services["pt-adapter"]["environment"]["PT_SANDBOX_SUPERVISED"]="1"
        worker=services["chain-worker"];worker["image"]=self.proposal["images"]["candidate_targeted_worker"]
        worker["environment"].update({k:v for k,v in services["pt-adapter"]["environment"].items() if k.startswith("PT_SANDBOX_")})
        worker["volumes"]=deepcopy(services["chain-operator"]["volumes"][:2])+["adapter:/state"]
        if worker["restart"]!="no" or worker["cpus"]!=1 or worker["mem_limit"]!="384m":raise ValueError("Worker resource/restart drift")
        self.write()

    def up(self, role):
        if role not in {"api","pt-adapter"}:raise ValueError("Only API/adapter activation is supported")
        self.command(self.C+["up","-d","--no-deps","--no-build","--pull","never",role])

    def identity(self, role): return self.inspect(role)["Id"]

    def probe(self, *, timeout=20):
        # Probe container has no journal mount and never imports Worker.main.
        cfg=deepcopy(self.config);worker=cfg["services"]["chain-worker"]
        worker["image"]=self.proposal["images"]["candidate_targeted_worker"]
        worker["environment"].update({k:v for k,v in cfg["services"]["pt-adapter"]["environment"].items() if k.startswith("PT_SANDBOX_")})
        worker["volumes"]=deepcopy(cfg["services"]["chain-operator"]["volumes"][:2])
        path=self.records/"probe-compose.private.json";path.write_text(json.dumps(cfg,indent=2))
        command=self.D+["compose","-f",str(path),"run","--rm","--no-deps","--pull","never","chain-worker","python","-m","experimental.portuguese_parameters.supervised_worker","--probe-only"]
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
        except subprocess.TimeoutExpired:
            raise ConnectionError("Read-only dependency probe reached its startup deadline") from None
        (self.records/"probe.private.log").write_text(result.stdout+result.stderr)
        if result.returncode:
            if "TransientProbeError:" in result.stderr:raise ConnectionError("Read-only dependency startup failure")
            raise ValueError("Permanent dependency/authentication/capability failure; inspect probe.private.log")
        if json.loads(result.stdout).get("status")!="ready":raise ValueError("Unexpected probe result")

    def start_worker(self):
        with (self.records/"worker-start-attempt.json").open("x") as out:json.dump({"name":self.worker_name,"scope":self.authority["authorization_id"]},out)
        self.command(self.C+["run","-d","--name",self.worker_name,"--no-deps","--pull","never","chain-worker","python","-m","experimental.portuguese_parameters.supervised_worker",self.authority["authorization_id"]])
        worker=json.loads(self.command(self.D+["inspect",self.worker_name]))[0]
        (self.records/"worker-start-result.private.json").write_text(json.dumps({"id":worker["Id"]}))
        adapter=self.inspect("pt-adapter")
        journal=next(m["Name"] for m in adapter["Mounts"] if m["Destination"]=="/state")
        if (worker["Image"]!=self.proposal["images"]["candidate_targeted_worker"] or worker["HostConfig"]["Memory"]!=384*1024**2
            or worker["HostConfig"]["NanoCpus"]!=1_000_000_000 or worker["HostConfig"]["RestartPolicy"]["Name"]!="no"
            or not any(m.get("Name")==journal and m["Destination"]=="/state" for m in worker["Mounts"])):
            raise ValueError("Named processor image/resource/journal identity differs")

    def wait_lease(self):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            rows=self.journal(); scope=next(v for v in rows["authorizations"] if v["id"]==self.authority["authorization_id"])
            processor=next((v for v in rows.get("supervised_processors",[]) if v["authorization_id"]==scope["id"]),None)
            if scope["state"]!="prepared":raise ValueError("Scope bound/closed during activation; reconcile")
            if processor and processor["state"]=="finished":raise ValueError("Processor finished; inspect its log; no replacement")
            if processor and processor["state"]=="waiting" and time.time()+2<processor["lease_until"]<=time.time()+6:return
            time.sleep(.25)
        raise ValueError("Fresh waiting-processor lease unavailable; API admission remains disabled")

    def enable_api(self):
        self.config["services"]["api"]["environment"].update(PORTUGUESE_SUPERVISED_MODE="true",PORTUGUESE_SUPERVISED_AUTHORIZATION_ID=self.authority["authorization_id"],PORTUGUESE_SUPERVISED_ADAPTER_URL="http://pt-adapter:8080");self.write()

    def disable_api(self):
        self.config["services"]["api"]["environment"]["PORTUGUESE_SUPERVISED_MODE"]="false";self.write()

    def stop_if_unbound(self):
        marker=self.records/"worker-start-result.private.json"
        if not marker.exists():return  # Unknown Docker response requires operator reconciliation.
        actual=json.loads(self.command(self.D+["inspect",self.worker_name]))[0]
        if actual["Id"]!=json.loads(marker.read_text())["id"]:raise ValueError("Processor identity changed; reconcile without stopping unrelated work")
        row=next(v for v in self.journal()["authorizations"] if v["id"]==self.authority["authorization_id"])
        if row["state"]=="prepared" and row["workflow_id"] is None:
            self.command(self.D+["stop","--time","20",self.worker_name])


def reviewed_restore(current, before):
    """Restore only this helper's three roles, never unrelated configuration."""
    for key in set(current)|set(before):
        if key!="services" and current.get(key)!=before.get(key):raise ValueError("Unrelated compose configuration drift")
    if set(current["services"])!=set(before["services"]):raise ValueError("Service inventory drift")
    for role in before["services"]:
        if role not in {"api","pt-adapter","chain-worker"} and current["services"][role]!=before["services"][role]:raise ValueError("Unrelated service drift: "+role)
    return before


def restore_review(profile, records):
    """Explicit post-close cleanup. Never closes authority or stops active work."""
    marker=json.loads((records/"worker-start-attempt.json").read_text())
    path=profile/"compose.private.json";original=(records/"compose-before.private.json").read_bytes()
    reviewed_restore(json.loads(path.read_text()),json.loads(original))
    D=["docker","--context","desktop-linux"];C=D+["compose","-f",str(path)]
    worker=json.loads(subprocess.check_output(D+["inspect",marker["name"]],text=True,timeout=15))[0]
    if worker["State"]["Running"]:raise ValueError("Stop the exact named processor first; do not interrupt uncertain work")
    code="""import sqlite3,sys
with sqlite3.connect('file:/state/journal.sqlite3?mode=ro',uri=True) as db:
 row=db.execute('select state from authorizations where id=?',(sys.argv[1],)).fetchone()
 assert row and row[0]=='closed'
 assert not db.execute("select 1 from jobs where state='running'").fetchone()
print('closed')
"""
    subprocess.run(C+["exec","-T","pt-adapter","python","-c",code,marker["scope"]],check=True,timeout=20,capture_output=True)
    path.write_bytes(original)
    subprocess.run(C+["up","-d","--no-deps","--no-build","--pull","never","api","pt-adapter"],check=True,timeout=60,capture_output=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["check","activate","restore-review"])
    parser.add_argument("--profile",type=Path,required=True);parser.add_argument("--proposal",type=Path)
    parser.add_argument("--records",type=Path,required=True);parser.add_argument("--authority-file",type=Path);parser.add_argument("--worker-name")
    args=parser.parse_args()
    if args.action=="restore-review":
        restore_review(args.profile.resolve(),args.records.resolve());print("Inspection configuration restored after verified closure; no authority created");return
    if not args.proposal:parser.error("--proposal required")
    driver=DockerProfile(args.profile,args.proposal,args.records,args.authority_file,args.worker_name)
    if args.action=="check":driver.probe()
    else:activate(driver)
    print(json.dumps({"status":"ready","action":args.action,"authority_created":False,"workflow_submitted":False}))


if __name__=="__main__":main()
