from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_session_token, hash_password, hash_session_token, verify_password
from app.db import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User, UserSession
from app.schemas.auth import LoginRequest, PasswordChangeRequest, RegistrationRequest, UserRead, validate_password_strength
from app.services.audit import record_audit_event


router = APIRouter(prefix="/auth", tags=["authentication"])
_DUMMY_PASSWORD_HASH = hash_password("NotARealPassword123")


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_hours * 60 * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: RegistrationRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    user = User(
        id=str(uuid4()),
        email=payload.email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        role=payload.requested_role,
        node=payload.node,
        status="pending",
    )
    db.add(user)
    record_audit_event(
        db,
        None,
        "user.registration_requested",
        "user",
        user.id,
        {"email": user.email, "requested_role": user.role, "node": user.node},
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=UserRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == payload.email).first()
    password_hash = user.password_hash if user else _DUMMY_PASSWORD_HASH
    password_valid = verify_password(payload.password, password_hash)
    if not user or not password_valid:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.status == "pending":
        raise HTTPException(status_code=403, detail="Your registration is awaiting administrator approval")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="This account is not active")

    raw_token, token_hash = create_session_token()
    session = UserSession(
        id=str(uuid4()),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=utc_now() + timedelta(hours=settings.session_hours),
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        ip_address=request.client.host if request.client else None,
    )
    user.last_login_at = utc_now()
    db.add(session)
    record_audit_event(db, user, "user.login", "user", user.id)
    db.commit()
    _set_session_cookie(response, raw_token)
    return user


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token:
        db.query(UserSession).filter(
            UserSession.token_hash == hash_session_token(raw_token)
        ).delete()
        db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return Response(status_code=204, headers=response.headers)


@router.get("/me", response_model=UserRead)
def current_user(user: User = Depends(get_current_user)):
    return user


@router.post("/change-password", status_code=204)
def change_password(
    payload: PasswordChangeRequest,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Choose a password you have not already used")
    user.password_hash = hash_password(payload.new_password)
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    record_audit_event(db, user, "user.password_changed", "user", user.id)
    db.commit()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return Response(status_code=204, headers=response.headers)


def bootstrap_admin(db: Session) -> None:
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    if db.query(User).filter(User.role == "platform_admin").first():
        return
    validate_password_strength(settings.bootstrap_admin_password)
    email = settings.bootstrap_admin_email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        existing.role = "platform_admin"
        existing.node = None
        existing.status = "active"
        existing.approved_at = utc_now()
        existing.password_hash = hash_password(settings.bootstrap_admin_password)
        admin = existing
    else:
        admin = User(
            id=str(uuid4()),
            email=email,
            display_name=settings.bootstrap_admin_name,
            password_hash=hash_password(settings.bootstrap_admin_password),
            role="platform_admin",
            node=None,
            status="active",
            approved_at=utc_now(),
        )
        db.add(admin)
    record_audit_event(db, None, "user.bootstrap_admin_created", "user", admin.id)
    db.commit()
