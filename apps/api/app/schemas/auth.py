from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


UserRole = Literal["solution_designer", "node_manager", "platform_admin"]
RegistrationRole = Literal["solution_designer", "node_manager"]
UserStatus = Literal["pending", "active", "rejected", "suspended"]
NodeCode = Literal["germany", "portugal", "denmark", "dutch"]


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 320 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid email address")
    return email


def validate_password_strength(value: str) -> str:
    if len(value) < 12:
        raise ValueError("Password must contain at least 12 characters")
    if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value):
        raise ValueError("Password must include uppercase and lowercase letters")
    if not re.search(r"\d", value):
        raise ValueError("Password must include a number")
    return value


class RegistrationRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    email: str
    password: str = Field(max_length=256)
    requested_role: RegistrationRole
    node: NodeCode | None = None

    _normalize_email = field_validator("email")(normalize_email)
    _validate_password = field_validator("password")(validate_password_strength)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Enter your full name")
        return normalized

    @model_validator(mode="after")
    def node_is_required_for_node_manager(self):
        if self.requested_role == "node_manager" and not self.node:
            raise ValueError("Select a node for Node Manager access")
        return self


class LoginRequest(BaseModel):
    email: str
    password: str = Field(max_length=256)

    _normalize_email = field_validator("email")(normalize_email)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(max_length=256)
    new_password: str = Field(max_length=256)

    _validate_new_password = field_validator("new_password")(validate_password_strength)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role: UserRole
    node: NodeCode | None
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    approved_by_user_id: str | None
    last_login_at: datetime | None

class ApprovalRequest(BaseModel):
    role: UserRole
    node: NodeCode | None = None

    @model_validator(mode="after")
    def node_is_required_for_node_manager(self):
        if self.role == "node_manager" and not self.node:
            raise ValueError("A Node Manager must be assigned to a node")
        if self.role == "platform_admin":
            self.node = None
        return self


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=160)
    role: UserRole | None = None
    node: NodeCode | None = None


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None
    action: str
    target_type: str
    target_id: str | None
    details: str | None
    created_at: datetime

