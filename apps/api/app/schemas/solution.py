from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SolutionCreate(BaseModel):
    name: str
    description: str | None = None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    status: str = "draft"


class SolutionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    status: str | None = None


class SolutionRead(BaseModel):
    id: str
    name: str
    description: str | None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SolutionWithDeploymentsRead(SolutionRead):
    deployments: list["DeploymentRead"] = []


from app.schemas.deployment import DeploymentRead

SolutionWithDeploymentsRead.model_rebuild()