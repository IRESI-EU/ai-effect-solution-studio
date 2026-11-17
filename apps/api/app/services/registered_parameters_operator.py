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


def prepare(db,reviewer_id,source_id,registration_id,*,deployment_design_input=None):
    reviewer=db.get(User,reviewer_id);source=db.get(Solution,source_id)
    if not reviewer or not source or source.status=="archived":
        raise HTTPException(409,"Existing active reviewer and saved source required")
    contracts=db.query(OperationContract).filter(OperationContract.id.in_(PINS)).all()
    value={"solution_id":source.id,"instance_settings_only":True,"registered_parameters":{
        "registration_id":registration_id,"reviewer_id":reviewer.id,
        "source_revision":design_ai.digest(design_ai.content(source)),
        "contract_definitions":{c.id:capability_bindings.digest(c.definition) for c in contracts}}}
    if deployment_design_input is not None:
        value["registered_parameters"]["deployment_design_input"] = deployment_design_input
    policy=design_ai.TemplatePolicy.model_validate(value)
    authority("portugal",policy,source,db,reviewer)
    return value


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewer-id',required=True)
    parser.add_argument('--source-id',required=True)
    parser.add_argument('--registration-id',required=True)
    parser.add_argument('--design-environment')
    parser.add_argument('--dataset-ref')
    parser.add_argument('--dataset-label')
    args=parser.parse_args()
    with SessionLocal() as db:
        deployment=None
        if any((args.design_environment,args.dataset_ref,args.dataset_label)):
            if not all((args.design_environment,args.dataset_ref,args.dataset_label)):
                parser.error('Target registration requires environment, dataset-ref and dataset-label together')
            from app.core.config import settings
            from app.services.shared_allowance import database_scope
            deployment=dict(environment=args.design_environment,database_scope=database_scope(settings.database_url),dataset_ref=args.dataset_ref,label=args.dataset_label)
        value=prepare(db,args.reviewer_id,args.source_id,args.registration_id,deployment_design_input=deployment)
        db.rollback()
    print(json.dumps({'portugal':value},sort_keys=True))


if __name__=='__main__':main()
