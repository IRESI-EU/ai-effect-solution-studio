from pydantic import BaseModel

from app.schemas.auth import NodeCode


class UserOwnershipRequest(BaseModel):
    user_id: str


class SolutionOwnershipRequest(UserOwnershipRequest):
    include_unowned_deployments: bool = True


class ServiceOwnershipRequest(BaseModel):
    node: NodeCode
