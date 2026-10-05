from datetime import UTC, datetime, timedelta
from typing import Callable

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_session_token
from app.db import get_db
from app.models.user import User, UserSession


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def get_optional_user(
    session_token: str | None = Cookie(default=None, alias=settings.session_cookie_name),
    db: Session = Depends(get_db),
) -> User | None:
    if not session_token:
        return None
    token_hash = hash_session_token(session_token)
    session = (
        db.query(UserSession)
        .filter(UserSession.token_hash == token_hash, UserSession.expires_at > utc_now())
        .first()
    )
    if not session or session.user.status != "active":
        return None
    if session.last_seen_at < utc_now() - timedelta(minutes=5):
        session.last_seen_at = utc_now()
        db.commit()
    return session.user


def get_current_user(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission for this action")
        return user

    return dependency


require_admin = require_roles("platform_admin")
require_service_publisher = require_roles("platform_admin", "node_manager")


def can_manage_owned_record(user: User, owner_user_id: str | None) -> bool:
    return user.role == "platform_admin" or (owner_user_id is not None and owner_user_id == user.id)


def can_manage_service(user: User, owner_node: str | None) -> bool:
    if user.role == "platform_admin":
        return True
    return user.role == "node_manager" and owner_node is not None and owner_node == user.node
