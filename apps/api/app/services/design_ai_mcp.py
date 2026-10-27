"""Private, per-request MCP server. Auth is bound outside model-controlled arguments."""
from contextlib import asynccontextmanager
from datetime import timedelta
from functools import wraps
import json

from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.shared.memory import create_connected_server_and_client_session

from app.core.config import settings
from app.models.user import User
from app.schemas.design_ai import AssistantTurn
from app.services import design_ai as service


def create_server(db, user: User, *, draft_id: str | None = None, explicit_save: bool = False):
    server = FastMCP("AI-EFFECT private design tools")

    def design_tool(function):
        @wraps(function)
        async def guarded(*args, **kwargs):
            try:
                return await function(*args, **kwargs)
            except HTTPException as exc:
                # Only controlled application errors cross the MCP boundary.
                message = exc.detail if isinstance(exc.detail, str) else "A referenced service is missing or inaccessible"
                raise ToolError("DESIGN_ERROR:" + json.dumps({"status": exc.status_code, "message": message})) from None
        return server.tool()(guarded)

    def authorize():
        service.enabled()
        actor = db.query(User).filter(User.id == user.id, User.status == "active").populate_existing().first()
        if not actor or actor.role not in {"solution_designer", "node_manager", "platform_admin"}:
            raise HTTPException(403, "Active design account required")
        return actor

    @design_tool
    async def list_pilot_templates() -> dict:
        """List operator-selected saved templates and their availability."""
        return {"templates": service.list_templates(db, authorize())}

    @design_tool
    async def read_template(template_key: str) -> dict:
        """Read an eligible saved template, its source revision and real services."""
        value = service.template(template_key, db, authorize())
        return {"key": value["key"], "name": value["name"], "description": value["description"],
                "source": value["source"], "reference_note": value["reference_note"],
                "services": [{"node_id": node["id"], **{key: node["data"]["service"].get(key) for key in
                    ("id", "name", "description", "operation_name", "status", "version")}} for node in service.service_nodes(value["nodes"])],
                "connections": [{"source": e["source"], "target": e["target"]} for e in value["edges"]]}

    @design_tool
    async def discover_guided_capability(template_key: str) -> dict:
        """Retrieve verified supported local capabilities without creating a draft."""
        return service.discovery_capability(template_key, db, authorize())

    @design_tool
    async def inspect_supported_configuration(template_key: str) -> dict:
        """Inspect active operation contracts and explicitly verified wrapper inputs."""
        actor = authorize()
        value = service.template(template_key, db, actor)
        contracts = service.contracts(value["nodes"], db)
        parameters_supported = any(c.get("definition", {}).get("execution_parameters") for c in contracts if c.get("definition"))
        return {"contracts": contracts, "run_input": value["input_policy"],
                "supported_edits": ["rename", "describe", "set_node_label"] + (["set_run_input"] if value["input_policy"] else []) + (["set_node_parameters"] if parameters_supported else []),
                "named_bindings_preserved": False, "runtime_checked": False}

    @design_tool
    async def validate_draft(proposal: dict) -> dict:
        """Validate a structured edit against the current caller-owned draft without applying it."""
        actor = authorize()
        if not draft_id:
            raise HTTPException(409, "Create a draft first")
        row = service.load_draft(draft_id, db, actor)
        _, result = service.candidate(row, AssistantTurn.model_validate(proposal), db, actor)
        return result

    @design_tool
    async def save_draft(revision: int) -> dict:
        """Save only in a server-authorized explicit Save draft request."""
        actor = authorize()
        if not draft_id or not explicit_save:
            raise HTTPException(403, "An explicit Save draft action is required")
        return service.save(draft_id, revision, db, actor, explicit_save=explicit_save)

    return server


class DesignTools:
    def __init__(self, session):
        self.session = session
        self.activity = []
        self.calls = 0

    async def discover(self):
        result = await self.session.list_tools()
        self.activity.append({"tool": "tools/list", "status": "ok", "summary": f"Discovered {len(result.tools)} private design tools"})
        return result

    async def call(self, name: str, arguments: dict):
        service.enabled()
        self.calls += 1
        if self.calls > min(max(settings.design_ai_tool_limit, 1), 12):
            raise HTTPException(422, "Design tool call limit reached")
        result = await self.session.call_tool(name, arguments)
        self.activity.append({"tool": name, "status": "error" if result.isError else "ok",
                              "summary": "Design request rejected" if result.isError else "Completed through private MCP connection"})
        if result.isError:
            # Do not relay SDK tracebacks, raw metadata or credentials to the browser.
            for item in result.content:
                if item.type == "text" and "DESIGN_ERROR:" in item.text:
                    try:
                        error = json.loads(item.text.split("DESIGN_ERROR:", 1)[1])
                        raise HTTPException(error["status"], {"message": error["message"], "activity": self.activity})
                    except (ValueError, KeyError):
                        break
            raise HTTPException(422, "The design tool rejected this request. Refresh the draft and check template configuration.")
        if result.structuredContent is not None:
            return result.structuredContent
        return json.loads(next(item.text for item in result.content if item.type == "text"))


@asynccontextmanager
async def connection(db, user, **kwargs):
    service.enabled()
    server = create_server(db, user, **kwargs)
    failure = None
    async with create_connected_server_and_client_session(server, read_timeout_seconds=timedelta(seconds=15)) as session:
        tools = DesignTools(session)
        try:
            yield tools
        except BaseException as exc:
            # Close SDK task groups normally so application HTTP errors are not
            # wrapped into ExceptionGroup and accidentally become 500 responses.
            failure = exc
    if failure is not None:
        raise failure
