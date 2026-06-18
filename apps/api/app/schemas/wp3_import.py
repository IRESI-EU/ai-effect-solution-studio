from pydantic import BaseModel
from typing import Any


class WP3ImportRequest(BaseModel):
    provider: str
    category: str = "Imported WP3 Package"
    trust_badge: str = "Imported"
    blueprint: dict[str, Any]
    dockerinfo: dict[str, Any]