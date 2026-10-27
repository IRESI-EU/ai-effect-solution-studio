from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SolutionCreate(BaseModel):
    design_metadata: dict[str, Any] | None = None
    name: str
    description: str | None = None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    status: str = "draft"


class SolutionUpdate(BaseModel):
    expected_updated_at: str | None = None
    design_metadata: dict[str, Any] | None = None
    name: str | None = None
    description: str | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    status: str | None = None


class SolutionRead(BaseModel):
    design_metadata: dict[str, Any] | None = None
    id: str
    name: str
    description: str | None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime
    created_by_user_id: str | None = None

    class Config:
        from_attributes = True

class SolutionWithDeploymentsRead(SolutionRead):
    deployments: list["DeploymentRead"] = []


from app.schemas.deployment import DeploymentRead

SolutionWithDeploymentsRead.model_rebuild()
