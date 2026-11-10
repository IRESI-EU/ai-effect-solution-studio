"""Prepare one new engineering recommendation in the retained host harness.

No reset, new profile, account or stack. Existing recommendations/designs stay
unchanged. A generated local-only entry restores the real app's conversation.
"""
import argparse
import json
from pathlib import Path
import httpx

from harness import ROOT, LABEL, PROMPT, build_app, deny_network


def prepare(profile):
    profile = profile.resolve(strict=True)
    record = profile / "prepared-workspace-review-20261110.json"
    entry = ROOT / "apps/web/public/offline-workspace-review.html"
    if record.exists() or entry.exists():
        raise SystemExit("Engineering entry already prepared; preserve it, do not reset/replay")
    config = httpx.get("http://127.0.0.1:28187/design-ai/config",timeout=3,trust_env=False).json()
    assert config["provider_name"] == LABEL and config["provider_mode"] == "test" and not config["provider_configured"]
    app = build_app(profile, preparing=True)
    deny_network()
    from fastapi.testclient import TestClient
    credentials = json.loads((profile / "private-credentials.json").read_text())["agent"]
    with TestClient(app) as client:
        assert client.post("/auth/login",json=credentials).status_code == 200
        response=client.post("/design-ai/chat",json={"message":PROMPT})
        assert response.status_code == 200
        value=response.json()
        assert value["recommendation"]["mechanism"] == "catalogue_composed"
        client.post("/auth/logout")
    record.write_text(json.dumps(value,indent=2),encoding="utf-8")
    conversation={"ownerId":"controls-agent","draftId":None,"messages":[{"role":"assistant","content":"Separate engineering review. Prepared synthetic proposal; no live AI or execution."}],
        "activity":value["activity"],"prompt":"","seedInput":"42","historyUnavailable":False,"recommendation":value["recommendation"]}
    payload=json.dumps(conversation).replace("<","\\u003c")
    entry.write_text('<!doctype html><meta charset="utf-8"><title>Offline workspace review</title><p>'+LABEL+'</p>'
        '<p id="status">Opening the existing application…</p><script>(async()=>{const r=await fetch("/api/auth/me",{cache:"no-store"});'
        'if(!r.ok){location.replace("/login?next=/offline-workspace-review.html");return;}const u=await r.json();'
        'if(u.id!=="controls-agent"){document.getElementById("status").textContent="Sign in with the dedicated engineering account. Your existing design is unchanged.";return;}'
        'localStorage.setItem("design-ai-discovery:controls-agent",JSON.stringify('+payload+'));location.replace("/design-ai");})();</script>',encoding="utf-8")
    print("Prepared a distinct server-issued engineering recommendation; no draft created and no existing recommendation changed")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile",type=Path,required=True)
    prepare(parser.parse_args().profile)
