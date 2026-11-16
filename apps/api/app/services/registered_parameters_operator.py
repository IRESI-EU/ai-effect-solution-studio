"""Prepare (never activate) the existing operator template-registration policy.

No database writes, approvals, visibility or permission changes. The local operator
must install the reviewed record in DESIGN_AI_TEMPLATES, preserving other policies.
"""
import argparse
import json

from fastapi import HTTPException
from app.db import SessionLocal
from app.models.solution import Solution
from app.models.user import User
from app.models.operation_contract import OperationContract
from app.services import design_ai, capability_bindings
from app.services.registered_parameters import authority, PINS


def prepare(db,reviewer_id,source_id,registration_id):
    reviewer=db.get(User,reviewer_id);source=db.get(Solution,source_id)
    if not reviewer or not source or source.status=="archived":
        raise HTTPException(409,"Existing active reviewer and saved source required")
    contracts=db.query(OperationContract).filter(OperationContract.id.in_(PINS)).all()
    value={"solution_id":source.id,"instance_settings_only":True,"registered_parameters":{
        "registration_id":registration_id,"reviewer_id":reviewer.id,
        "source_revision":design_ai.digest(design_ai.content(source)),
        "contract_definitions":{c.id:capability_bindings.digest(c.definition) for c in contracts}}}
    policy=design_ai.TemplatePolicy.model_validate(value)
    authority("portugal",policy,source,db,reviewer)
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewer-id',required=True)
    parser.add_argument('--source-id',required=True)
    parser.add_argument('--registration-id',required=True)
    args=parser.parse_args()
    with SessionLocal() as db:
        value=prepare(db,args.reviewer_id,args.source_id,args.registration_id)
        db.rollback()
    print(json.dumps({'portugal':value},sort_keys=True))


if __name__=='__main__':main()
