"""Check historical real metadata locally; real OpenAI smoke is explicit and bounded.

Default mode uses manual structured edits, not a mocked or scripted AI provider.
--real-provider performs at most seven Responses requests using the configured
runtime model. Never executes workflows or retrieves datasets/artifacts.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


def check(env_file, real_provider, output):
    if output.exists():
        raise ValueError("Choose a new report path; no acceptance records were changed")
    load_dotenv(env_file,override=True)
    url=make_url(os.environ["DATABASE_URL"])
    if url.host not in {"127.0.0.1","localhost","::1"} or not url.database.startswith("design_ai_acceptance_"):
        raise ValueError("This check only writes to a newly prepared local acceptance database")
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import SessionLocal
    from app.models.user import User
    from app.models.solution import Solution
    from app.core.config import settings
    from app.schemas.design_ai import AssistantTurn
    from app.services import design_ai as service
    from app.services.design_ai_mcp import connection
    from app.services.design_ai_provider import configured
    if real_provider and not configured():
        raise ValueError("Real-provider check blocked: set OPENAI_API_KEY and DESIGN_AI_MODEL in the local acceptance env file; no fallback was used")
    report={"database":"isolated PostgreSQL","metadata":"historical real export","provider":"real OpenAI" if real_provider else "not used; manual structured edits",
            "runtime_model":settings.design_ai_model if real_provider else None,"domain_input_verified":False,
            "execution_invoked":False,"checks":{},"activity":[],"provider_requests":0}
    def good(response):
        if response.status_code!=200:
            raise RuntimeError(f"Acceptance request failed (HTTP {response.status_code}); inspect the local API log, not credentials or raw upstream responses")
        return response.json()
    with TestClient(app) as client:
        good(client.post("/auth/login",json={"email":settings.bootstrap_admin_email,"password":settings.bootstrap_admin_password}))
        def chat(message,draft=None):
            report["provider_requests"]+=1
            assert report["provider_requests"]<=7
            result=good(client.post("/design-ai/chat",json={"message":message,"draft_id":draft["id"] if draft else None,"revision":draft["revision"] if draft else None}))
            report["activity"].extend(result["activity"])
            return result
        for key in ("denmark","dutch"):
            with SessionLocal() as db:
                actor=db.query(User).filter(User.email==settings.bootstrap_admin_email).one()
                source=service.source_solution(key,db)
                before=service.digest(service.content(source))
                source_id=source.id
                async def inspect_tools():
                    async with connection(db,actor) as tools:
                        discovered=await tools.discover()
                        assert {item.name for item in discovered.tools}=={"list_pilot_templates","read_template","inspect_supported_configuration","validate_draft","save_draft"}
                        metadata=await tools.call("read_template",{"template_key":key})
                        configuration=await tools.call("inspect_supported_configuration",{"template_key":key})
                        assert configuration["run_input"] is None
                        report["activity"].extend(tools.activity)
                        return metadata
                metadata=asyncio.run(inspect_tools())
            if real_provider:
                objective=("I want a district-heating topology study using Danish SysLAB. Recommend its saved template and explain only retrieved services." if key=="denmark" else "Recommend the existing Dutch Node ConfigureAndSynthesize to RunBenchmark template.")
                assert chat(objective)["recommendation"]["key"]==key
            draft=good(client.post("/design-ai/drafts",json={"template_key":key}))
            assert draft["validation"]["unknown"]
            if real_provider and key=="denmark":
                chat("Explain the services and connections of my current draft. Do not edit it.",draft)
            def propose(current):
                name=f"Local acceptance {key} study"
                if real_provider:
                    return chat(f"Rename my draft to {name}. This is a display name change only.",current)["draft"]
                with SessionLocal() as db:
                    actor=db.query(User).filter(User.email==settings.bootstrap_admin_email).one()
                    proposal=AssistantTurn(message="Explicit manual structured edit; no AI provider used",template_key=None,expected_revision=current["revision"],edits=[{"kind":"rename","value":name,"node_id":None}])
                    return service.propose(current["id"],proposal,db,actor)
            proposal=propose(draft)
            current=good(client.post(f"/design-ai/drafts/{draft['id']}/apply",json={"revision":draft["revision"],"proposal_id":proposal["pending"]["id"]}))
            if key=="denmark":
                restored=good(client.post(f"/design-ai/drafts/{draft['id']}/undo",json={"revision":current["revision"]}))
                assert restored["design"]==draft["design"]
                proposal=propose(restored)
                current=good(client.post(f"/design-ai/drafts/{draft['id']}/apply",json={"revision":restored["revision"],"proposal_id":proposal["pending"]["id"]}))
            prior=service.digest(current["design"])
            if real_provider and key=="dutch":
                declined=chat("Replace RunBenchmark with an unavailable magic service. Decline unsupported changes and keep the draft intact.",current)
                assert declined["draft"] is None or not declined["draft"].get("pending")
            else:
                with SessionLocal() as db:
                    actor=db.query(User).filter(User.email==settings.bootstrap_admin_email).one()
                    async def invalid():
                        async with connection(db,actor,draft_id=draft["id"]) as tools:
                            result=await tools.session.call_tool("validate_draft",{"proposal":{"message":"Invalid replacement", "template_key":None,"expected_revision":current["revision"],"edits":[{"kind":"replace_service","value":"unavailable","node_id":"invented"}]}})
                            assert result.isError
                    asyncio.run(invalid())
            assert service.digest(good(client.get("/design-ai/drafts/"+draft["id"]))["design"])==prior
            saved=good(client.post(f"/design-ai/drafts/{draft['id']}/save",json={"revision":current["revision"]}))
            report["activity"].extend(saved["activity"])
            saved=saved["draft"]
            again=good(client.post(f"/design-ai/drafts/{draft['id']}/save",json={"revision":current["revision"]}))["draft"]
            assert again["saved_solution_id"]==saved["saved_solution_id"]
            loaded=good(client.get("/solutions/"+saved["saved_solution_id"]))
            assert loaded["nodes"]==current["design"]["nodes"] and loaded["edges"]==current["design"]["edges"]
            assert loaded["design_metadata"]["run_input"] is None and loaded["status"]=="draft"
            with SessionLocal() as db:
                assert service.digest(service.content(db.get(Solution,source_id)))==before
            code="""import sys,json
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
with TestClient(app) as c:
 assert c.post('/auth/login',json={'email':settings.bootstrap_admin_email,'password':settings.bootstrap_admin_password}).status_code==200
 d=c.get('/design-ai/drafts/'+sys.argv[1]).json()
 s=c.get('/solutions/'+sys.argv[2]).json()
 assert d['saved_solution_id']==s['id'] and d['design']['nodes']==s['nodes'] and d['design']['edges']==s['edges']
 print('Restart persistence passed')
"""
            result=subprocess.run([sys.executable,"-c",code,draft["id"],saved["saved_solution_id"]],env=os.environ.copy(),capture_output=True,text=True,timeout=30)
            if result.returncode:
                raise RuntimeError("Fresh-process restart verification failed; raw output omitted")
            report["checks"][key]={"services":[{"id":item["id"],"operation":item["operation_name"]} for item in metadata["services"]],
                "copy_edit_save_reload_builder":"passed","source_unchanged":True,"invalid_edit_preserved_draft":True,
                "draft_id":draft["id"],"saved_solution_id":saved["saved_solution_id"],"domain_inputs":"not verified; no wrapper schema or operation contracts in this export"}
        if not real_provider and not configured():
            response=client.post("/design-ai/chat",json={"message":"Help me design a district-heating topology study"})
            assert response.status_code==503
            report["real_provider_check"]="blocked: OPENAI_API_KEY and/or DESIGN_AI_MODEL missing; no fallback"
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf-8") as target:
        json.dump(report,target,indent=2,ensure_ascii=False)
    print(json.dumps({"checks":list(report["checks"]),"provider":report["provider"],"provider_requests":report["provider_requests"],"report":str(output)}))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--real-provider",action="store_true")
    args=parser.parse_args()
    try:
        check(args.env_file,args.real_provider,args.output)
    except (ValueError,RuntimeError) as error:
        parser.exit(1,str(error)+"\n")
