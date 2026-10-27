"""Local verification-only middleware; not installed by the product application."""
import json

PROMPTS = {
    "A": "Change the second topology step to generate up to four options. Leave the first step unchanged.",
    "B": "Change the topology limit to four.",
}


def install_guard(app, directory, plans):
    from starlette.responses import JSONResponse, Response
    @app.middleware("http")
    async def verification_only(request, call_next):
        path = request.url.path
        if path.startswith(("/workflows", "/deployments", "/data-references")):
            return JSONResponse({"detail": "Provider verification: workflow submission and runtime access are blocked"}, status_code=403)
        if request.method not in {"GET", "HEAD"}:
            allowed = path in {"/auth/login", "/auth/logout", "/design-ai/chat"} or any(
                path == f"/design-ai/drafts/{plans['A']['draft_id']}/{action}" for action in ("apply", "save"))
            if not allowed:
                return JSONResponse({"detail": "Provider verification: mutation outside the authorized cases is blocked"}, status_code=403)
        if request.method == "POST" and path == "/design-ai/chat":
            if not (directory / "live-preflight.json").is_file():
                return JSONResponse({"detail": "Complete the two-case preflight first"}, status_code=403)
            body = await request.json()
            case = next((case for case, plan in plans.items() if body.get("draft_id") == plan["draft_id"]
                         and body.get("message") == PROMPTS[case] and body.get("revision") == 0 and not body.get("history")), None)
            if not case:
                return JSONResponse({"detail": "Only the two exact prepared requests are authorized"}, status_code=403)
            try:
                with (directory / f"attempt-{case}.json").open("x", encoding="utf-8") as stream:
                    json.dump({"case": case, "request": body}, stream)
            except FileExistsError:
                return JSONResponse({"detail": "This case was already attempted; no retry is authorized"}, status_code=409)
            response = await call_next(request)
            raw = b"".join([part async for part in response.body_iterator])
            # Private application evidence; provider-visible text is separately
            # retained by the passive logger in the unmodified SDK request path.
            (directory / f"chat-{case}-result.json").write_bytes(raw)
            return Response(raw, status_code=response.status_code, headers=dict(response.headers), media_type=response.media_type)
        return await call_next(request)
