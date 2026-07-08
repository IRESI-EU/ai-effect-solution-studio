from datetime import datetime

from pydantic import BaseModel


class DeploymentCreate(BaseModel):
    workflow_id: str
    solution_id: str | None = None
    name: str
    status: str = "submitted"


class DeploymentUpdate(BaseModel):
    status: str | None = None


class DeploymentRead(BaseModel):
    id: str
    workflow_id: str
    solution_id: str | None
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool = False

    class Config:
        from_attributes = True