"""No ledger replica, local fallback, redirects, environment proxy or retries."""
from urllib.parse import urlsplit
from pathlib import PurePosixPath
from pathlib import Path
import ssl
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.services.shared_allowance import CONTROLS, database_scope, digest, safe_usage


def requested(settings):
    return any(getattr(settings,"design_ai_budget_"+name) for name in (
        "authority_url","authority_socket","authority_ca_file","authority_token","authority_id","scope","consumer","environment"))


class Client:
    def __init__(self, settings, *, transport=None):
        self.settings=settings
        try:
            url=urlsplit(settings.design_ai_budget_authority_url)
            url.port
        except ValueError as exc:raise HTTPException(503,"Invalid accounting origin") from exc
        socket=settings.design_ai_budget_authority_socket
        if (not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in {"","/"}
                or (socket and url.geturl()!="http://accounting.internal")
                or (socket and not PurePosixPath(socket).is_absolute())
                or (not socket and not (url.scheme=="https" or url.scheme=="http" and url.hostname in {"127.0.0.1","localhost","::1"}))):
            raise HTTPException(503,"Accounting requires verified HTTPS, loopback HTTP or an explicit private Unix socket")
        if (not settings.design_ai_restricted_beta or not settings.design_ai_reviewer_ids.strip()
                or settings.design_ai_acceptance_budget_file or settings.design_ai_acceptance_task_limit_file
                or not 32<=len(settings.design_ai_budget_authority_token)<=256
                or not settings.design_ai_budget_authority_id or not settings.design_ai_budget_scope
                or not settings.design_ai_budget_consumer or not settings.design_ai_budget_environment):
            raise HTTPException(503,"Exclusive restricted-beta authority configuration required; local fallback is forbidden")
        try:db_scope=database_scope(settings.database_url)
        except ValueError as exc:raise HTTPException(503,"Explicit PostgreSQL environment scope required") from exc
        self.claims={"scope":settings.design_ai_budget_scope,"consumer_id":settings.design_ai_budget_consumer,
                     "environment":settings.design_ai_budget_environment,"database_scope":db_scope}
        self.transport=transport
        self.verify=True
        ca_file=settings.design_ai_budget_authority_ca_file
        if ca_file:
            try:
                path=Path(ca_file)
                if socket or url.scheme!="https" or not path.is_absolute() or not path.is_file() or path.stat().st_size>1_048_576:
                    raise ValueError("Explicit HTTPS CA file required")
                self.verify=ssl.create_default_context()
                self.verify.load_verify_locations(cafile=str(path))
            except (OSError,ValueError,ssl.SSLError) as exc:
                raise HTTPException(503,"Accounting HTTPS CA unavailable or invalid; no fallback") from exc
        self.key=None

    def call(self, operation, **body):
        transport=self.transport or httpx.HTTPTransport(uds=self.settings.design_ai_budget_authority_socket or None,
            verify=self.verify,retries=0,trust_env=False)
        try:
            with httpx.Client(base_url=self.settings.design_ai_budget_authority_url,transport=transport,
                    headers={"Authorization":"Bearer "+self.settings.design_ai_budget_authority_token},
                    timeout=3,trust_env=False,follow_redirects=False) as client:
                response=client.post("/v1/"+operation,json={**self.claims,**body})
            if response.status_code not in {200,429}:
                raise HTTPException(503,"Accounting denied or unavailable; no retry or local allowance fallback")
            value=response.json()
            if not isinstance(value,dict):raise ValueError("Invalid receipt")
            if response.status_code==429:
                raise HTTPException(429,value.get("detail","AI messages paused by shared allowance"))
            if value.get("protocol_version")!=1 or value.get("authority_id")!=self.settings.design_ai_budget_authority_id or value.get("scope")!=self.claims["scope"]:
                raise HTTPException(503,"Accounting authority or scope identity differs")
            if "request_key" in body and value.get("request_key")!=body["request_key"]:
                raise HTTPException(503,"Accounting reservation receipt identity differs")
            return value
        except (httpx.HTTPError,ValueError,TypeError) as exc:
            raise HTTPException(503,"Accounting transport uncertain; stop without retry or local fallback") from exc

    def availability(self):return self.call("status")

    def reserve(self, input_bound, output_limit):
        self.key=str(uuid4())
        receipt=self.call("reserve",request_key=self.key,input_bound=input_bound,output_limit=output_limit,controls=CONTROLS)
        if receipt.get("dispatch_allowed") is not True or receipt.get("held_nano")!=5_000_000:
            raise HTTPException(503,"No fresh single-dispatch accounting authorization; do not resend")
        return self.key

    def settle(self, key, payload):
        if key!=self.key:raise HTTPException(503,"Wrong reservation identity")
        # Never forward response text, prompts, outputs or credentials to accounting.
        filtered={"id":payload.get("id"),"usage":safe_usage(payload.get("usage")),"service_tier":payload.get("service_tier")}
        receipt=self.call("settle",request_key=key,payload=filtered)
        usage_hash=digest(filtered["usage"])
        if receipt.get("usage_sha256")!=usage_hash or receipt.get("response_id")!=payload.get("id"):
            raise HTTPException(503,"Durable usage receipt differs; stop without retry")
        return self.call("acknowledge",request_key=key,usage_sha256=usage_hash)

    def failed(self, key, status):
        # Reservation is already durable. In particular, do NOT retry a failed
        # settlement or send more accounting writes in a provider finally block.
        # An unresolved hold blocks every environment until usage is reconciled.
        return None
