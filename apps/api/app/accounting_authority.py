"""Separate private service, deliberately NOT mounted in the application router.

Start only after an audited operator activation. No provider key, model client,
database credentials or policy-amendment endpoint exists in this service.
"""
import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services.shared_allowance import Authority


class Claims(BaseModel):
    model_config=ConfigDict(extra="forbid")
    scope: str = Field(min_length=1,max_length=100)
    consumer_id: str = Field(min_length=1,max_length=100)
    environment: str = Field(min_length=1,max_length=100)
    database_scope: str = Field(pattern=r"^[a-f0-9]{64}$")


class Key(Claims):
    request_key: str = Field(pattern=r"^[a-f0-9-]{36}$")


class Reserve(Key):
    input_bound: int = Field(strict=True,ge=1,le=32000)
    output_limit: int = Field(strict=True,ge=1,le=2000)
    controls: dict[str,str]


class Settle(Key):
    payload: dict


class Acknowledge(Key):
    usage_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


def create_app(path=None):
    path=path or os.environ.get("DESIGN_AI_AUTHORITY_LEDGER","")
    if not path:raise RuntimeError("Exact existing authority ledger required; service disabled")
    authority=Authority(path)
    # The owner connection permits SQLite's normal hot-journal recovery after
    # process death. It never creates a missing file or initializes a policy.
    with authority.transaction(write=True) as db:authority.verify(db)
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)

    def bearer(authorization:Annotated[str,Header()]=""):
        if not authorization.startswith("Bearer ") or not 32<=len(authorization[7:])<=256:
            raise HTTPException(401,"Private accounting authentication required")
        return authorization[7:]

    def claims(value):return {k:v for k,v in value.model_dump().items() if k in Claims.model_fields}

    @app.post("/v1/status")
    def status(value:Claims,token=Depends(bearer)):
        return authority.availability(token,claims(value))

    @app.post("/v1/reserve")
    def reserve(value:Reserve,token=Depends(bearer)):
        return authority.reserve(token,claims(value),value.request_key,value.input_bound,value.output_limit,value.controls)

    @app.post("/v1/lookup")
    def lookup(value:Key,token=Depends(bearer)):
        return authority.lookup(token,claims(value),value.request_key)

    @app.post("/v1/settle")
    def settle(value:Settle,token=Depends(bearer)):
        return authority.settle(token,claims(value),value.request_key,value.payload)

    @app.post("/v1/acknowledge")
    def acknowledge(value:Acknowledge,token=Depends(bearer)):
        return authority.acknowledge(token,claims(value),value.request_key,value.usage_sha256)

    return app
