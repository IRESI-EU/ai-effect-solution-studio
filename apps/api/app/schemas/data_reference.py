from pydantic import BaseModel, Field


class DataReferencePreviewRequest(BaseModel):
    workflow_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$", max_length=160)
    protocol: str
    uri: str
    format: str | None = None
    task_id: str = Field(pattern=r"^task_[A-Za-z0-9_-]+$", max_length=160)
