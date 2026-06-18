from pydantic import BaseModel


class DataReferencePreviewRequest(BaseModel):
    protocol: str
    uri: str
    format: str | None = None