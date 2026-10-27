"""Prepare a NEW local acceptance database from an explicit real metadata export.

Never imports users, sessions, historic deployments, datasets or artifacts.
Never drops, resets or writes into an existing database. Local bootstrap uses
the existing authentication mechanism and existing environment variable names.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
from uuid import uuid4

from dotenv import dotenv_values
import psycopg
from psycopg import sql
from sqlalchemy.engine import URL


def prepare(cluster_file: Path, export: Path, env_file: Path):
    if env_file.exists():
        raise ValueError("The acceptance environment file already exists; no database was created or changed")
    cluster=json.loads(cluster_file.read_text())
    if cluster.get("purpose")!="design-ai-disposable-acceptance" or cluster.get("host") not in {"127.0.0.1","localhost","::1"}:
        raise ValueError("An explicitly identified local acceptance cluster is required")
    encoded=export.read_bytes()
    bundle=json.loads(encoded)
    if bundle.get("format")!="ai-effect-design-metadata/1" or not bundle.get("solutions") or set(bundle["solutions"])-{"denmark","dutch","portugal","germany"}:
        raise ValueError("Not a supported explicit real-metadata export")
    name="design_ai_acceptance_"+uuid4().hex[:12]
    url=URL.create("postgresql+psycopg",username=cluster["user"],password=cluster["password"],host=cluster["host"],port=cluster["port"],database=name)
    # CREATE DATABASE fails rather than reusing a name; never connect to a user database.
    with psycopg.connect(url.set(drivername="postgresql",database="postgres").render_as_string(hide_password=False),autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(name)))
    provider_file=dotenv_values(".env.design-ai") if Path(".env.design-ai").is_file() else {}
    values={"DATABASE_URL":url.render_as_string(hide_password=False),"DESIGN_AI_ENABLED":"true",
        "DESIGN_AI_TEMPLATES":json.dumps({key:{"solution_id":item["id"]} for key,item in bundle["solutions"].items()}),
        "OPENAI_API_KEY":os.environ.get("OPENAI_API_KEY") or provider_file.get("OPENAI_API_KEY") or "",
        "DESIGN_AI_MODEL":os.environ.get("DESIGN_AI_MODEL") or provider_file.get("DESIGN_AI_MODEL") or "",
        "BOOTSTRAP_ADMIN_EMAIL":"local-acceptance@example.test","BOOTSTRAP_ADMIN_PASSWORD":secrets.token_hex(20)+"Aa1!",
        "BOOTSTRAP_ADMIN_NAME":"Local acceptance — historical real metadata","SECURE_COOKIES":"false",
        "ORCHESTRATOR_BASE_URL":"http://127.0.0.1:9"}
    os.environ.update(values)
    from app.main import app  # Database URL is deliberately set before importing any application module.
    from app.db import SessionLocal
    from app.models.user import User
    from app.models.service import Service
    from app.models.solution import Solution
    from app.models.operation_contract import OperationContract
    from app.services.design_ai import template
    def attributes(model,item):
        result={key:value for key,value in item.items() if key in model.__table__.columns.keys()}
        result.pop("created_by_user_id",None)
        for column in model.__table__.columns:
            if column.type.__class__.__name__=="DateTime" and isinstance(result.get(column.name),str):
                result[column.name]=datetime.fromisoformat(result[column.name])
        return result
    with SessionLocal() as db:
        actor=db.query(User).filter(User.email==values["BOOTSTRAP_ADMIN_EMAIL"]).one()
        for item in bundle["services"]:
            db.add(Service(**attributes(Service,item),created_by_user_id=actor.id))
        db.flush()
        for item in bundle["contracts"]:
            db.add(OperationContract(**attributes(OperationContract,item)))
        for item in bundle["solutions"].values():
            data=attributes(Solution,item)
            data["design_metadata"]={**(data.get("design_metadata") or {}),"acceptance_export":{"sha256":hashlib.sha256(encoded).hexdigest(),"source_dump":bundle.get("source_dump"),"reference_note":bundle["reference_note"]}}
            db.add(Solution(**data,created_by_user_id=actor.id))
        db.commit()
        for key in bundle["solutions"]:
            template(key,db,actor)  # Do not repair or broaden source metadata to force acceptance.
    env_file.parent.mkdir(parents=True,exist_ok=True)
    with env_file.open("x",encoding="utf-8") as target:
        target.write("# Private local acceptance only. Never commit this file.\n")
        target.write("\n".join(f"{key}={json.dumps(value,ensure_ascii=False)}" for key,value in values.items())+"\n")
    print(json.dumps({"database":name,"templates":list(bundle["solutions"]),"export_sha256":hashlib.sha256(encoded).hexdigest(),
        "provider_configured":bool(values["OPENAI_API_KEY"] and values["DESIGN_AI_MODEL"]),"env_file":str(env_file)},ensure_ascii=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cluster-config",type=Path,required=True)
    parser.add_argument("--metadata-export",type=Path,required=True)
    parser.add_argument("--env-file",type=Path,required=True)
    args=parser.parse_args()
    try:
        prepare(args.cluster_config,args.metadata_export,args.env_file)
    except ValueError as error:
        parser.exit(1,str(error)+"\n")
