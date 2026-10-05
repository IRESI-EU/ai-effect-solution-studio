from pydantic import BaseModel, Field


class DataReferencePreviewRequest(BaseModel):
    protocol: str
    uri: str
    format: str | None = None
    task_id: str | None = Field(default=None, pattern=r"^task_[A-Za-z0-9_-]+$", max_length=160)
